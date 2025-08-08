import os

from openai import AsyncOpenAI
from tenacity import retry, wait_exponential

from fle.agents.llm.metrics import timing_tracker, track_timing_async
from fle.agents.llm.utils import (
    has_image_content,
    merge_contiguous_messages,
    remove_whitespace_blocks,
)


class APIFactory:
    # Provider configurations
    PROVIDERS = {
        "open-router": {
            "base_url": "https://openrouter.ai/api/v1",
            "api_key_env": "OPEN_ROUTER_API_KEY",
            "supports_images": True,
            "model_transform": lambda m: m.replace("open-router-", ""),
        },
        "claude": {
            "base_url": "https://api.anthropic.com/v1",
            "api_key_env": "ANTHROPIC_API_KEY",
            "supports_images": True,
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com",
            "api_key_env": "DEEPSEEK_API_KEY",
        },
        "gemini": {
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "api_key_env": "GEMINI_API_KEY",
        },
        "together": {
            "base_url": "https://api.together.xyz/v1",
            "api_key_env": "TOGETHER_API_KEY",
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "api_key_env": "OPENAI_API_KEY",
            "supports_images": True,
            "supports_reasoning": True,
        },
    }

    def __init__(self, model: str, beam: int = 1):
        self.model = model
        self.beam = beam

    def _get_provider_config(self, model: str) -> dict:
        """Get provider config based on model name"""
        for provider, config in self.PROVIDERS.items():
            if provider in model:
                return config

    @track_timing_async("llm_api_call")
    @retry(wait=wait_exponential(multiplier=2, min=2, max=15))
    async def acall(self, **kwargs):
        model_to_use = kwargs.get("model", self.model)
        messages = kwargs.get("messages", [])
        has_images = has_image_content(messages)

        # Get provider config
        provider_config = self._get_provider_config(model_to_use)

        # Validate image support
        if has_images and not provider_config.get("supports_images", False):
            raise ValueError(f"Model {model_to_use} doesn't support images")

        # Prepare messages
        if not has_images:
            messages = remove_whitespace_blocks(messages)
            messages = merge_contiguous_messages(messages)

        # Create client
        client = AsyncOpenAI(
            base_url=provider_config["base_url"],
            api_key=os.getenv(provider_config["api_key_env"]),
            max_retries=0,
        )

        # Transform model name if needed
        if "model_transform" in provider_config:
            model_to_use = provider_config["model_transform"](model_to_use) + ":nitro"

        # Special handling for o1/o3 models
        if "o1-mini" in model_to_use or "o3-mini" in model_to_use:
            if has_images:
                raise ValueError("o1/o3 models don't support images")

            if messages and messages[0]["role"] == "system":
                messages[0]["role"] = "developer"

            kwargs.pop("max_tokens", None)  # Use max_completion_tokens instead

            reasoning_length = "low"
            if "med" in model_to_use:
                reasoning_length = "medium"
            elif "high" in model_to_use:
                reasoning_length = "high"

            response = await client.chat.completions.create(
                model="o3-mini" if "o3-mini" in model_to_use else "o1-mini",
                messages=messages,
                n=self.beam,
                reasoning_effort=reasoning_length,
                response_format={"type": "text"},
            )
        else:
            # Standard API call for all other providers
            response = await client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                max_tokens=kwargs.get("max_tokens", 256),
                temperature=kwargs.get("temperature", 0.3),
                logit_bias=kwargs.get("logit_bias"),
                n=kwargs.get("n_samples"),
                stop=kwargs.get("stop_sequences"),
                presence_penalty=kwargs.get("presence_penalty"),
                frequency_penalty=kwargs.get("frequency_penalty"),
                stream=False,
            )

        # Track reasoning tokens if available
        if hasattr(response, "usage") and hasattr(response.usage, "reasoning_tokens"):
            async with timing_tracker.track_async(
                "reasoning", model=model_to_use, tokens=response.usage.reasoning_tokens
            ):
                pass

        return response
