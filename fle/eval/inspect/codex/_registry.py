"""inspect_ai entry point that registers the ``codex`` model provider.

inspect_ai imports this module at startup for *every* eval, not just ones
using ``--model codex/...``. The provider leans on private inspect_ai
internals that move between releases, so an incompatible inspect-ai must
only disable the codex provider -- never break unrelated evals with an
ImportError raised during entry-point loading.
"""

import logging

log = logging.getLogger(__name__)

try:
    from fle.eval.inspect.codex.provider import CodexAPI  # noqa: F401
except Exception as exc:
    log.warning(
        "The codex/<model> provider is unavailable "
        "(incompatible inspect-ai version?): %s",
        exc,
    )
