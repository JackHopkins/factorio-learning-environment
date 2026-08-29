"""Research identity and oversized-save fallback tests."""

import pytest

from fle.commons.models.research_state import (
    ResearchState,
    research_state_identity,
)
from fle.commons.models.technology_state import TechnologyState
from fle.env.tools.admin.save_research_state.client import SaveResearchState
from fle.envd.backend import FLEWorker, _instance_state_hash


UNIT = pytest.mark.no_factorio


def _technology(
    name: str,
    *,
    researched: bool,
    enabled: bool = True,
    level: int = 1,
    prerequisites: list[str] | None = None,
    ingredients: list[dict[str, int]] | None = None,
) -> TechnologyState:
    return TechnologyState(
        name=name,
        researched=researched,
        enabled=enabled,
        level=level,
        research_unit_count=10,
        research_unit_energy=30.0,
        prerequisites=prerequisites or [],
        ingredients=ingredients or [],
    )


class _FakeNamespace:
    def __init__(self):
        self.compact_state = {
            "format": "research-state-identity-v1",
            "researched": {"automation": 1},
            "disabled": [],
            "current_research": None,
            "research_progress": 0,
            "research_queue": [],
            "progress": {},
        }
        self.save_calls: list[bool] = []

    def _save_entity_state(self, *, compress, encode):
        assert compress is True
        assert encode is True
        return "serialized-entities"

    def inspect_inventory(self):
        return {"iron-plate": 3}

    def get_messages(self):
        return []

    def _save_research_state(self, compact=False):
        self.save_calls.append(compact)
        if not compact:
            raise ValueError("RCON returned an incomplete technology table")
        return self.compact_state


class _FakeInstance:
    def __init__(self):
        self.first_namespace = _FakeNamespace()
        self.namespaces = [self.first_namespace]


@UNIT
def test_full_and_compact_research_forms_share_identity():
    full = ResearchState(
        technologies={
            "automation": _technology(
                "automation",
                researched=True,
                prerequisites=["logistics"],
                ingredients=[{"automation-science-pack": 1}],
            ),
            "logistics": _technology("logistics", researched=False),
        },
        current_research=None,
        research_progress=0.0,
        research_queue=[],
        progress={},
    )
    compact = {
        "format": "research-state-identity-v1",
        "researched": {"automation": 1},
        "disabled": [],
        "current_research": None,
        "research_progress": 0,
        "research_queue": [],
        "progress": {},
    }

    assert research_state_identity(full) == research_state_identity(compact)


@UNIT
def test_research_identity_changes_when_research_changes():
    before = {
        "researched": {"automation": 1},
        "disabled": [],
        "current_research": None,
        "research_progress": 0,
        "research_queue": [],
        "progress": {},
    }
    after = {
        **before,
        "researched": {"automation": 1, "electronics": 1},
    }

    assert research_state_identity(before) != research_state_identity(after)


@UNIT
def test_state_hash_falls_back_to_compact_research_after_full_save_failure():
    instance = _FakeInstance()
    worker = FLEWorker.__new__(FLEWorker)
    worker.instance = instance
    worker._research_cache = None
    worker._state_hash_cache = None
    worker._state_hash_dirty = True

    first = worker._current_state_hash()
    assert len(first) == 64
    assert instance.first_namespace.save_calls == [False, True]
    assert worker._research_cache is None

    instance.first_namespace.compact_state["researched"]["electronics"] = 1
    worker._state_hash_dirty = True
    second = worker._current_state_hash()

    assert len(second) == 64
    assert second != first
    assert instance.first_namespace.save_calls == [False, True, False, True]


@UNIT
def test_instance_hash_uses_same_identity_for_full_and_compact_state():
    instance = _FakeInstance()
    full = ResearchState(
        technologies={
            "automation": _technology(
                "automation",
                researched=True,
                prerequisites=["logistics"],
                ingredients=[{"automation-science-pack": 1}],
            )
        },
        current_research=None,
        research_progress=0.0,
        research_queue=[],
        progress={},
    )
    compact = instance.first_namespace.compact_state

    assert _instance_state_hash(instance, research_state=full) == _instance_state_hash(
        instance, research_identity=compact
    )


@UNIT
def test_save_tool_rejects_empty_full_payload_but_accepts_compact_payload():
    tool = SaveResearchState.__new__(SaveResearchState)
    tool.player_index = 1
    tool.execute = lambda *_args: ({}, 0)

    with pytest.raises(Exception, match="incomplete technology table"):
        tool()

    compact = {
        "format": "research-state-identity-v1",
        "researched": {},
        "disabled": [],
        "current_research": None,
        "research_progress": 0,
        "research_queue": [],
        "progress": {},
    }
    tool.execute = lambda *_args: (compact, 0)
    assert tool(compact=True) == compact
