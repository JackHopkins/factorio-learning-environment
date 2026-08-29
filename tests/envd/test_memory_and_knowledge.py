import json

import pytest

from fle.envd.capability_graph import build_capability_graph, compare_capability_snapshots
from fle.envd.contract_features import ProductCatalog, StaticRecipeDataSource
from fle.envd.contract_generator import ContractCandidate
from fle.envd.follow_up import choose_follow_up_candidate
from fle.envd.knowledge import ApiReference, GameDataReference, load_game_data
from fle.envd.memory import MemoryConflict, MemoryNotFound, SessionMemory
from fle.envd.models import (
    CapabilityDelta,
    ContractContextSnapshot,
    ContractDifficultyFeatures,
    ContractEpochOutcome,
    ContractEpochSpec,
)


pytestmark = pytest.mark.no_factorio


def _snapshot(*, digest: str, tick: int, techs=(), unlocked=(), rates=None, entities=None):
    return ContractContextSnapshot(
        session_id="session",
        epoch_index=1,
        captured_tick=tick,
        technology_ids=tuple(techs),
        unlocked_recipe_ids=tuple(unlocked),
        inventory_counts={},
        placed_entity_counts=entities or {},
        production_rates_60s=rates or {},
        production_rates_300s=rates or {},
        power_capacity_kw=100.0,
        power_utilization=0.2,
        logistic_network_count=0,
        train_stop_count=0,
        pollution_total=None,
        evolution_factor=None,
        map_seed_hash="map",
        state_digest=digest,
    )


def _catalog():
    return ProductCatalog(
        StaticRecipeDataSource(
            [
                {
                    "name": "iron-plate",
                    "category": "smelting",
                    "energy": 3.2,
                    "ingredients": [{"name": "iron-ore", "amount": 1}],
                    "products": [{"name": "iron-plate", "amount": 1}],
                    "enabled": True,
                },
                {
                    "name": "steel-plate",
                    "category": "smelting",
                    "energy": 16,
                    "ingredients": [{"name": "iron-plate", "amount": 5}],
                    "products": [{"name": "steel-plate", "amount": 1}],
                    "enabled": False,
                },
            ],
            [{"name": "steel-processing", "prerequisites": [], "unlocked_recipes": ["steel-plate"]}],
            game_version="2.0.73",
        )
    )


def test_session_memory_is_revisioned_and_traceable():
    memory = SessionMemory(max_entries=4)
    first = memory.write("plan/current", "build iron then steel")
    assert first.entry is not None
    assert first.entry.revision == 1
    second = memory.write("plan/current", "steel is blocked", expected_revision=1)
    assert second.entry is not None
    assert second.entry.revision == 2
    assert memory.search("steel").results[0].key == "plan/current"
    with pytest.raises(MemoryConflict):
        memory.write("plan/current", "stale", expected_revision=1)
    deleted = memory.delete("plan/current", expected_revision=2)
    assert deleted.entry is None
    assert deleted.mutation.revision == 3
    assert memory.trace().total == 3
    with pytest.raises(MemoryNotFound):
        memory.read("plan/current")


def test_game_data_reference_resolves_canonical_ids_and_unlock_path():
    game = GameDataReference(
        {
            "factorio_version": "2.0.73",
            "recipes": [
                {
                    "name": "iron-plate",
                    "category": "smelting",
                    "ingredients": [{"name": "iron-ore", "amount": 1}],
                    "products": [{"name": "iron-plate", "amount": 1}],
                },
                {
                    "name": "steel-plate",
                    "category": "smelting",
                    "ingredients": [{"name": "iron-plate", "amount": 5}],
                    "products": [{"name": "steel-plate", "amount": 1}],
                },
            ],
            "technologies": [
                {"name": "steel-processing", "prerequisites": ["automation"], "unlocked_recipes": ["steel-plate"]},
                {"name": "automation", "prerequisites": [], "unlocked_recipes": []},
            ],
            "prototypes": [
                {"name": "steel-furnace", "type": "furnace", "crafting_categories": ["smelting"]},
                {"name": "lab", "type": "lab", "crafting_categories": []},
            ],
        }
    )
    recipe = game.recipe("steel-plate")
    assert recipe["canonical_id"] == "steel-plate"
    assert recipe["data"]["unlocked_by"] == ["steel-processing"]
    path = game.unlock_path("steel-plate")
    assert path["data"]["technology_closure"] == ["automation", "steel-processing"]
    machines = game.machine_requirements("steel-plate")
    assert machines["data"]["machine_prototypes"] == ["steel-furnace"]
    lab = game.prototype("Prototype.Lab")
    assert lab["canonical_id"] == "lab"
    assert game.search("steel", kinds=["recipe", "technology"])["results"]


def test_game_data_reference_resolves_barrel_alias_and_reports_fluid_ambiguity():
    game = GameDataReference(
        {
            "factorio_version": "2.0.73",
            "recipes": [
                {
                    "name": "lubricant-barrel",
                    "category": "crafting-with-fluid",
                    "ingredients": [],
                    "products": [{"name": "lubricant-barrel", "amount": 1}],
                },
                {
                    "name": "basic-oil-processing",
                    "category": "oil-processing",
                    "ingredients": [],
                    "products": [{"name": "petroleum-gas", "amount": 45}],
                },
                {
                    "name": "advanced-oil-processing",
                    "category": "oil-processing",
                    "ingredients": [],
                    "products": [{"name": "petroleum-gas", "amount": 55}],
                },
            ],
            "technologies": [],
        }
    )
    recipe = game.recipe("fill-lubricant-barrel")
    assert recipe["canonical_id"] == "lubricant-barrel"
    assert recipe["data"]["requested_id"] == "fill-lubricant-barrel"
    assert "fill-lubricant-barrel" in recipe["data"]["aliases"]

    with pytest.raises(KeyError, match="ambiguous") as error:
        game.recipe("petroleum-gas")
    assert "basic-oil-processing" in str(error.value)
    assert "advanced-oil-processing" in str(error.value)
    assert game.search("fill-lubricant-barrel", kinds=["recipe"])["results"]


def test_checked_in_game_export_contains_prototype_and_exact_oil_facts():
    game, source = load_game_data()
    assert source.endswith("factorio-2.0.73-contract-game-data.json")
    assert game.prototype("Prototype.Lab")["data"]["type"] == "lab"
    assert game.recipe("RecipeName.FillLubricantBarrel")["canonical_id"] == (
        "lubricant-barrel"
    )
    with pytest.raises(KeyError, match="ambiguous"):
        game.recipe("petroleum-gas")


def test_api_reference_contains_all_tool_manuals():
    reference = ApiReference()
    ids = set(reference.documents)
    assert "api/overview" in ids
    assert "api/agent/insert_item" in ids
    assert "api/agent/get_prototype_recipe" in ids
    search = reference.search("insert_item", kinds=["api"])
    assert any(item["document_id"] == "api/agent/insert_item" for item in search["results"])
    page = reference.read("api/agent/insert_item")
    assert page["content"]


def test_capability_graph_delta_records_progress_without_rating_credit():
    catalog = _catalog()
    before = _snapshot(digest="before", tick=100, entities={"stone-furnace": 1})
    after = _snapshot(
        digest="after",
        tick=200,
        techs=("steel-processing",),
        unlocked=("steel-plate",),
        rates={"iron-plate": 60.0},
        entities={"stone-furnace": 2},
    )
    graph = build_capability_graph(after, catalog, target_product="steel-plate")
    assert any(node.node_id == "technology:steel-processing" for node in graph.nodes)
    delta = compare_capability_snapshots(
        before, after, target_product="steel-plate", catalog=catalog
    )
    assert delta.meaningful_progress is True
    assert delta.new_technologies == ("steel-processing",)
    assert delta.path_progress > 0


def _candidate(item: str, quantity: int, deadline: int, *, mixture: str = "frontier"):
    features = ContractDifficultyFeatures(
        product_id=item,
        product_tier=1,
        recipe_depth=2 if item == "steel-plate" else 1,
        missing_technology_count=0,
        missing_machine_type_count=0,
        required_new_intermediate_count=0,
        log_quantity=3.0,
        deadline_ticks=deadline,
        required_rate_per_minute=30.0,
        existing_rate_per_minute=0.0,
        inventory_coverage_ratio=0.0,
        estimated_power_fraction=0.1,
        transport_complexity=0.0,
        stage_band=1,
    )
    return ContractCandidate(
        template_id=f"{mixture}-{item}",
        mixture_class=mixture,
        generation_seed=1,
        item_name=item,
        quantity=quantity,
        deadline_ticks=deadline,
        analytic_minimum_ticks=deadline // 2,
        features=features,
        raw_difficulty=1.0,
        state_advantage=0.0,
        effective_difficulty=1.0,
    )


def _previous_spec() -> ContractEpochSpec:
    context = _snapshot(digest="order-before", tick=100)
    features = ContractDifficultyFeatures(
        product_id="steel-plate",
        product_tier=1,
        recipe_depth=2,
        missing_technology_count=1,
        missing_machine_type_count=0,
        required_new_intermediate_count=1,
        log_quantity=4.6,
        deadline_ticks=3600,
        required_rate_per_minute=100.0,
        existing_rate_per_minute=0.0,
        inventory_coverage_ratio=0.0,
        estimated_power_fraction=0.1,
        transport_complexity=0.0,
        stage_band=1,
    )
    return ContractEpochSpec.create(
        session_id="session",
        epoch_index=1,
        template_id="frontier-steel",
        mixture_class="frontier",
        generation_seed=1,
        selection_seed=1,
        item_name="steel-plate",
        quantity=100,
        deadline_ticks=3600,
        context=context,
        features=features,
        raw_difficulty=1.0,
        state_advantage=0.0,
        effective_difficulty=1.0,
    )


def _outcome(status: str, delivered: int = 0) -> ContractEpochOutcome:
    return ContractEpochOutcome(
        session_id="session",
        epoch_index=1,
        commitment_hash="commitment",
        status=status,
        delivered_quantity=delivered,
        requested_quantity=100,
        completion_ratio=delivered / 100,
        simulation_ticks_used=3600,
        interventions_used=1,
        model_seconds=1.0,
        tool_seconds=1.0,
        runner_wall_seconds=1.0,
        terminal_state_digest="after",
    )


def test_follow_up_repeats_frontier_after_capability_progress():
    selected, follow_up = choose_follow_up_candidate(
        [_candidate("steel-plate", 80, 4500)],
        previous_spec=_previous_spec(),
        previous_outcome=_outcome("expired"),
        capability_delta=CapabilityDelta(
            before_state_digest="before",
            after_state_digest="after",
            target_id="steel-plate",
            new_technologies=("steel-processing",),
            meaningful_progress=True,
            path_progress=1,
        ),
        catalog=_catalog(),
        selection_seed=7,
    )
    assert selected is not None and selected.item_name == "steel-plate"
    assert follow_up is not None
    assert follow_up.reason == "frontier_progress_repeat"


def test_follow_up_backs_off_to_dependency_after_zero_progress():
    selected, follow_up = choose_follow_up_candidate(
        [_candidate("steel-plate", 80, 4500), _candidate("iron-plate", 30, 5000, mixture="consolidation")],
        previous_spec=_previous_spec(),
        previous_outcome=_outcome("expired"),
        capability_delta=None,
        catalog=_catalog(),
        selection_seed=7,
    )
    assert selected is not None and selected.item_name == "iron-plate"
    assert follow_up is not None and follow_up.reason == "zero_progress_backoff"


def test_zero_delivery_partial_backs_off_instead_of_claiming_capacity():
    selected, follow_up = choose_follow_up_candidate(
        [
            _candidate("steel-plate", 80, 4500),
            _candidate("iron-plate", 30, 5000, mixture="consolidation"),
        ],
        previous_spec=_previous_spec(),
        previous_outcome=_outcome("partial", delivered=0),
        capability_delta=None,
        catalog=_catalog(),
        selection_seed=7,
    )
    assert selected is not None and selected.item_name == "iron-plate"
    assert follow_up is not None and follow_up.reason == "zero_progress_backoff"


def test_follow_up_partial_repeats_near_delivered_capacity():
    selected, follow_up = choose_follow_up_candidate(
        [_candidate("steel-plate", 50, 4500), _candidate("steel-plate", 100, 4500)],
        previous_spec=_previous_spec(),
        previous_outcome=_outcome("partial", delivered=40),
        capability_delta=None,
        catalog=_catalog(),
        selection_seed=7,
    )
    assert selected is not None and selected.item_name == "steel-plate"
    assert selected.quantity == 50
    assert follow_up is not None and follow_up.reason == "partial_near_capacity"
