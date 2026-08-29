from types import SimpleNamespace

import pytest

from fle.envd.backend import FLEWorker
from fle.envd.models import DepotDeliveryTelemetry


pytestmark = pytest.mark.no_factorio


class _StateNamespace:
    def __init__(self):
        self.tick = 0
        self.inventory = {"iron-plate": 10}
        self.stats = {"input": {}, "output": {}}
        self.census = {"assembling-machine-1": {"working": 1}}
        self.research = {"researched": {"automation": 1}}

    def inspect_inventory(self):
        return dict(self.inventory)

    def _get_production_stats(self):
        return self.stats

    def _entity_census(self):
        return {"census": self.census}

    def _save_research_state(self, *, compact=False):
        assert compact is True
        return self.research


class _StateInstance:
    def __init__(self, namespace):
        self.first_namespace = namespace

    def get_elapsed_ticks(self):
        return self.first_namespace.tick


def _worker():
    namespace = _StateNamespace()
    worker = FLEWorker.__new__(FLEWorker)
    worker.instance = _StateInstance(namespace)
    worker.task_spec = SimpleNamespace(task_id="state-task")
    worker._contracts_view = lambda: []
    worker._sync_customer = lambda: []
    worker._sync_active_order = lambda: []
    worker._scores = lambda: (0.0, 0.0)
    worker._current_state_hash = lambda: "state-hash"
    worker._blueprint_summaries = lambda: []
    worker._delivery_telemetry_snapshot = (
        lambda *, recent_limit=120: DepotDeliveryTelemetry()
    )
    worker._customer_depots_cache = []
    worker._action_events = []
    worker._research_cache = None
    worker._observed_unlocked = set()
    worker._flow_history = []
    worker._production_history = []
    worker._contract_production_baseline = {"input": {}, "output": {}}
    worker._observation_revision = 0
    worker._observation_history = []
    worker._public_state_history = []
    worker._observation_nonce = "testnonce"
    worker._observation_keyframe_revision = 0
    worker._observation_keyframe_id = ""
    worker._observation_keyframe_pending = True
    return worker, namespace


def test_observe_emits_absolute_inventory_and_revisioned_delta():
    worker, namespace = _worker()

    first = worker.observe("lease-1")
    assert first.is_keyframe is True
    assert first.cursor == "testnonce.1"
    assert first.base_revision == 1
    assert first.inventory == {"iron-plate": 10}
    assert first.inventory_delta == {}
    assert first.delta == {}

    namespace.tick = 600
    namespace.inventory["iron-plate"] = 13
    namespace.stats["output"] = {"iron-plate": 120}
    namespace.census = {"assembling-machine-1": {"working": 2}}
    namespace.research = {
        "researched": {"automation": 1, "logistics": 1},
    }
    worker._research_cache = None

    second = worker.observe("lease-1", cursor=first.cursor)
    assert second.cursor == "testnonce.2"
    assert second.is_keyframe is False
    assert second.cursor_expired is False
    assert second.base_revision == first.base_revision
    assert second.inventory == {"iron-plate": 13}
    assert second.inventory_delta == {"iron-plate": 3}
    assert second.delta["production"]["output"] == {"iron-plate": 120}
    assert second.entities["status_by_name"]["assembling-machine-1"]["working"] == 2
    assert second.research["newly_researched_since_previous"] == ["logistics"]
    assert second.production["raw_rates_5s"]["iron-plate"] == 720
    assert second.production["automated_rates_available"] is False

    inventory_history = worker.query_state(
        "lease-1", kind="inventory", since_revision=1
    )
    assert inventory_history["current"] == {"iron-plate": 13}
    assert inventory_history["samples"] == [
        {"revision": 2, "ticks": 600, "delta": {"iron-plate": 3}}
    ]

    production_history = worker.query_state(
        "lease-1", kind="production", since_revision=1, item="iron-plate"
    )
    assert production_history["samples"][-1]["revision"] == 2
    assert production_history["samples"][-1]["output"] == {"iron-plate": 120}

    research_history = worker.query_state(
        "lease-1", kind="research", since_revision=1
    )
    assert research_history["changes"] == [
        {
            "revision": 2,
            "ticks": 600,
            "newly_researched": ["logistics"],
            "newly_unlocked": ["iron-plate"],
        }
    ]

    entity_history = worker.query_state(
        "lease-1", kind="entities", changed_since=1
    )
    assert entity_history["mutations"][-1]["changed"]["assembling-machine-1"] == {
        "before": 1,
        "after": 2,
    }


def test_stale_cursor_falls_back_to_keyframe_and_public_history_is_compact():
    worker, namespace = _worker()
    worker.observe("lease-1")
    namespace.tick = 60
    namespace.inventory["iron-plate"] = 11
    worker._research_cache = None
    stale = worker.observe("lease-1", cursor="other-run.1")

    assert stale.cursor_expired is True
    assert stale.is_keyframe is True
    assert stale.base_revision == stale.revision == 2
    assert len(worker._observation_history) == 2
    assert len(worker._public_state_history) == 2
    assert "inventory_delta" in worker._public_state_history[1]
    assert "inventory" not in worker._public_state_history[1]


def test_delivery_ledger_is_not_lost_when_recent_observation_projection_is_bounded():
    worker, _ = _worker()
    worker._delivery_history = []
    worker._delivery_raw_totals = {}

    for tick in range(1100):
        worker._record_delivery_samples(
            {"tick": tick}, [(tick, {"iron-plate": 1.0})]
        )

    assert len(worker._delivery_history) == 1100
    assert worker._delivery_history[0] == (0, {"iron-plate": 1.0})
    assert worker._delivery_history[-1] == (1099, {"iron-plate": 1.0})
    assert worker._delivery_raw_totals == {"iron-plate": 1100.0}
