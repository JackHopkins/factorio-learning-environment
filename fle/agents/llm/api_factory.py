import os
from typing import Dict, Any
from openai import AsyncOpenAI
from tenacity import retry, wait_exponential

from fle.agents.llm.metrics import timing_tracker, track_timing_async
from fle.agents.llm.utils import merge_contiguous_messages, remove_whitespace_blocks


class LLMProvider:
    """Base configuration for LLM providers"""

    CONFIGS = {
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "api_key": "OPENAI_API_KEY",
            "param_map": {"max_tokens": "max_completion_tokens"},
            "model_overrides": {
                "o1": {"temperature": 1, "exclude": ["logit_bias", "presence_penalty", "frequency_penalty"]},
                "o1-preview": {"temperature": 1, "exclude": ["logit_bias", "presence_penalty", "frequency_penalty"]},
                "o1-mini": {"temperature": 1, "exclude": ["logit_bias", "presence_penalty", "frequency_penalty"]},
                "gpt-5": {"temperature": 1, "exclude": ["logit_bias", "presence_penalty", "frequency_penalty"]},
                "gpt-5-mini": {"temperature": 1, "exclude": ["logit_bias", "presence_penalty", "frequency_penalty"]},
                "gpt-5-nano": {"temperature": 1, "exclude": ["logit_bias", "presence_penalty", "frequency_penalty"]},
            }
        },
        "claude": {
            "base_url": "https://api.anthropic.com/v1",
            "api_key": "ANTHROPIC_API_KEY",
            "param_map": {"max_tokens": "max_completion_tokens"},
        },
        "open-router": {
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": "OPEN_ROUTER_API_KEY",
            "transform": lambda m: m.replace("open-router-", ""),
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com",
            "api_key": "DEEPSEEK_API_KEY",
        },
        "gemini": {
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "api_key": "GEMINI_API_KEY",
            "param_map": {"max_tokens": "max_output_tokens"},
        },
        "together": {
            "base_url": "https://api.together.xyz/v1",
            "api_key": "TOGETHER_API_KEY",
        },
    }

    def __init__(self, model: str):
        # Find provider from model name
        self.provider = next((p for p in self.CONFIGS if p in model), "openai")
        self.config = self.CONFIGS[self.provider]
        self.client = AsyncOpenAI(
            base_url=self.config["base_url"],
            api_key=os.getenv(self.config["api_key"]),
            max_retries=0,
        )

    def prepare_params(self, **kwargs) -> Dict[str, Any]:
        """Map parameters based on provider requirements"""
        # Transform model name if needed
        model = kwargs.get("model", "")

        # Strip provider prefix if present (e.g., "openai/gpt-5-mini" -> "gpt-5-mini")
        if "/" in model:
            model = model.split("/", 1)[1]

        # Apply any provider-specific transform
        if transform := self.config.get("transform"):
            model = transform(model)

        # Check for model-specific overrides
        model_overrides = {}
        if overrides := self.config.get("model_overrides", {}):
            for model_pattern, override_params in overrides.items():
                if model_pattern in model:
                    model_overrides.update(override_params)

        # Standard parameters with overrides applied
        params = {
            "model": model,
            "messages": merge_contiguous_messages(
                remove_whitespace_blocks(kwargs.get("messages", []))
            ),
            "temperature": model_overrides.get("temperature", kwargs.get("temperature", 0.3)),
            "stream": False,
        }

        # Map provider-specific parameters
        param_map = self.config.get("param_map", {})

        # Get excluded parameters for this model
        excluded_params = model_overrides.get("exclude", [])

        # Add optional parameters
        optional_params = {
            "max_tokens": "max_tokens",
            "logit_bias": "logit_bias",
            "n_samples": "n",
            "stop_sequences": "stop",
            "presence_penalty": "presence_penalty",
            "frequency_penalty": "frequency_penalty",
        }

        for key, api_key in optional_params.items():
            if key in kwargs and kwargs[key] is not None:
                # Skip excluded parameters for specific models
                if api_key in excluded_params:
                    continue
                # Check if this parameter needs remapping for this provider
                final_key = param_map.get(api_key, api_key)
                params[final_key] = kwargs[key]

        return params


class APIFactory:
    """LLM API client with provider auto-detection"""

    def __init__(self, model: str, beam: int = 1):
        self.model = model
        self.beam = beam

    @track_timing_async("llm_api_call")
    @retry(wait=wait_exponential(multiplier=2, min=2, max=15))
    async def acall(self, **kwargs):
        """Make an async API call to the appropriate provider"""
        model = kwargs.get("model", self.model)
        provider = LLMProvider(model)

        # Prepare parameters for this provider
        kwargs["model"] = model
        api_params = provider.prepare_params(**kwargs)

        # Set default for max_tokens/max_completion_tokens if not provided
        if "max_completion_tokens" not in api_params and "max_tokens" not in api_params:
            # Use the appropriate parameter name for this provider
            param_map = provider.config.get("param_map", {})
            tokens_param = param_map.get("max_tokens", "max_tokens")
            api_params[tokens_param] = 256

        try:
            response = await provider.client.chat.completions.create(**api_params)
        except Exception as e:
            print(f"Error with {provider.provider}: {e}")
            raise

        # Track reasoning tokens if available
        if hasattr(response, "usage") and hasattr(response.usage, "reasoning_tokens"):
            async with timing_tracker.track_async(
                    "reasoning", model=model, tokens=response.usage.reasoning_tokens
            ):
                pass

        return response