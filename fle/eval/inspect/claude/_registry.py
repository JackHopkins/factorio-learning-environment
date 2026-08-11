"""inspect_ai entry point that registers the ``claude`` model provider.

inspect_ai imports this module at startup for *every* eval, not just ones
using ``--model claude/...``. The provider leans on private inspect_ai
internals that move between releases, so an incompatible inspect-ai must
only disable the claude provider -- never break unrelated evals with an
ImportError raised during entry-point loading.
"""

import logging

log = logging.getLogger(__name__)

try:
    from fle.eval.inspect.claude.provider import ClaudeAPI  # noqa: F401
except Exception as exc:
    log.warning(
        "The claude/<model> provider is unavailable "
        "(incompatible inspect-ai version?): %s",
        exc,
    )
