"""Claude Pro/Max subscription (OAuth) support for FLE evals.

Provides an Inspect AI model provider (``claude/<model>``) that talks to the
Anthropic API using OAuth credentials from a Claude Pro/Max subscription,
instead of an ANTHROPIC_API_KEY.

Usage:
    fle claude login
    fle inspect-eval --env-id iron_ore_throughput --model claude/claude-sonnet-4-5

The provider itself lives in ``.provider`` and is registered through the
``inspect_ai`` entry point declared in pyproject.toml. It is deliberately not
imported here so that ``fle claude`` stays usable without inspect_ai installed.
"""

from .auth import (
    ClaudeAuthError,
    ClaudeCredentials,
    ensure_credentials,
    load_credentials,
    login,
)

__all__ = [
    "ClaudeAuthError",
    "ClaudeCredentials",
    "ensure_credentials",
    "load_credentials",
    "login",
]
