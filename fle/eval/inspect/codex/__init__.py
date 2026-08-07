"""ChatGPT subscription (Codex OAuth) support for FLE evals.

Provides an Inspect AI model provider (``codex/<model>``) that talks to the
ChatGPT Codex backend using OAuth credentials from a ChatGPT Plus/Pro
subscription, instead of an OpenAI API key.

Usage:
    fle codex login
    fle inspect-eval --env-id iron_ore_throughput --model codex/gpt-5.6-sol

The provider itself lives in ``.provider`` and is registered through the
``inspect_ai`` entry point declared in pyproject.toml. It is deliberately not
imported here so that ``fle codex`` stays usable without inspect_ai installed.
"""

from .auth import (
    CodexAuthError,
    CodexCredentials,
    ensure_credentials,
    load_credentials,
    login,
)

__all__ = [
    "CodexAuthError",
    "CodexCredentials",
    "ensure_credentials",
    "load_credentials",
    "login",
]
