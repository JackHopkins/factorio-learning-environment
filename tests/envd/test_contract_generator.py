"""Property tests for deterministic generation, commitments, and rejections."""

import json

import pytest
from pydantic import ValidationError

from fle.envd.contract_features import ProductCatalog, StaticRecipeDataSource
from fle.envd.contract_generator import (
    ANALYTIC_SAFETY_FACTOR,
    DEFAULT_TEMPLATE_BANK,
    MACHINE_SETUP_SECONDS_PER_CATEGORY,
    STAGE_REFERENCE_RATES,
    analytic_feasibility,
    build_epoch_spec,
    context_band,
    generate_candidates,
    round_to_batch,
)
from fle.envd.contract_rating import UncalibratedDifficultyModel
from fle.envd.models import (
    ContractContextSnapshot,
)

pytestmark = pytest.mark.no_factorio


RECIPES = [
    {
        "name": name,
        "category": category,
        "energy": energy,
        "ingredients": ingredients,
        "products": [{"name": name, "amount": 1}],
        "enabled": enabled,
    }
    for name, category, energy, ingredients, enabled in [
        ("iron-plate", "smelting", 3.2, [{"name": "iron-ore", "amount": 1}], True),
        ("copper-plate", "smelting", 3.2, [{"name": "copper-ore", "amount": 1}], True),
        ("steel-plate", "smelting", 16.0, [{"name": "iron-plate", "amount": 5}], False),
        ("stone-brick", "smelting", 3.2, [{"name": "stone", "amount": 2}], True),
        (
            "iron-gear-wheel",
            "crafting",
            0.5,
            [{"name": "iron-plate", "amount": 2}],
            True,
        ),
        (
            "electronic-circuit",
            "crafting",
            0.5,
            [
                {"name": "iron-plate", "amount": 1},
                {"name": "copper-cable", "amount": 3},
            ],
            True,
        ),
        (
            "copper-cable",
            "crafting",
            0.5,
            [{"name": "copper-plate", "amount": 1}],
            True,
        ),
        (
            "advanced-circuit",
            "crafting",
            6.0,
            [
                {"name": "electronic-circuit", "amount": 2},
                {"name": "plastic-bar", "amount": 2},
            ],
            False,
        ),
        ("plastic-bar", "crafting", 1.0, [{"name": "coal", "amount": 1}], False),
    ]
]

CATALOG = ProductCatalog(StaticRecipeDataSource(RECIPES))


def _context(**overrides) -> ContractContextSnapshot:
    fields = dict(
        session_id="s",
        epoch_index=0,
        captured_tick=1000,
        technology_ids=("electricity",),
        unlocked_recipe_ids=("iron-plate",),
        inventory_counts={"iron-plate": 50},
        placed_entity_counts={"stone-furnace": 4},
        production_rates_60s={},
        production_rates_300s={"iron-plate": 40.0, "copper-plate": 20.0},
        power_capacity_kw=300.0,
        power_utilization=0.4,
        logistic_network_count=0,
        train_stop_count=0,
        pollution_total=None,
        evolution_factor=None,
        map_seed_hash="msh",
        state_digest="digest",
    )
    fields.update(overrides)
    return ContractContextSnapshot(**fields)


MODEL = UncalibratedDifficultyModel()


def test_generation_is_byte_deterministic():
    template = DEFAULT_TEMPLATE_BANK.get("consolidate-smelting")
    kwargs = dict(
        template=template,
        generation_seed=1234,
        context=_context(),
        catalog=CATALOG,
        difficulty_model=MODEL,
        pool_size=4,
    )
    first = generate_candidates(**kwargs)
    second = generate_candidates(**kwargs)
    assert [c.model_dump(mode="json") for c in first] == [
        c.model_dump(mode="json") for c in second
    ]


def test_different_seed_changes_the_pool():
    template = DEFAULT_TEMPLATE_BANK.get("consolidate-smelting")
    kwargs = dict(
        template=template,
        context=_context(),
        catalog=CATALOG,
        difficulty_model=MODEL,
        pool_size=6,
    )
    first = [c.model_dump() for c in generate_candidates(generation_seed=1, **kwargs)]
    second = [c.model_dump() for c in generate_candidates(generation_seed=2, **kwargs)]
    assert first != second


def test_context_change_changes_candidates():
    """Generation is a pure function of context too (state digest input)."""
    template = DEFAULT_TEMPLATE_BANK.get("consolidate-smelting")
    kwargs = dict(
        template=template,
        generation_seed=7,
        catalog=CATALOG,
        difficulty_model=MODEL,
        pool_size=6,
    )
    base = [c.model_dump() for c in generate_candidates(context=_context(), **kwargs)]
    changed = [
        c.model_dump()
        for c in generate_candidates(
            context=_context(production_rates_300s={"iron-plate": 900.0}), **kwargs
        )
    ]
    assert base != changed


def test_commitment_binds_every_field_and_is_immutable():
    candidates = generate_candidates(
        template=DEFAULT_TEMPLATE_BANK.get("consolidate-smelting"),
        generation_seed=42,
        context=_context(),
        catalog=CATALOG,
        difficulty_model=MODEL,
        pool_size=3,
    )
    accepted = [c for c in candidates if c.accepted]
    assert accepted, "expected at least one feasible candidate"
    spec = build_epoch_spec(
        session_id="session",
        epoch_index=0,
        selection_seed=99,
        candidate=accepted[0],
        context=_context(),
        benchmark_version="bv-test",
        calibration_version="uncalibrated",
    )
    canonical = json.dumps(
        spec.model_dump(exclude={"commitment_hash"}, mode="json"), sort_keys=True
    )
    # Round-trip through JSON preserves the commitment.
    reparsed = type(spec).model_validate_json(spec.model_dump_json())
    assert reparsed.commitment_hash == spec.commitment_hash
    assert (
        json.dumps(
            reparsed.model_dump(exclude={"commitment_hash"}, mode="json"),
            sort_keys=True,
        )
        == canonical
    )
    _ = canonical

    # A parsed, tampered specification fails validation because the hash is
    # re-derived and compared on load.
    tampered_payload = json.loads(spec.model_dump_json())
    tampered_payload["quantity"] += 1
    with pytest.raises(ValidationError):
        type(spec).model_validate(tampered_payload)


def test_deadline_respects_analytic_lower_bound():
    template = DEFAULT_TEMPLATE_BANK.get("stress-throughput-scaling")
    candidates = generate_candidates(
        template=template,
        generation_seed=5,
        context=_context(),
        catalog=CATALOG,
        difficulty_model=MODEL,
        pool_size=6,
        remaining_session_ticks=None,
    )
    accepted = [c for c in candidates if c.accepted]
    for candidate in accepted:
        floor = int(candidate.analytic_minimum_ticks * ANALYTIC_SAFETY_FACTOR)
        assert candidate.deadline_ticks >= floor * 1.05 - 1


def test_locked_products_are_rejected_with_reasons():
    template = DEFAULT_TEMPLATE_BANK.get("frontier-circuits")
    candidates = generate_candidates(
        template=template,
        generation_seed=11,
        context=_context(inventory_counts={}),
        catalog=CATALOG,
        difficulty_model=MODEL,
        pool_size=8,
    )
    advanced = [c for c in candidates if c.item_name == "advanced-circuit"]
    assert advanced, "advanced-circuit should appear in the frontier pool"
    assert all(c.rejection_reason == "recipe_locked" for c in advanced)


def test_disabled_frontier_recipe_with_known_technology_is_researchable_but_large_orders_defer():
    catalog = ProductCatalog(
        StaticRecipeDataSource(
            RECIPES,
            technologies=[
                {
                    "name": "advanced-circuit-tech",
                    "prerequisites": [],
                    "unlocked_recipes": ["advanced-circuit"],
                    "unit_count": 10,
                    "unit_energy": 30.0,
                }
            ],
        )
    )
    candidates = generate_candidates(
        template=DEFAULT_TEMPLATE_BANK.get("frontier-circuits"),
        generation_seed=17,
        context=_context(inventory_counts={}),
        catalog=catalog,
        difficulty_model=MODEL,
        pool_size=8,
    )
    advanced = [c for c in candidates if c.item_name == "advanced-circuit"]
    assert advanced
    # The recipe is analytically researchable, but the generated quantities
    # would require a commissioning window beyond the bounded epoch cap. It
    # must be deferred as oversized rather than reported as recipe-locked.
    assert all(c.rejection_reason == "analytic_too_large" for c in advanced)
    assert all(c.rejection_reason != "recipe_locked" for c in advanced)


def test_frontier_targets_exactly_one_band_ahead():
    bootstrap = _context(
        technology_ids=(),
        placed_entity_counts={"stone-furnace": 1},
        state_digest="bootstrap",
    )
    assert (
        context_band(bootstrap, DEFAULT_TEMPLATE_BANK.get("consolidate-smelting")) == 0
    )
    assert (
        context_band(bootstrap, DEFAULT_TEMPLATE_BANK.get("frontier-early-automation"))
        == 1
    )


def test_technology_prerequisites_and_machine_setup_are_in_deadline_floor():
    catalog = ProductCatalog(
        StaticRecipeDataSource(
            RECIPES,
            technologies=[
                {
                    "name": "electricity",
                    "prerequisites": [],
                    "unlocked_recipes": [],
                    "unit_count": 10,
                    "unit_energy": 30.0,
                },
                {
                    "name": "advanced-circuit-tech",
                    "prerequisites": ["electricity"],
                    "unlocked_recipes": ["advanced-circuit"],
                    "unit_count": 20,
                    "unit_energy": 30.0,
                },
            ],
        )
    )
    facts = catalog.require("advanced-circuit")
    assert facts.enabling_technologies == {
        "electricity",
        "advanced-circuit-tech",
    }
    without_machine = analytic_feasibility(
        catalog,
        "advanced-circuit",
        1,
        _context(technology_ids=(), placed_entity_counts={}),
    )
    with_machine = analytic_feasibility(
        catalog,
        "advanced-circuit",
        1,
        _context(
            technology_ids=(),
            placed_entity_counts={"assembling-machine-1": 1},
        ),
    )
    assert without_machine - with_machine >= int(
        MACHINE_SETUP_SECONDS_PER_CATEGORY * 60
    )


def test_consolidation_pool_always_includes_an_unproduced_same_band_product():
    candidates = generate_candidates(
        template=DEFAULT_TEMPLATE_BANK.get("consolidate-smelting"),
        generation_seed=91,
        context=_context(production_rates_300s={"iron-plate": 40.0}),
        catalog=CATALOG,
        difficulty_model=MODEL,
        pool_size=3,
    )
    assert candidates[0].item_name in {"copper-plate", "stone-brick"}
    assert {candidate.item_name for candidate in candidates} == {
        "iron-plate",
        "copper-plate",
        "stone-brick",
    }


def test_inventory_covered_orders_are_rejected():
    template = DEFAULT_TEMPLATE_BANK.get("consolidate-smelting")
    # Flood every unlocked smelting product so any drawn candidate either
    # sits fully in inventory or is locked.
    context = _context(
        inventory_counts={
            "iron-plate": 10**7,
            "copper-plate": 10**7,
            "stone-brick": 10**7,
        }
    )
    candidates = generate_candidates(
        template=template,
        generation_seed=3,
        context=context,
        catalog=CATALOG,
        difficulty_model=MODEL,
        pool_size=8,
    )
    assert candidates
    for candidate in candidates:
        if candidate.rejection_reason == "recipe_locked":
            continue
        assert candidate.rejection_reason == "inventory_already_covers", (
            candidate.item_name,
            candidate.rejection_reason,
        )


def test_family_repetition_cap_rejects():
    template = DEFAULT_TEMPLATE_BANK.get("consolidate-smelting")
    candidates = generate_candidates(
        template=template,
        generation_seed=21,
        context=_context(),
        catalog=CATALOG,
        difficulty_model=MODEL,
        pool_size=6,
        recent_family_counts={"smelting": 99},
        family_repetition_cap=3,
    )
    assert all(c.rejection_reason == "family_repetition_cap" for c in candidates)


def test_session_horizon_rejection():
    template = DEFAULT_TEMPLATE_BANK.get("consolidate-smelting")
    candidates = generate_candidates(
        template=template,
        generation_seed=31,
        context=_context(),
        catalog=CATALOG,
        difficulty_model=MODEL,
        pool_size=6,
        remaining_session_ticks=60,
    )
    assert candidates
    assert all(c.rejection_reason == "exceeds_session_horizon" for c in candidates)


def test_calibration_envelope_rejection():
    template = DEFAULT_TEMPLATE_BANK.get("consolidate-smelting")
    candidates = generate_candidates(
        template=template,
        generation_seed=41,
        context=_context(),
        catalog=CATALOG,
        difficulty_model=MODEL,
        pool_size=6,
        calibration_envelope={
            "log_quantity": (-100.0, -90.0),  # impossible to satisfy
        },
    )
    assert all(c.rejection_reason == "outside_calibration_envelope" for c in candidates)


def test_template_rejects_orders_outside_current_stage_band():
    template = DEFAULT_TEMPLATE_BANK.get("consolidate-smelting")
    candidates = generate_candidates(
        template=template,
        generation_seed=42,
        context=_context(
            placed_entity_counts={"rocket-silo": 1}, state_digest="rocket-stage"
        ),
        catalog=CATALOG,
        difficulty_model=MODEL,
        pool_size=4,
    )
    assert candidates
    assert all(c.rejection_reason == "stage_band_unsupported" for c in candidates)


def test_rejection_reasons_are_persisted_on_candidates():
    template = DEFAULT_TEMPLATE_BANK.get("consolidate-smelting")
    candidates = generate_candidates(
        template=template,
        generation_seed=51,
        context=_context(
            inventory_counts={
                "iron-plate": 10**9,
                "copper-plate": 10**9,
                "stone-brick": 10**9,
            }
        ),
        catalog=CATALOG,
        difficulty_model=MODEL,
        pool_size=6,
    )
    rejected = [c for c in candidates if not c.accepted]
    assert rejected
    payload = json.dumps([c.model_dump(mode="json") for c in rejected])
    assert "inventory_already_covers" in payload


def test_higher_pressure_templates_order_larger_quantities():
    consolidation = DEFAULT_TEMPLATE_BANK.get("consolidate-smelting")
    stress = DEFAULT_TEMPLATE_BANK.get("stress-throughput-scaling")

    def median_quantity(template):
        quantities = sorted(
            c.quantity
            for c in generate_candidates(
                template=template,
                generation_seed=77,
                context=_context(),
                catalog=CATALOG,
                difficulty_model=UncalibratedDifficultyModel(),
                pool_size=8,
            )
            if c.accepted
        )
        return quantities[len(quantities) // 2] if quantities else 0

    assert median_quantity(stress) >= median_quantity(consolidation)


def test_baseline_rate_uses_stage_reference_when_unmeasured():
    from fle.envd.contract_generator import baseline_rate

    unmeasured = baseline_rate(_context(production_rates_300s={}), "iron-plate", 1)
    assert unmeasured == STAGE_REFERENCE_RATES[1]


def test_batch_rounding_granularities():
    assert round_to_batch(50) == 50
    assert round_to_batch(1234) % 100 == 0
    assert round_to_batch(23456) % 500 == 0
    assert round_to_batch(0.4) == 1


def test_bank_template_ids_unique_and_mixture_complete():
    templates = DEFAULT_TEMPLATE_BANK.all()
    ids = [t.template_id for t in templates]
    assert len(ids) == len(set(ids))
    classes = {t.mixture_class for t in templates}
    assert classes == {"consolidation", "frontier", "stress"}
