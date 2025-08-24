import os

from openai import AsyncOpenAI
from tenacity import retry, wait_exponential

from fle.agents.llm.metrics import timing_tracker, track_timing_async
from fle.agents.llm.utils import (
    merge_contiguous_messages,
    remove_whitespace_blocks,
)


class APIFactory:
    # Provider configurations
    PROVIDERS = {
        "open-router": {
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": "OPEN_ROUTER_API_KEY",
            "model_transform": lambda m: m.replace("open-router-", ""),
        },
        "claude": {
            "base_url": "https://api.anthropic.com/v1",
            "api_key": "ANTHROPIC_API_KEY",
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com",
            "api_key": "DEEPSEEK_API_KEY",
        },
        "gemini": {
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "api_key": "GEMINI_API_KEY",
        },
        "together": {
            "base_url": "https://api.together.xyz/v1",
            "api_key": "TOGETHER_API_KEY",
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "api_key": "OPENAI_API_KEY",
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
        raise ValueError(f"No provider found for model: {model}")

    @track_timing_async("llm_api_call")
    @retry(wait=wait_exponential(multiplier=2, min=2, max=15))
    async def acall(self, **kwargs):
        model_to_use = kwargs.get("model", self.model)
        messages = kwargs.get("messages", [])
        # Get provider config
        provider_config = self._get_provider_config(model_to_use)
        # Apply model transform if specified
        if "model_transform" in provider_config:
            model_to_use = provider_config["model_transform"](model_to_use)
        # Prepare messages for text-only LLMs
        messages = remove_whitespace_blocks(messages)
        messages = merge_contiguous_messages(messages)
        # Create client
        client = AsyncOpenAI(
            base_url=provider_config["base_url"],
            api_key=os.getenv(provider_config["api_key"]),
            max_retries=0,
        )

        # Standard API call for all providers
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
