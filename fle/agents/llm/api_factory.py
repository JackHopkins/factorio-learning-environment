import os
import logging

from openai import AsyncOpenAI
from tenacity import retry, wait_exponential, stop_after_attempt

from fle.agents.llm.metrics import timing_tracker, track_timing_async
from fle.agents.llm.utils import (
    merge_contiguous_messages,
    remove_whitespace_blocks,
)
from fle.commons.constants import (
    OR_QWEN3_235B_THINKING,
    OR_GPT_OSS_120B,
    OR_DEEPSEEK_V3_1,
    OR_DEEPSEEK_R1,
    OR_CLAUDE_OPUS_4_1,
    OR_GEMINI_2_5_PRO,
    OR_GPT_5,
)


# Lazy import to avoid circular dependencies
def _get_api_key_manager():
    """Lazy import for API key manager to avoid circular imports."""
    try:
        from fle.eval.infra.api_key_manager import get_api_key_manager

        return get_api_key_manager
    except ImportError:
        return None


API_KEY_MANAGER_AVAILABLE = True  # Assume available, handle at runtime


class APIFactory:
    # Provider configurations
    PROVIDERS = {
        "open-router": {
            "base_url": "https://openrouter.ai/api/v1",
            "api_key_env": "OPEN_ROUTER_API_KEY",
            "key_manager_provider": "open-router",
            "model_transform": lambda m: m.replace("open-router-", "")
            if m.startswith("open-router-")
            else m,
        },
        "claude": {
            "base_url": "https://api.anthropic.com/v1",
            "api_key_env": "ANTHROPIC_API_KEY",
            "key_manager_provider": "anthropic",
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com",
            "api_key_env": "DEEPSEEK_API_KEY",
            "key_manager_provider": "deepseek",
        },
        "gemini": {
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "api_key_env": "GEMINI_API_KEY",
            "key_manager_provider": "gemini",
        },
        "together": {
            "base_url": "https://api.together.xyz/v1",
            "api_key_env": "TOGETHER_API_KEY",
            "key_manager_provider": "together",
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "api_key_env": "OPENAI_API_KEY",
            "key_manager_provider": "openai",
        },
    }

    def __init__(self, model: str, beam: int = 1, api_key_config_file: str = None):
        """Initialize APIFactory

        Args:
            model: Model name to use
            beam: Beam size for sampling
            api_key_config_file: Optional path to API key config file
        """
        self.model = model
        self.beam = beam
        self.api_key_config_file = (
            api_key_config_file  # Store for child process reinitialization
        )
        self.api_key_manager = None

        # Don't initialize API key manager in parent process to avoid multiprocessing pickle issues
        # It will be initialized lazily in the child process when first needed
        self.api_key_manager = None

    def _get_provider_config(self, model: str) -> dict:
        """Get provider config based on model name

        Models with '/' in the name (e.g., 'anthropic/claude-sonnet-4')
        are OpenRouter models and should use OpenRouter API.
        """
        # Check if this is an OpenRouter model (contains '/')
        if "/" in model:
            return self.PROVIDERS["open-router"]

        # Otherwise, check for provider prefixes
        for provider, config in self.PROVIDERS.items():
            if provider in model:
                return config
        raise ValueError(f"No provider found for model: {model}")

    def _get_api_key(self, provider_config: dict) -> str:
        """Get API key with rotation if available

        Args:
            provider_config: Provider configuration dictionary

        Returns:
            API key string
        """
        # Try key manager first if available (reinitialize if needed due to multiprocessing)
        if "key_manager_provider" in provider_config:
            key_manager_provider = provider_config["key_manager_provider"]

            # Reinitialize API key manager in child process if needed
            if not self.api_key_manager:
                try:
                    config_file = (
                        self.api_key_config_file
                        or os.getenv("FLE_API_KEY_CONFIG_FILE")
                        or os.getenv("API_KEY_CONFIG_FILE")
                    )
                    if config_file:
                        get_api_key_manager_func = _get_api_key_manager()
                        if get_api_key_manager_func:
                            self.api_key_manager = get_api_key_manager_func(config_file)
                            logging.info(
                                f"Reinitialized API key manager in child process: {config_file}"
                            )
                except Exception as e:
                    logging.warning(
                        f"Failed to reinitialize API key manager in child process: {e}"
                    )

            if self.api_key_manager:
                rotated_key = self.api_key_manager.get_key(key_manager_provider)
                if rotated_key:
                    logging.debug(f"Using rotated key for {key_manager_provider}")
                    return rotated_key

        # Fallback to environment variable
        env_var = provider_config["api_key_env"]
        env_key = os.getenv(env_var)

        if env_key:
            logging.debug(f"Using environment key from {env_var}")
            return env_key

        raise ValueError(
            f"No API key available for provider. "
            f"Set {env_var} or configure key manager."
        )

    def _mark_key_result(
        self,
        provider_config: dict,
        api_key: str,
        success: bool,
        error: Exception = None,
    ):
        """Mark the result of using an API key

        Args:
            provider_config: Provider configuration
            api_key: The API key that was used
            success: Whether the API call was successful
            error: Error that occurred (if any)
        """
        if self.api_key_manager and "key_manager_provider" in provider_config:
            key_manager_provider = provider_config["key_manager_provider"]

            if success:
                self.api_key_manager.mark_key_success(key_manager_provider, api_key)
            elif error:
                self.api_key_manager.mark_key_error(
                    key_manager_provider, api_key, error
                )

    @track_timing_async("llm_api_call")
    @retry(
        wait=wait_exponential(multiplier=2, min=2, max=15), stop=stop_after_attempt(3)
    )
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

        # Get API key with rotation
        api_key = self._get_api_key(provider_config)

        # Create client
        client = AsyncOpenAI(
            base_url=provider_config["base_url"],
            api_key=api_key,
            max_retries=0,  # We handle retries ourselves
        )

        try:
            # Check if this is a reasoning model that needs reasoning_enabled
            reasoning_models = [
                OR_QWEN3_235B_THINKING,
                OR_GPT_OSS_120B,
                OR_DEEPSEEK_V3_1,
                OR_DEEPSEEK_R1,
                OR_CLAUDE_OPUS_4_1,
                OR_GEMINI_2_5_PRO,
                OR_GPT_5,
            ]

            # Build the API call parameters
            api_params = {
                "model": model_to_use,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", 256),
                "temperature": kwargs.get("temperature", 0.3),
                "logit_bias": kwargs.get("logit_bias"),
                "n": kwargs.get("n_samples"),
                "stop": kwargs.get("stop_sequences"),
                "presence_penalty": kwargs.get("presence_penalty"),
                "frequency_penalty": kwargs.get("frequency_penalty"),
                "stream": False,
                "extra_body": {
                    "reasoning": {"enabled": model_to_use in reasoning_models}
                },
            }

            # Standard API call for all providers
            response = await client.chat.completions.create(**api_params)
            reasoning = getattr(response.choices[0].message, "reasoning", None)
            if reasoning is None and model_to_use in reasoning_models:
                print("WARNING: No reasoning was returned for model: {model_to_use}")
            # Mark key as successful
            self._mark_key_result(provider_config, api_key, success=True)

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
            # Mark key as having an error
            self._mark_key_result(provider_config, api_key, success=False, error=e)
            # Re-raise the exception to trigger retry mechanism
            raise
