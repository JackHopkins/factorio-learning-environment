import asyncio
import os

import anthropic
from openai import AsyncOpenAI, OpenAI
from tenacity import retry, wait_exponential

from fle.agents.llm.metrics import timing_tracker, track_timing_async
from fle.agents.llm.utils import (
    format_messages_for_anthropic,
    format_messages_for_openai,
    has_image_content,
    merge_contiguous_messages,
    remove_whitespace_blocks,
)


class NoRetryAsyncOpenAI(AsyncOpenAI):
    """Wrapper around AsyncOpenAI that always sets max_retries=0"""

    def __init__(self, **kwargs):
        kwargs["max_retries"] = 0
        super().__init__(**kwargs)


class APIFactory:
    # Models that support image input
    MODELS_WITH_IMAGE_SUPPORT = [
        # Claude models with vision
        "claude-3-opus",
        "claude-3-sonnet",
        "claude-3-haiku",
        "claude-3-5-sonnet",
        "claude-3-7-sonnet",
        "claude-3.7-sonnet",
        # OpenAI models with vision
        "gpt-4-vision",
        "gpt-4-turbo",
        "gpt-4o",
        "gpt-4-1106-vision-preview",
    ]

    def __init__(self, model: str, beam: int = 1):
        self.model = model
        self.beam = beam

    def _is_model_image_compatible(self, model: str) -> bool:
        """
        Check if the model supports image inputs, accounting for model version suffixes.

        Examples:
            'claude-3.5-sonnet-20241022' -> matches 'claude-3.5-sonnet'
            'gpt-4o-2024-05-13' -> matches 'gpt-4o'
        """
        # Normalize the model name to lowercase
        model_lower = model.lower()

        # First check for exact matches
        if model_lower in self.MODELS_WITH_IMAGE_SUPPORT:
            return True

        # Check for models with version number suffixes
        for supported_model in self.MODELS_WITH_IMAGE_SUPPORT:
            if supported_model in model:
                return True

        # Special handling for custom adaptations
        if "vision" in model_lower and any(
            gpt in model_lower for gpt in ["gpt-4", "gpt4"]
        ):
            return True

        return False

    @track_timing_async("llm_api_call")
    @retry(wait=wait_exponential(multiplier=2, min=2, max=15))
    async def acall(self, *args, **kwargs):
        max_tokens = kwargs.get("max_tokens", 2000)
        model_to_use = kwargs.get("model", self.model)
        messages = kwargs.get("messages", [])

        # Check for image content
        has_images = has_image_content(messages)

        # Validate image capability if images are present
        if has_images and not self._is_model_image_compatible(model_to_use):
            raise ValueError(
                f"Model {model_to_use} does not support image inputs, but images were provided."
            )

        if "open-router" in model_to_use:
            async with timing_tracker.track_async(
                "open_router_api_call", model=model_to_use, llm=True
            ):
                client = NoRetryAsyncOpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=os.getenv("OPEN_ROUTER_API_KEY"),
                )
                response = await client.chat.completions.create(
                    model=model_to_use.replace("open-router", "").strip("-"),
                    max_tokens=kwargs.get("max_tokens", 256),
                    temperature=kwargs.get("temperature", 0.3),
                    messages=kwargs.get("messages", None),
                    logit_bias=kwargs.get("logit_bias", None),
                    n=kwargs.get("n_samples", None),
                    stop=kwargs.get("stop_sequences", None),
                    stream=False,
                    presence_penalty=kwargs.get("presence_penalty", None),
                    frequency_penalty=kwargs.get("frequency_penalty", None),
                )
                return response

        if "claude" in model_to_use:
            async with timing_tracker.track_async(
                "claude_api_call", model=model_to_use, llm=True
            ):
                # Process system message
                system_message = ""
                if messages and messages[0]["role"] == "system":
                    system_message = messages[0]["content"]
                    if isinstance(system_message, list):
                        # Extract just the text parts for system message
                        system_text_parts = []
                        for part in system_message:
                            if isinstance(part, dict) and part.get("type") == "text":
                                system_text_parts.append(part.get("text", ""))
                            elif isinstance(part, str):
                                system_text_parts.append(part)
                        system_message = "\n".join(system_text_parts)
                    system_message = system_message.strip()

                # If the most recent message is from the assistant and ends with whitespace, clean it
                if messages and messages[-1]["role"] == "assistant":
                    if isinstance(messages[-1]["content"], str):
                        messages[-1]["content"] = messages[-1]["content"].strip()

                # If the most recent message is from the assistant, add a user message to prompt the assistant
                if messages and messages[-1]["role"] == "assistant":
                    messages.append({"role": "user", "content": "Success."})

                if not has_images:
                    # For text-only messages, use the standard processing
                    messages = remove_whitespace_blocks(messages)
                    messages = merge_contiguous_messages(messages)

                    # Format for Claude API
                    anthropic_messages = []
                    for msg in messages:
                        if msg["role"] != "system":  # System message handled separately
                            anthropic_messages.append(
                                {"role": msg["role"], "content": msg["content"]}
                            )
                else:
                    # For messages with images, use the special formatter
                    anthropic_messages = format_messages_for_anthropic(
                        messages, system_message
                    )

                if not system_message:
                    raise RuntimeError("No system message!!")

                try:
                    client = anthropic.Anthropic(max_retries=0)
                    # Use asyncio.to_thread for CPU-bound operations
                    response = await asyncio.to_thread(
                        client.messages.create,
                        temperature=kwargs.get("temperature", 0.7),
                        max_tokens=max_tokens,
                        model=model_to_use,
                        messages=anthropic_messages,
                        system=system_message,
                        stop_sequences=kwargs.get("stop_sequences", ["```END"]),
                    )
                except Exception as e:
                    print(e)
                    raise

                return response

        elif "deepseek" in model_to_use:
            if has_images:
                raise ValueError(
                    "Deepseek models do not support image inputs, but images were provided."
                )

            async with timing_tracker.track_async(
                "deepseek_api_call", model=model_to_use, llm=True
            ):
                client = NoRetryAsyncOpenAI(
                    api_key=os.getenv("DEEPSEEK_API_KEY"),
                    base_url="https://api.deepseek.com",
                )
                try:
                    response = await client.chat.completions.create(
                        model=model_to_use,
                        max_tokens=kwargs.get("max_tokens", 256),
                        temperature=kwargs.get("temperature", 0.3),
                        messages=kwargs.get("messages", None),
                        logit_bias=kwargs.get("logit_bias", None),
                        n=kwargs.get("n_samples", None),
                        stop=kwargs.get("stop_sequences", None),
                        stream=False,
                        presence_penalty=kwargs.get("presence_penalty", None),
                        frequency_penalty=kwargs.get("frequency_penalty", None),
                    )
                    return response
                except Exception as e:
                    print(e)
                    raise

        elif "gemini" in model_to_use:
            if has_images:
                raise ValueError(
                    "Gemini integration doesn't support image inputs through this interface."
                )

            async with timing_tracker.track_async(
                "gemini_api_call", model=model_to_use, llm=True
            ):
                client = NoRetryAsyncOpenAI(
                    api_key=os.getenv("GEMINI_API_KEY"),
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                )
                response = await client.chat.completions.create(
                    model=model_to_use,
                    max_tokens=kwargs.get("max_tokens", 256),
                    temperature=kwargs.get("temperature", 0.3),
                    messages=kwargs.get("messages", None),
                    n=kwargs.get("n_samples", None),
                    stream=False,
                )
                return response

        elif any(model in model_to_use for model in ["llama", "Qwen"]):
            if has_images:
                raise ValueError(
                    "Llama and Qwen models do not support image inputs through this interface."
                )

            async with timing_tracker.track_async(
                "together_api_call", model=model_to_use, llm=True
            ):
                client = NoRetryAsyncOpenAI(
                    api_key=os.getenv("TOGETHER_API_KEY"),
                    base_url="https://api.together.xyz/v1",
                )
                return await client.chat.completions.create(
                    model=model_to_use,
                    max_tokens=kwargs.get("max_tokens", 256),
                    temperature=kwargs.get("temperature", 0.3),
                    messages=kwargs.get("messages", None),
                    logit_bias=kwargs.get("logit_bias", None),
                    n=kwargs.get("n_samples", None),
                    stop=kwargs.get("stop_sequences", None),
                    stream=False,
                )

        elif "o1-mini" in model_to_use or "o3-mini" in model_to_use:
            if has_images:
                raise ValueError(
                    "Claude o1-mini and o3-mini models do not support image inputs."
                )

            async with timing_tracker.track_async(
                "o1_mini_api_call", model=model_to_use, llm=True
            ):
                client = NoRetryAsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                # replace `max_tokens` with `max_completion_tokens` for OpenAI API
                if "max_tokens" in kwargs:
                    kwargs.pop("max_tokens")
                messages = kwargs.get("messages")
                messages[0]["role"] = "developer"
                try:
                    reasoning_length = "low"
                    if "med" in model_to_use:
                        reasoning_length = "medium"
                    elif "high" in model_to_use:
                        reasoning_length = "high"
                    model = kwargs.get("model", "o3-mini")
                    if "o3-mini" in model:
                        model = "o3-mini"
                    elif "o1-mini" in model:
                        model = "o1-mini"

                    response = await client.chat.completions.create(
                        *args,
                        n=self.beam,
                        model=model,
                        messages=messages,
                        stream=False,
                        response_format={"type": "text"},
                        reasoning_effort=reasoning_length,
                    )

                    # Track reasoning metrics if available
                    if hasattr(response, "usage") and hasattr(
                        response.usage, "reasoning_tokens"
                    ):
                        async with timing_tracker.track_async(
                            "reasoning",
                            model=model_to_use,
                            tokens=response.usage.reasoning_tokens,
                            reasoning_length=reasoning_length,
                        ):
                            # This is just a marker for the timing - the actual reasoning happened in the API
                            pass

                    return response
                except Exception as e:
                    print(e)
        else:
            async with timing_tracker.track_async(
                "openai_api_call", model=model_to_use, llm=True
            ):
                try:
                    client = NoRetryAsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                    assert "messages" in kwargs, (
                        "You must provide a list of messages to the model."
                    )

                    if has_images:
                        # Format messages for OpenAI with image support
                        formatted_messages = format_messages_for_openai(messages)
                    else:
                        formatted_messages = messages

                    response = await client.chat.completions.create(
                        model=model_to_use,
                        max_tokens=kwargs.get("max_tokens", 256),
                        temperature=kwargs.get("temperature", 0.3),
                        messages=formatted_messages,
                        logit_bias=kwargs.get("logit_bias", None),
                        n=kwargs.get("n_samples", None),
                        stop=kwargs.get("stop_sequences", None),
                        stream=False,
                        presence_penalty=kwargs.get("presence_penalty", None),
                        frequency_penalty=kwargs.get("frequency_penalty", None),
                    )

                    # Track reasoning metrics if available
                    if hasattr(response, "usage") and hasattr(
                        response.usage, "reasoning_tokens"
                    ):
                        async with timing_tracker.track_async(
                            "reasoning",
                            model=model_to_use,
                            tokens=response.usage.reasoning_tokens,
                        ):
                            # This is just a marker for the timing - the actual reasoning happened in the API
                            pass

                    return response
                except Exception as e:
                    print(e)
                    try:
                        client = NoRetryAsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                        assert "messages" in kwargs, (
                            "You must provide a list of messages to the model."
                        )

                        # Attempt with truncated message history as fallback
                        sys = kwargs.get("messages", None)[0]
                        messages = [sys] + kwargs.get("messages", None)[8:]

                        if has_images:
                            # Format messages for OpenAI with image support
                            formatted_messages = format_messages_for_openai(messages)
                        else:
                            formatted_messages = messages

                        response = await client.chat.completions.create(
                            model=model_to_use,
                            max_tokens=kwargs.get("max_tokens", 256),
                            temperature=kwargs.get("temperature", 0.3),
                            messages=formatted_messages,
                            logit_bias=kwargs.get("logit_bias", None),
                            n=kwargs.get("n_samples", None),
                            stop=kwargs.get("stop_sequences", None),
                            stream=False,
                            presence_penalty=kwargs.get("presence_penalty", None),
                            frequency_penalty=kwargs.get("frequency_penalty", None),
                        )

                        # Track reasoning metrics if available
                        if hasattr(response, "usage") and hasattr(
                            response.usage, "reasoning_tokens"
                        ):
                            async with timing_tracker.track_async(
                                "reasoning",
                                model=model_to_use,
                                tokens=response.usage.reasoning_tokens,
                            ):
                                # This is just a marker for the timing - the actual reasoning happened in the API
                                pass

                        return response
                    except Exception as e:
                        print(e)
                        raise

    def call(self, *args, **kwargs):
        # For the synchronous version, we should also implement image support,
        # but I'll leave this method unchanged as the focus is on the async version.
        # The same pattern would be applied here as in acall.
        max_tokens = kwargs.get("max_tokens", 1500)
        model_to_use = kwargs.get("model", self.model)

        messages = kwargs.get("messages", [])
        has_images = self._has_image_content(messages)

        # Validate image capability if images are present
        if has_images and not self._is_model_image_compatible(model_to_use):
            raise ValueError(
                f"Model {model_to_use} does not support image inputs, but images were provided."
            )

        if "claude" in model_to_use:
            # Process system message
            system_message = ""
            if messages and messages[0]["role"] == "system":
                system_message = messages[0]["content"]
                if isinstance(system_message, list):
                    # Extract just the text parts for system message
                    system_text_parts = []
                    for part in system_message:
                        if isinstance(part, dict) and part.get("type") == "text":
                            system_text_parts.append(part.get("text", ""))
                        elif isinstance(part, str):
                            system_text_parts.append(part)
                    system_message = "\n".join(system_text_parts)
                system_message = system_message.strip()

            # Remove final assistant content that ends with trailing whitespace
            if messages[-1]["role"] == "assistant":
                if isinstance(messages[-1]["content"], str):
                    messages[-1]["content"] = messages[-1]["content"].strip()

            # If the most recent message is from the assistant, add a user message to prompt the assistant
            if messages[-1]["role"] == "assistant":
                messages.append({"role": "user", "content": "Success."})

            if not has_images:
                # Standard text processing
                messages = self.remove_whitespace_blocks(messages)
                messages = self.merge_contiguous_messages(messages)

                # Format for Claude API
                anthropic_messages = []
                for msg in messages:
                    if msg["role"] != "system":  # System message handled separately
                        anthropic_messages.append(
                            {"role": msg["role"], "content": msg["content"]}
                        )
            else:
                # Format with image support
                anthropic_messages = self._format_messages_for_anthropic(
                    messages, system_message
                )

            try:
                client = anthropic.Anthropic()
                response = client.messages.create(
                    temperature=kwargs.get("temperature", 0.7),
                    max_tokens=max_tokens,
                    model=model_to_use,
                    messages=anthropic_messages,
                    system=system_message,
                    stop_sequences=kwargs.get("stop_sequences", None),
                )
            except Exception as e:
                print(e)
                raise

            return response

        elif "deepseek" in model_to_use:
            if has_images:
                raise ValueError(
                    "Deepseek models do not support image inputs, but images were provided."
                )

            client = OpenAI(
                api_key=os.getenv("DEEPSEEK_API_KEY"),
                base_url="https://api.deepseek.com",
            )
            response = client.chat.completions.create(
                *args,
                **kwargs,
                model=model_to_use,
                presence_penalty=kwargs.get("presence_penalty", None),
                frequency_penalty=kwargs.get("frequency_penalty", None),
                logit_bias=kwargs.get("logit_bias", None),
                n=kwargs.get("n_samples", None),
                stop=kwargs.get("stop_sequences", None),
                stream=False,
            )
            return response

        elif "o1-mini" in model_to_use:
            if has_images:
                raise ValueError("Claude o1-mini model does not support image inputs.")

            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            # replace `max_tokens` with `max_completion_tokens` for OpenAI API
            if "max_tokens" in kwargs:
                kwargs.pop("max_tokens")

            return client.chat.completions.create(
                *args, n=self.beam, **kwargs, stream=False
            )
        else:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            assert "messages" in kwargs, (
                "You must provide a list of messages to the model."
            )

            if has_images:
                # Format messages for OpenAI with image support
                formatted_messages = self._format_messages_for_openai(messages)
            else:
                formatted_messages = messages

            return client.chat.completions.create(
                model=model_to_use,
                max_tokens=kwargs.get("max_tokens", 256),
                temperature=kwargs.get("temperature", 0.3),
                messages=formatted_messages,
                logit_bias=kwargs.get("logit_bias", None),
                n=kwargs.get("n_samples", None),
                stop=kwargs.get("stop_sequences", None),
                stream=False,
            )
