"""Inspect AI model provider backed by a Claude Pro/Max subscription.

Subclasses Inspect's AnthropicAPI and swaps API-key auth for the OAuth
credentials of a Claude subscription (the same grant Claude Code uses).

The Anthropic API only accepts subscription tokens when the request looks
like Claude Code, which shapes the implementation:

  * auth is ``Authorization: Bearer <token>`` (never ``x-api-key``), with the
    ``oauth-2025-04-20`` and ``claude-code-20250219`` betas and Claude Code's
    ``user-agent``/``x-app`` headers;
  * the first system block must be exactly Claude Code's identity line --
    requests without it are rejected as unauthorized;
  * tokens expire hourly and the refresh token rotates on use, so refreshes
    are serialised process-wide and rotated tokens are written back to the
    file they were loaded from (see ``.auth``).

Message conversion, caching, thinking and usage accounting are all inherited
from Inspect's AnthropicAPI.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

import anyio
import httpx
from anthropic import AsyncAnthropic, DefaultAsyncHttpxClient
from anthropic.types import TextBlockParam
from typing_extensions import override

from inspect_ai.model import GenerateConfig, modelapi
from inspect_ai.model._providers.anthropic import AnthropicAPI

from .auth import ClaudeCredentials, ensure_credentials

CLAUDE_BASE_URL = "https://api.anthropic.com"

# The real credential is attached per-request by _ClaudeOAuth below; the
# placeholder just keeps the SDK on the Bearer-auth path (no x-api-key).
_PLACEHOLDER_AUTH_TOKEN = "claude-oauth"

# Anthropic rejects subscription tokens unless the request carries the
# Claude Code identity: these betas/headers plus the system prompt below.
_OAUTH_BETAS = "claude-code-20250219,oauth-2025-04-20"
_CLAUDE_CODE_VERSION = "2.1.75"
CLAUDE_CODE_SYSTEM_PROMPT = (
    "You are Claude Code, Anthropic's official CLI for Claude."
)


class _CredentialCache:
    """Process-wide credential holder shared by every Claude request.

    Refresh tokens rotate on use, so concurrent samples must not each kick off
    their own refresh -- the losers of that race would persist tokens that the
    winner already invalidated. One lock, one refresh, one cached result.
    """

    def __init__(self) -> None:
        self._lock = anyio.Lock()
        self._credentials: ClaudeCredentials | None = None

    async def get(self) -> ClaudeCredentials:
        async with self._lock:
            if self._credentials is None or self._credentials.is_expired():
                self._credentials = await ensure_credentials()
            return self._credentials


# One cache for the whole process: every _ClaudeOAuth (one per model instance)
# must share the same lock, or two model instances could race a refresh with
# the same soon-to-be-rotated refresh token.
_CREDENTIAL_CACHE = _CredentialCache()


class _ClaudeOAuth(httpx.Auth):
    """Attaches (and transparently refreshes) Claude OAuth credentials."""

    def __init__(self) -> None:
        self._cache = _CREDENTIAL_CACHE

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncIterator[httpx.Request]:
        credentials = await self._cache.get()
        request.headers["Authorization"] = f"Bearer {credentials.access_token}"
        # The API rejects requests carrying both header styles.
        if "x-api-key" in request.headers:
            del request.headers["x-api-key"]
        yield request


def _oauth_http_client() -> httpx.AsyncClient:
    return DefaultAsyncHttpxClient(auth=_ClaudeOAuth())


@modelapi(name="claude")
class ClaudeAPI(AnthropicAPI):
    """Anthropic provider that authenticates with a Claude Pro/Max subscription."""

    def __init__(
        self,
        model_name: str,
        base_url: str | None = None,
        api_key: str | None = None,
        config: GenerateConfig = GenerateConfig(),
        **model_args: Any,
    ) -> None:
        model_args.setdefault("http_client", _oauth_http_client())
        # Client-default betas are folded into per-request anthropic-beta
        # headers by AnthropicAPI._beta_header_value, so the OAuth betas
        # survive requests that add their own (thinking, computer use, ...).
        headers = {
            "anthropic-beta": _OAUTH_BETAS,
            "user-agent": f"claude-cli/{_CLAUDE_CODE_VERSION}",
            "x-app": "cli",
        }
        headers.update(model_args.pop("default_headers", None) or {})
        model_args["default_headers"] = headers

        super().__init__(
            model_name=model_name,
            base_url=base_url or CLAUDE_BASE_URL,
            api_key=api_key or _PLACEHOLDER_AUTH_TOKEN,
            config=config,
            **model_args,
        )

    @override
    def _create_client(self) -> AsyncAnthropic:
        # AnthropicAPI._create_client would insist on ANTHROPIC_API_KEY (or
        # ANTHROPIC_AUTH_TOKEN) and send it; the subscription flow owns auth
        # entirely, so build the Bearer-auth client directly.
        return AsyncAnthropic(
            base_url=self.base_url,
            auth_token=_PLACEHOLDER_AUTH_TOKEN,
            **self.model_args,
        )

    @override
    def initialize(self) -> None:
        # Inspect's auth-failure recovery calls aclose() + initialize(), and
        # closing the Anthropic client closes the shared http_client kept in
        # model_args -- recreating from it would fail on the first request.
        # Recreate the authenticated transport first.
        http_client = self.model_args.get("http_client")
        if isinstance(http_client, httpx.AsyncClient) and http_client.is_closed:
            self.model_args["http_client"] = _oauth_http_client()
        super().initialize()

    @override
    def connection_key(self) -> str:
        # All Claude traffic shares one subscription quota.
        return "claude-oauth"

    async def resolve_chat_input(
        self,
        input: Any,
        tools: Any,
        config: GenerateConfig,
    ) -> Any:
        (
            system_param,
            tools_param,
            mcp_servers_param,
            messages,
            cache_prompt,
        ) = await super().resolve_chat_input(input, tools, config)

        # Subscription tokens are only authorized for Claude Code, and the
        # API checks the first system block for its identity. The eval's own
        # system prompt follows as the second block; cache breakpoints set by
        # the base class sit on the last block and still cover this prefix.
        spoof = TextBlockParam(type="text", text=CLAUDE_CODE_SYSTEM_PROMPT)
        system_param = [spoof, *(system_param or [])]

        return system_param, tools_param, mcp_servers_param, messages, cache_prompt
