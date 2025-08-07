import os

from openai import AsyncOpenAI
from tenacity import retry, wait_exponential

from fle.agents.llm.metrics import timing_tracker, track_timing_async
from fle.agents.llm.utils import (
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
    # Provider configurations - all using OpenAI-compatible endpoints
    PROVIDERS = {
        "claude": {
            "base_url": "https://api.anthropic.com/v1",
            "api_key_env": "ANTHROPIC_API_KEY",
            "supports_images": True,
        },
        "open-router": {
            "base_url": "https://openrouter.ai/api/v1",
            "api_key_env": "OPEN_ROUTER_API_KEY",
            "supports_images": True,
            "model_transform": lambda m: m.replace("open-router", "").strip("-"),
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com",
            "api_key_env": "DEEPSEEK_API_KEY",
            "supports_images": False,
        },
        "gemini": {
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "api_key_env": "GEMINI_API_KEY",
            "supports_images": False,
        },
        "together": {
            "base_url": "https://api.together.xyz/v1",
            "api_key_env": "TOGETHER_API_KEY",
            "supports_images": False,
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "api_key_env": "OPENAI_API_KEY",
            "supports_images": True,
            "supports_reasoning": True,
        },
    }

    # Models that support image input
    MODELS_WITH_IMAGE_SUPPORT = [
        "claude-3-opus",
        "claude-3-sonnet",
        "claude-3-haiku",
        "claude-3-5-sonnet",
        "claude-3-7-sonnet",
        "claude-3.7-sonnet",
        "gpt-4-vision",
        "gpt-4-turbo",
        "gpt-4o",
        "gpt-4-1106-vision-preview",
    ]

    def __init__(self, model: str, beam: int = 1):
        self.model = model
        self.beam = beam

    def _get_provider_config(self, model: str) -> dict:
        """Get provider config based on model name"""
        for provider_name, config in self.PROVIDERS.items():
            if provider_name in model:
                return config
        # Check for llama/qwen which use together
        if any(m in model.lower() for m in ["llama", "qwen"]):
            return self.PROVIDERS["together"]
        return self.PROVIDERS["openai"]  # default

    def _is_model_image_compatible(self, model: str) -> bool:
        """Check if model supports images"""
        model_lower = model.lower()
        if model_lower in [m.lower() for m in self.MODELS_WITH_IMAGE_SUPPORT]:
            return True
        return any(
            supported.lower() in model_lower
            for supported in self.MODELS_WITH_IMAGE_SUPPORT
        )

    def _prepare_messages(self, messages: list, has_images: bool) -> list:
        """Prepare messages for API call"""
        if not has_images:
            messages = remove_whitespace_blocks(messages)
            messages = merge_contiguous_messages(messages)

        # Clean trailing whitespace from final assistant message
        if messages and messages[-1]["role"] == "assistant":
            if isinstance(messages[-1]["content"], str):
                messages[-1]["content"] = messages[-1]["content"].strip()

        # Add continuation prompt if last message is from assistant
        if messages and messages[-1]["role"] == "assistant":
            messages.append({"role": "user", "content": "Success."})

        return messages

    def _is_reasoning_model(self, model: str) -> bool:
        """Check if model is a reasoning model (o1/o3)"""
        return any(reasoning in model for reasoning in ["o1-mini", "o3-mini"])

    @track_timing_async("llm_api_call")
    @retry(wait=wait_exponential(multiplier=2, min=2, max=15))
    async def acall(self, *args, **kwargs):
        model_to_use = kwargs.get("model", self.model)
        messages = kwargs.get("messages", [])
        has_images = has_image_content(messages)

        # Get provider config
        provider_config = self._get_provider_config(model_to_use)

        # Validate image support
        if has_images and not provider_config.get("supports_images", False):
            provider_name = next(
                name
                for name, config in self.PROVIDERS.items()
                if config == provider_config
            )
            raise ValueError(f"{provider_name} models do not support image inputs")

        # Transform model name if needed
        if "model_transform" in provider_config:
            model_to_use = provider_config["model_transform"](model_to_use)

        # Prepare messages
        messages = self._prepare_messages(messages, has_images)

        # Create client
        client = NoRetryAsyncOpenAI(
            base_url=provider_config["base_url"],
            api_key=os.getenv(provider_config["api_key_env"]),
        )

        # Build API parameters
        api_params = {
            "model": model_to_use,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.3),
            "stream": False,
        }

        # Handle reasoning models (o1/o3) with special parameters
        if self._is_reasoning_model(model_to_use):
            if has_images:
                raise ValueError("o1/o3 models do not support image inputs")

            # Convert system message to developer message for o1/o3
            if messages and messages[0]["role"] == "system":
                messages[0]["role"] = "developer"

            reasoning_length = "low"
            if "med" in model_to_use:
                reasoning_length = "medium"
            elif "high" in model_to_use:
                reasoning_length = "high"

            api_params.update(
                {
                    "model": "o3-mini" if "o3-mini" in model_to_use else "o1-mini",
                    "n": self.beam,
                    "reasoning_effort": reasoning_length,
                    "response_format": {"type": "text"},
                }
            )
        else:
            # Standard parameters for all other models
            api_params.update(
                {
                    "max_tokens": kwargs.get("max_tokens", 256),
                    "logit_bias": kwargs.get("logit_bias"),
                    "n": kwargs.get("n_samples"),
                    "stop": kwargs.get("stop_sequences"),
                    "presence_penalty": kwargs.get("presence_penalty"),
                    "frequency_penalty": kwargs.get("frequency_penalty"),
                }
            )

        # Remove None values
        api_params = {k: v for k, v in api_params.items() if v is not None}

        try:
            response = await client.chat.completions.create(**api_params)

            # Track reasoning tokens if available
            if hasattr(response, "usage") and hasattr(
                response.usage, "reasoning_tokens"
            ):
                async with timing_tracker.track_async(
                    "reasoning",
                    model=model_to_use,
                    tokens=response.usage.reasoning_tokens,
                ):
                    pass

            return response

        except Exception as e:
            # Fallback for OpenAI models with context length issues
            if (
                "openai" in provider_config["base_url"]
                and "maximum context length" in str(e).lower()
            ):
                # Retry with truncated history
                if len(messages) > 2:
                    sys_msg = (
                        messages[0]
                        if messages[0]["role"] in ["system", "developer"]
                        else None
                    )
                    truncated = ([sys_msg] if sys_msg else []) + messages[-8:]
                    api_params["messages"] = truncated
                    return await client.chat.completions.create(**api_params)
            raise
