"""Property and table tests for passive snapshots, bands, and features."""

import pytest

from fle.envd.contract_features import (
    GameDataError,
    ProductCatalog,
    StaticRecipeDataSource,
    capture_context_snapshot,
    classify_progression_band,
    compute_state_digest,
    extract_difficulty_features,
    ratchet_progression_band,
    watermark_is_monotonic,
    _window_rate,
)
from fle.envd.models import ContractContextSnapshot

pytestmark = pytest.mark.no_factorio


RECIPES = [
    {
        "name": "iron-plate",
        "category": "smelting",
        "energy": 3.2,
        "ingredients": [{"name": "iron-ore", "amount": 1}],
        "products": [{"name": "iron-plate", "amount": 1}],
        "enabled": True,
    },
    {
        "name": "copper-plate",
        "category": "smelting",
        "energy": 3.2,
        "ingredients": [{"name": "copper-ore", "amount": 1}],
        "products": [{"name": "copper-plate", "amount": 1}],
        "enabled": True,
    },
    {
        "name": "steel-plate",
        "category": "smelting",
        "energy": 16.0,
        "ingredients": [{"name": "iron-plate", "amount": 5}],
        "products": [{"name": "steel-plate", "amount": 1}],
        "enabled": False,  # locked until researched
    },
    {
        "name": "iron-gear-wheel",
        "category": "crafting",
        "energy": 0.5,
        "ingredients": [{"name": "iron-plate", "amount": 2}],
        "products": [{"name": "iron-gear-wheel", "amount": 1}],
        "enabled": True,
    },
    {
        "name": "electronic-circuit",
        "category": "crafting",
        "energy": 0.5,
        "ingredients": [
            {"name": "iron-plate", "amount": 1},
            {"name": "copper-cable", "amount": 3},
        ],
        "products": [{"name": "electronic-circuit", "amount": 1}],
        "enabled": True,
    },
    {
        "name": "copper-cable",
        "category": "crafting",
        "energy": 0.5,
        "ingredients": [{"name": "copper-plate", "amount": 1}],
        "products": [{"name": "copper-cable", "amount": 2}],
        "enabled": True,
    },
]

TECHNOLOGIES = [
    {
        "name": "steel-processing",
        "prerequisites": [],
        "unlocked_recipes": ["steel-plate"],
        "unit_count": 25,
        "unit_energy": 30.0,
    },
]


def _catalog() -> ProductCatalog:
    return ProductCatalog(StaticRecipeDataSource(RECIPES, TECHNOLOGIES))


def _snapshot_kwargs(**overrides):
    fields = dict(
        session_id="session-1",
        epoch_index=0,
        captured_tick=1000,
        technology_ids=("electricity",),
        unlocked_recipe_ids=("iron-plate",),
        inventory_counts={"iron-plate": 100},
        placed_entity_counts={"stone-furnace": 4},
        production_rates_60s={},
        production_rates_300s={"iron-plate": 40.0},
        power_capacity_kw=300.0,
        power_utilization=0.4,
        logistic_network_count=0,
        train_stop_count=0,
        pollution_total=None,
        evolution_factor=None,
        map_seed_hash="seed-hash",
        state_digest="digest-placeholder",
    )
    fields.update(overrides)
    return fields


def _snapshot(**overrides) -> ContractContextSnapshot:
    snapshot = ContractContextSnapshot(**_snapshot_kwargs(**overrides))
    object.__setattr__(snapshot, "state_digest", _real_digest(snapshot))
    return snapshot


def _real_digest(snapshot: ContractContextSnapshot) -> str:
    return compute_state_digest(snapshot.model_dump())


# ---------------------------------------------------------------------------
# Snapshot determinism and watermarks
# ---------------------------------------------------------------------------


class FakeNamespace:
    """Minimal namespace surface for capture_context_snapshot."""

    def __init__(self):
        from fle.commons.models.research_state import ResearchState
        from fle.commons.models.technology_state import TechnologyState

        self._research_state = ResearchState(
            technologies={
                "electricity": TechnologyState(
                    name="electricity",
                    researched=True,
                    enabled=True,
                    level=1,
                    research_unit_count=1,
                    research_unit_energy=30.0,
                    prerequisites=[],
                    ingredients=[],
                )
            },
            current_research=None,
            research_progress=0.0,
            research_queue=[],
            progress={},
        )

    def _save_research_state(self):
        return self._research_state

    def inspect_inventory(self):
        return {"iron-plate": 42, "stone": 0}

    def _objective_telemetry(self, reset):
        return {
            "pollution_total": 12.5,
            "evolution_factor": 0.01,
            "produced": {"iron-plate": 600},
        }

    def _entity_census(self):
        return {
            "census": {
                "stone-furnace": {"working": 3, "no-power": 1},
                "transport-belt": {"normal": 8},
            }
        }

    def _get_production_stats(self):
        return {"output": {"iron-plate": 600}}


def test_capture_is_deterministic():
    namespace = FakeNamespace()
    first = capture_context_snapshot(
        namespace,
        session_id="s",
        epoch_index=0,
        captured_tick=500,
        map_seed_hash="msh",
        flow_history=[(0, {}), (200, {"iron-plate": 400})],
    )
    second = capture_context_snapshot(
        FakeNamespace(),
        session_id="s",
        epoch_index=0,
        captured_tick=500,
        map_seed_hash="msh",
        flow_history=[(0, {}), (200, {"iron-plate": 400})],
    )
    assert first.model_dump() == second.model_dump()
    assert first.state_digest == second.state_digest
    assert first.placed_entity_counts == {
        "stone-furnace": 4,
        "transport-belt": 8,
    }


def test_capture_watermark_rejects_regression():
    prior = ("s", 3, 900, "abc")
    # Same epoch index but earlier tick regresses.
    assert not watermark_is_monotonic(prior, ("s", 3, 800, "def"))
    # Later epoch always advances.
    assert watermark_is_monotonic(prior, ("s", 4, 10, "xyz"))
    # Different sessions never compare.
    assert not watermark_is_monotonic(prior, ("other", 9, 9_999_999, "q"))


def test_capture_computes_window_rates_passively():
    namespace = FakeNamespace()
    history = [(14000, {"iron-plate": 0.0})]
    snapshot = capture_context_snapshot(
        namespace,
        session_id="s",
        epoch_index=0,
        captured_tick=17600,  # one minute after base sample
        map_seed_hash="msh",
        flow_history=history,
    )
    # 600 plates produced over the one-minute window -> ~600/min.
    assert snapshot.production_rates_60s["iron-plate"] == pytest.approx(600.0, abs=0.5)


def test_window_rate_has_no_rate_for_a_single_cumulative_sample():
    assert _window_rate([(1000, {"iron-plate": 10_000.0})], 3600) == {}


def test_window_rate_uses_oldest_short_history_sample():
    rates = _window_rate(
        [
            (1000, {"iron-plate": 1000.0}),
            (1600, {"iron-plate": 1100.0}),
        ],
        3600,
    )
    # 100 plates over ten seconds is 600 plates/minute, not a cumulative
    # total divided by epsilon.
    assert rates["iron-plate"] == pytest.approx(600.0, abs=0.01)


# ---------------------------------------------------------------------------
# Progression bands
# ---------------------------------------------------------------------------


def test_band_table_tests():
    base = _snapshot()
    assert classify_progression_band(base) == 1  # electricity researched

    band2 = _snapshot(
        technology_ids=("electricity", "oil-processing"),
    )
    assert classify_progression_band(band2) == 2

    band3 = _snapshot(
        technology_ids=("electricity", "robotics"),
    )
    assert classify_progression_band(band3) >= 3

    silo = _snapshot(placed_entity_counts={"rocket-silo": 1})
    assert classify_progression_band(silo) == 4

    endgame = _snapshot(
        technology_ids=(
            "electricity",
            "space-science-pack",
            "prod-effectivity-module-3",
        ),
        production_rates_300s={"space-science-pack": 2.0},
    )
    assert classify_progression_band(endgame) == 5

    bootstrap = _snapshot(
        technology_ids=(),
        placed_entity_counts={},
    )
    assert classify_progression_band(bootstrap) == 0


def test_band_ratchet_never_moves_backward():
    assert ratchet_progression_band(3, 1) == 3
    assert ratchet_progression_band(1, 4) == 4


def test_inventory_consumption_does_not_demote_band():
    rich = _snapshot(
        technology_ids=("electricity",),
        inventory_counts={"iron-plate": 5000},
    )
    consumed = _snapshot(
        technology_ids=("electricity",),
        inventory_counts={},
    )
    assert classify_progression_band(rich) == classify_progression_band(consumed)


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------


def test_features_deterministic_and_complete():
    context = _snapshot()
    catalog = _catalog()
    kwargs = dict(
        snapshot=context,
        product_id="engine-unit" if False else "electronic-circuit",
        quantity=500,
        deadline_ticks=36000,
        catalog=catalog,
    )
    first = extract_difficulty_features(**kwargs)
    second = extract_difficulty_features(**kwargs)
    assert first.model_dump() == second.model_dump()
    assert first.recipe_depth == 3  # circuit -> cable -> copper-plate -> ore
    assert first.required_rate_per_minute == pytest.approx(
        500 / (36000 / 3600), rel=1e-3
    )


def test_more_inventory_never_increases_difficulty():
    catalog = _catalog()
    poor = extract_difficulty_features(
        snapshot=_snapshot(inventory_counts={}),
        product_id="electronic-circuit",
        quantity=500,
        deadline_ticks=36000,
        catalog=catalog,
    )
    rich = extract_difficulty_features(
        snapshot=_snapshot(inventory_counts={"electronic-circuit": 250}),
        product_id="electronic-circuit",
        quantity=500,
        deadline_ticks=36000,
        catalog=catalog,
    )
    assert rich.inventory_coverage_ratio == pytest.approx(0.5, abs=1e-6)
    assert rich.inventory_coverage_ratio > poor.inventory_coverage_ratio


def test_locked_recipe_counts_missing_technology():
    catalog = _catalog()
    features = extract_difficulty_features(
        snapshot=_snapshot(),
        product_id="steel-plate",
        quantity=200,
        deadline_ticks=36000,
        catalog=catalog,
    )
    assert features.missing_technology_count >= 1


def test_absent_product_raises_game_data_error():
    with pytest.raises(GameDataError):
        _catalog().require("nonexistent-product")


def test_cyclic_recipes_do_not_recurse_forever():
    cyclic = [
        {
            "name": "a-item",
            "category": "crafting",
            "energy": 1.0,
            "ingredients": [{"name": "b-item", "amount": 1}],
            "products": [{"name": "a-item", "amount": 1}],
        },
        {
            "name": "b-item",
            "category": "crafting",
            "energy": 1.0,
            "ingredients": [{"name": "a-item", "amount": 1}],
            "products": [{"name": "b-item", "amount": 1}],
        },
    ]
    catalog = ProductCatalog(StaticRecipeDataSource(cyclic))
    facts = catalog.require("a-item")
    assert facts.cyclic is True
    assert facts.depth >= 1  # finite despite the cycle
