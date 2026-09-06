"""Provider-aware configuration helpers for Inspect models."""

from typing import Any

from inspect_ai.model import Model, ModelName


def configure_model_generation(
    model: Model | str, generation_config: dict[str, Any]
) -> dict[str, Any]:
    """Return generation options supported by the model's provider.

    ``transforms`` is an OpenRouter-specific option. Passing it while creating
    direct Google, Anthropic, or OpenAI models leaks the option into their SDK
    clients, which reject it before inference starts.
    """
    configured = generation_config.copy()
    if ModelName(model).api == "openrouter":
        configured["transforms"] = ["middle-out"]
    return configured
