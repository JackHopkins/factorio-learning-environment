"""The shipped example agents must at least be importable.

Regression test for the example modules importing BasicAgent and
BacktrackingAgent from fle.agents.*, where they do not exist (the
implementations live in examples/agents/).
"""

import importlib

import pytest

EXAMPLE_AGENT_MODULES = [
    "examples.agents.basic_agent",
    "examples.agents.backtracking_agent",
    "examples.agents.backtracking_system",
    "examples.agents.visual_agent",
]


@pytest.mark.parametrize("module_name", EXAMPLE_AGENT_MODULES)
def test_example_agent_module_imports(module_name: str) -> None:
    importlib.import_module(module_name)
