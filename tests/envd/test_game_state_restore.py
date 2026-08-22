import pickle
from types import SimpleNamespace

import pytest

from fle.commons.models.game_state import GameState

pytestmark = pytest.mark.no_factorio


def _fake_namespace() -> SimpleNamespace:
    return SimpleNamespace(
        persistent_vars=None,
        _set_inventory=lambda inventory: None,
        load_messages=lambda messages: None,
        _load_entity_state=lambda *args, **kwargs: None,
        _load_research_state=lambda state: None,
    )


def _fake_instance(namespaces) -> SimpleNamespace:
    first = namespaces[0]
    return SimpleNamespace(
        namespaces=namespaces,
        first_namespace=first,
        num_agents=len(namespaces),
    )


def _state(namespace_blobs) -> GameState:
    return GameState(
        entities="",
        inventories=[{} for _ in namespace_blobs],
        research=None,
        namespaces=namespace_blobs,
        agent_messages=[[] for _ in namespace_blobs],
    )


def test_to_instance_restores_namespace_vars():
    blob = pickle.dumps({"gear_count": 42, "plan": "main-bus"})
    instance = _fake_instance([_fake_namespace()])

    _state([blob]).to_instance(instance)

    assert instance.namespaces[0].persistent_vars["gear_count"] == 42
    assert instance.namespaces[0].persistent_vars["plan"] == "main-bus"


def test_to_instance_skips_empty_blobs():
    namespace = _fake_namespace()
    namespace.persistent_vars = {"kept": True}
    instance = _fake_instance([namespace])

    _state([bytes()]).to_instance(instance)

    assert namespace.persistent_vars == {"kept": True}


def test_to_instance_maps_blobs_per_agent():
    first, second = _fake_namespace(), _fake_namespace()
    instance = _fake_instance([first, second])

    _state(
        [pickle.dumps({"agent": 1}), pickle.dumps({"agent": 2})]
    ).to_instance(instance)

    assert first.persistent_vars == {"agent": 1}
    assert second.persistent_vars == {"agent": 2}


def test_to_instance_never_pickles_the_live_namespace():
    """Regression: the old code called pickle.loads() on the live namespace
    object (always truthy) instead of the stored blob."""

    namespace = _fake_namespace()
    instance = _fake_instance([namespace])

    broken_state = GameState(
        entities="",
        inventories=[{}],
        research=None,
        namespaces=[namespace],  # type: ignore[list-item]
        agent_messages=[[]],
    )
    with pytest.raises((TypeError, AttributeError, pickle.UnpicklingError)):
        broken_state.to_instance(instance)
