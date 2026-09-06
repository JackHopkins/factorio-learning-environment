"""Provider option tests that require no API keys or network access."""

import pytest

from fle.eval.inspect.model_utils import configure_model_generation


@pytest.mark.parametrize(
    "model_name",
    [
        "google/gemini-3.1-flash-lite",
        "anthropic/claude-sonnet-4-20250514",
        "openai/gpt-4o-mini",
        "mock/test-model",
    ],
)
def test_middle_out_is_not_sent_to_direct_providers(model_name: str) -> None:
    original = {"max_tokens": 4096}

    configured = configure_model_generation(model_name, original)

    assert configured == {"max_tokens": 4096}
    assert configured is not original


def test_middle_out_is_enabled_for_openrouter() -> None:
    configured = configure_model_generation(
        "openrouter/openai/gpt-4o-mini", {"max_tokens": 4096}
    )

    assert configured == {
        "max_tokens": 4096,
        "transforms": ["middle-out"],
    }
