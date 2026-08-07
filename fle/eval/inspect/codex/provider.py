"""Inspect AI model provider backed by a ChatGPT subscription.

Registers the ``codex`` provider, so any Inspect entry point accepts
``--model codex/<model>`` and authenticates with ChatGPT OAuth credentials
instead of an ``OPENAI_API_KEY``.

The ChatGPT Codex backend speaks a constrained dialect of the Responses API:

* ``stream`` must be ``true`` and ``store`` must be ``false``;
* the terminal ``response.completed`` event carries an **empty** ``output``,
  so output items have to be accumulated from ``response.output_item.done``;
* sampling/bookkeeping parameters (``temperature``, ``top_p``,
  ``max_output_tokens``, ``metadata``, ...) are rejected outright.

Everything else -- message/tool conversion, reasoning handling, usage
accounting -- is delegated to Inspect's own OpenAI Responses helpers.
"""

from __future__ import annotations

import uuid
from typing import Any, AsyncIterator

import anyio
import httpx
from openai import BadRequestError
from openai._types import NOT_GIVEN, NotGiven
from openai.types.responses import Response, ToolParam
from typing_extensions import override

from inspect_ai.log._samples import set_active_model_event_call
from inspect_ai.model import GenerateConfig, ModelOutput, modelapi
from inspect_ai.model._chat_message import ChatMessage
from inspect_ai.model._model_call import ModelCall, as_error_response
from inspect_ai.model._openai import (
    OpenAIAsyncHttpxClient,
    OpenAIResponseError,
    openai_handle_bad_request,
    openai_media_filter,
)
from inspect_ai.model._openai_responses import (
    openai_responses_chat_choices,
    openai_responses_inputs,
    openai_responses_tool_choice,
    openai_responses_tools,
)
from inspect_ai.model._providers.openai import OpenAIAPI
from inspect_ai.model._providers.openai_responses import (
    completion_params_responses,
    model_usage_from_response,
)
from inspect_ai.model._providers.util.hooks import HttpxHooks
from inspect_ai.tool import ToolChoice, ToolInfo

from .auth import CodexCredentials, ensure_credentials

CODEX_BASE_URL = "https://chatgpt.com/backend-api/codex"

# OpenAIAPI raises a PrerequisiteError unless *some* key is present; the real
# credential is attached per-request by _CodexOAuth below.
_PLACEHOLDER_API_KEY = "chatgpt-oauth"

# Rejected by the ChatGPT Codex backend with "Unsupported parameter: <name>".
_UNSUPPORTED_PARAMS = frozenset(
    {
        "max_output_tokens",
        "max_tool_calls",
        "metadata",
        "previous_response_id",
        "prompt_cache_retention",
        "safety_identifier",
        "temperature",
        "top_logprobs",
        "top_p",
        "truncation",
    }
)

# "logprobs are not supported with reasoning models" on this backend.
_UNSUPPORTED_INCLUDES = frozenset({"message.output_text.logprobs"})

# The backend advertises low/medium/high/xhigh/none; "minimal" is rejected.
_REASONING_EFFORT_ALIASES = {"minimal": "low"}

_TERMINAL_EVENTS = frozenset(
    {"response.completed", "response.incomplete", "response.failed"}
)


class _CredentialCache:
    """Process-wide credential holder shared by every Codex request.

    Refresh tokens rotate on use, so concurrent samples must not each kick off
    their own refresh -- the losers of that race would persist tokens that the
    winner already invalidated. One lock, one refresh, one cached result.
    """

    def __init__(self) -> None:
        self._lock = anyio.Lock()
        self._credentials: CodexCredentials | None = None

    async def get(self) -> CodexCredentials:
        async with self._lock:
            if self._credentials is None or self._credentials.is_expired():
                self._credentials = await ensure_credentials()
            return self._credentials


class _CodexOAuth(httpx.Auth):
    """Attaches (and transparently refreshes) ChatGPT OAuth credentials."""

    def __init__(self) -> None:
        self._cache = _CredentialCache()

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncIterator[httpx.Request]:
        credentials = await self._cache.get()
        request.headers["Authorization"] = f"Bearer {credentials.access_token}"
        request.headers["chatgpt-account-id"] = credentials.account_id
        yield request


def _sanitize_params(params: dict[str, Any]) -> dict[str, Any]:
    """Drop Responses-API parameters the ChatGPT Codex backend rejects."""
    sanitized = {k: v for k, v in params.items() if k not in _UNSUPPORTED_PARAMS}

    include = [
        i for i in sanitized.get("include") or [] if i not in _UNSUPPORTED_INCLUDES
    ]
    if include:
        sanitized["include"] = include
    else:
        sanitized.pop("include", None)

    reasoning = sanitized.get("reasoning")
    if isinstance(reasoning, dict):
        effort = reasoning.get("effort")
        if effort in _REASONING_EFFORT_ALIASES:
            sanitized["reasoning"] = {
                **reasoning,
                "effort": _REASONING_EFFORT_ALIASES[effort],
            }

    # store=False and stream=True are non-negotiable for this backend.
    sanitized["store"] = False
    return sanitized


@modelapi(name="codex")
class CodexAPI(OpenAIAPI):
    """OpenAI Responses provider that authenticates with a ChatGPT subscription."""

    def __init__(
        self,
        model_name: str,
        base_url: str | None = None,
        api_key: str | None = None,
        config: GenerateConfig = GenerateConfig(),
        **model_args: Any,
    ) -> None:
        model_args.setdefault("http_client", OpenAIAsyncHttpxClient(auth=_CodexOAuth()))
        # Mirror the official Codex CLI so the backend sees a familiar client.
        headers = {
            "OpenAI-Beta": "responses=experimental",
            "originator": "codex_cli_rs",
            "session_id": str(uuid.uuid4()),
        }
        headers.update(model_args.pop("default_headers", None) or {})
        model_args["default_headers"] = headers

        super().__init__(
            model_name=model_name,
            base_url=base_url or CODEX_BASE_URL,
            api_key=api_key or _PLACEHOLDER_API_KEY,
            config=config,
            responses_api=True,
            responses_store=False,
            **model_args,
        )

    @override
    def connection_key(self) -> str:
        # All Codex traffic shares one ChatGPT subscription quota.
        return "codex-oauth"

    @override
    async def generate(
        self,
        input: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput | tuple[ModelOutput | Exception, ModelCall]:
        request_id = self._http_hooks.start_request()
        model_name = self.service_model_name()

        tool_params: list[ToolParam] | NotGiven = (
            openai_responses_tools(
                tools, model_name, config, is_latest=self.is_latest()
            )
            if len(tools) > 0
            else NOT_GIVEN
        )

        request = dict(
            input=await openai_responses_inputs(input, self),
            tools=tool_params,
            tool_choice=openai_responses_tool_choice(tool_choice, tool_params)
            if isinstance(tool_params, list)
            and tool_choice != "auto"
            and len(tools) > 0
            else NOT_GIVEN,
            extra_headers={HttpxHooks.REQUEST_ID_HEADER: request_id}
            | (config.extra_headers or {}),
            **_sanitize_params(
                completion_params_responses(
                    model_name,
                    model_info=self,
                    config=config,
                    service_tier=None,
                    prompt_cache_key=NOT_GIVEN,
                    prompt_cache_retention=NOT_GIVEN,
                    safety_identifier=NOT_GIVEN,
                    responses_store=False,
                    tools=len(tools) > 0,
                    tool_params=[]
                    if isinstance(tool_params, NotGiven)
                    else tool_params,
                    has_computer_tool=False,
                )
            ),
        )

        model_call = set_active_model_event_call(
            request=request, filter=openai_media_filter
        )

        try:
            response = await self._collect_streamed_response(request)

            if response.error is not None:
                if response.error.code == "invalid_prompt":
                    model_call.set_error(
                        as_error_response(response.error),
                        self._http_hooks.end_request(request_id),
                    )
                    return ModelOutput.from_content(
                        model=model_name,
                        content=response.error.message,
                        stop_reason="content_filter",
                    ), model_call
                raise OpenAIResponseError(
                    code=response.error.code, message=response.error.message
                )

            model_call.set_response(
                response.model_dump(warnings=False),
                self._http_hooks.end_request(request_id),
            )
            return ModelOutput(
                model=response.model,
                choices=openai_responses_chat_choices(model_name, response, tools),
                usage=model_usage_from_response(response),
            ), model_call
        except BadRequestError as ex:
            model_call.set_error(
                as_error_response(ex.body), self._http_hooks.end_request(request_id)
            )
            return openai_handle_bad_request(model_name, ex), model_call

    async def _collect_streamed_response(self, request: dict[str, Any]) -> Response:
        """Run the streaming request and rebuild a complete Response.

        The Codex backend only speaks SSE and its terminal event reports an
        empty ``output`` array, so the finished items are gathered from the
        ``response.output_item.done`` events and spliced back in. Inspect's
        standard converters then see an ordinary Response.
        """
        stream = await self.client.responses.create(**request, stream=True)

        output: list[Any] = []
        response: Response | None = None
        async for event in stream:
            if event.type == "response.output_item.done":
                output.append(event.item)
            elif event.type in _TERMINAL_EVENTS:
                response = event.response
            elif event.type == "error":
                raise OpenAIResponseError(
                    code=event.code or "stream_error", message=event.message
                )

        if response is None:
            raise OpenAIResponseError(
                code="incomplete_stream",
                message="Codex stream ended without a terminal response event.",
            )

        if not response.output:
            response.output = output
        return response
