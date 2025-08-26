"""Factorio Learning Environment (FLE) package."""

# Make submodules available
from fle import agents, env, eval, cluster, commons

__all__ = ["agents", "env", "eval", "cluster", "commons"]

# Ensure Ctrl-C exits cleanly across OSes without stack traces
import signal
import sys


def _exit_on_sigint(signum, frame):
    sys.exit(0)


signal.signal(signal.SIGINT, _exit_on_sigint)
