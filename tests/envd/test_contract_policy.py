import random

import pytest

from fle.envd.contract_features import ProductCatalog, StaticRecipeDataSource
from fle.envd.contract_generator import (
    ContractCandidate,
    _features_for,
    build_epoch_spec,
)
from fle.envd.contract_policy import (
    EvidenceDrivenCustomerPolicy,
    INTENTS,
    MAX_COMMISSIONING_DEADLINE_TICKS,
    ProductEvidence,
)
from fle.envd.capability_graph import compare_capability_snapshots
from fle.envd.contract_rating import UncalibratedDifficultyModel
from fle.envd.models import (
    ADAPTIVE_BENCHMARK_VERSION,
    CapabilityDelta,
    CapabilityRating,
    CONTRACT_CALIBRATION_VERSION,
    ContractContextSnapshot,
    ContractEpochOutcome,
    ThroughputAuditResult,
    ProductDemandSpec,
)

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
        "name": "copper-cable",
        "category": "crafting",
        "energy": 0.5,
        "ingredients": [{"name": "copper-plate", "amount": 1}],
        "products": [{"name": "copper-cable", "amount": 2}],
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
]


def _context(**rates):
    return ContractContextSnapshot(
        session_id="s",
        epoch_index=1,
        captured_tick=0,
        technology_ids=("automation-science-pack",),
        unlocked_recipe_ids=(),
        inventory_counts={},
        placed_entity_counts={"stone-furnace": 2},
        production_rates_60s=rates,
        production_rates_300s=rates,
        power_capacity_kw=0,
        power_utilization=0,
        logistic_network_count=0,
        train_stop_count=0,
        pollution_total=None,
        evolution_factor=None,
        map_seed_hash="m",
        state_digest="d",
    )


def _candidate(catalog, context, product, band, mixture):
    features = _features_for(context, product, 1000, 100000, catalog, band)
    return ContractCandidate(
        template_id=f"{mixture}-{product}",
        mixture_class=mixture,
        generation_seed=1,
        item_name=product,
        quantity=1000,
        deadline_ticks=100000,
        analytic_minimum_ticks=1000,
        features=features,
        raw_difficulty=5,
        state_advantage=0,
        effective_difficulty=5,
        family="test",
    )


def _setup():
    catalog = ProductCatalog(StaticRecipeDataSource(RECIPES))
    context = _context()
    pool = [
        _candidate(catalog, context, "iron-plate", 0, "consolidation"),
        _candidate(catalog, context, "copper-plate", 0, "consolidation"),
        _candidate(catalog, context, "electronic-circuit", 1, "frontier"),
    ]
    return catalog, context, pool


def test_unseen_frontier_is_a_commissioning_batch_not_stage_rate_bulk():
    catalog, context, pool = _setup()
    policy = EvidenceDrivenCustomerPolicy()
    circuit = pool[-1]

    quantity, deadline, evidence = policy._size_line(
        circuit, "commissioning", context, catalog, __import__("random").Random(1)
    )

    assert quantity > 0
    assert deadline <= MAX_COMMISSIONING_DEADLINE_TICKS
    assert evidence["basis"] == "commissioning_cold_start"


def test_recent_product_rotates_when_an_equivalent_alternative_exists():
    catalog, context, pool = _setup()
    policy = EvidenceDrivenCustomerPolicy()
    policy.records["copper-plate"] = ProductEvidence(
        "copper-plate", attempts=1, last_epoch=1, completion_scores=[0.8]
    )
    policy.recent_products.append("copper-plate")
    policy.completed_epochs = 1

    plan = policy.choose(
        pool,
        context=context,
        catalog=catalog,
        difficulty_model=UncalibratedDifficultyModel(),
        selection_seed=2,
    )

    assert plan.products[0].product == "iron-plate"


def test_policy_can_emit_mixed_and_sustained_orders_from_evidence():
    catalog, context, pool = _setup()
    policy = EvidenceDrivenCustomerPolicy()
    for product in ("iron-plate", "copper-plate"):
        policy.records[product] = ProductEvidence(
            product,
            attempts=3,
            fulfilled=1,
            last_epoch=2,
            completion_scores=[0.6, 0.9, 1.0],
            delivered_rates=[20, 25, 30],
            sustained_depot_count=1,
            sustained_window_rates=[20, 25, 30],
        )
    policy.completed_epochs = 3

    plans = [
        policy.choose(
            pool,
            context=context,
            catalog=catalog,
            difficulty_model=UncalibratedDifficultyModel(),
            selection_seed=seed,
        )
        for seed in range(40)
    ]

    assert any(len(plan.products) == 2 for plan in plans)
    assert any(plan.order_kind == "sustained" for plan in plans)
    assert all(line.quantity > 0 for plan in plans for line in plan.products)
    mixed = next(plan for plan in plans if len(plan.products) == 2)
    assert all(
        "effective_difficulty" in line_evidence
        for line_evidence in mixed.evidence["lines"].values()
    )


def test_throughput_uses_sustained_depot_lcb_and_keeps_zero_windows():
    catalog, context, pool = _setup()
    policy = EvidenceDrivenCustomerPolicy()
    candidate = pool[0]
    policy.records[candidate.item_name] = ProductEvidence(
        candidate.item_name,
        attempts=2,
        completion_scores=[0.5, 1.0],
        positive_delivery_count=2,
        delivered_rates=[120.0, 120.0],
        sustained_depot_count=1,
        sustained_window_scores=[1.0, 0.0],
        sustained_window_rates=[120.0, 0.0],
    )

    _, _, evidence = policy._size_line(
        candidate, "throughput", context, catalog, __import__("random").Random(1)
    )

    assert evidence["basis"] == "sustained_depot_throughput_lcb"
    assert evidence["depot_rate_lcb"] < 60.0
    assert evidence["target_rate"] < 60.0


def test_stateful_policy_sequence_preserves_breadth_and_scales_from_evidence():
    catalog, context, pool = _setup()
    policy = EvidenceDrivenCustomerPolicy()
    plans = []

    for epoch in range(1, 11):
        seed = epoch * 991
        plan = policy.choose(
            pool,
            context=context,
            catalog=catalog,
            difficulty_model=UncalibratedDifficultyModel(),
            selection_seed=seed,
        )
        spec = build_epoch_spec(
            session_id="sequence",
            epoch_index=epoch,
            selection_seed=seed,
            candidate=plan.candidate,
            context=context,
            benchmark_version=ADAPTIVE_BENCHMARK_VERSION,
            calibration_version=CONTRACT_CALIBRATION_VERSION,
            order_kind=plan.order_kind,
            products=plan.products,
            policy_evidence=plan.evidence,
        )
        delivered = {line.product: line.quantity * 0.8 for line in plan.products}
        outcome = ContractEpochOutcome(
            session_id="sequence",
            epoch_index=epoch,
            commitment_hash=spec.commitment_hash,
            status="expired",
            delivered_quantity=int(sum(delivered.values())),
            requested_quantity=spec.quantity,
            delivered_by_product=delivered,
            requested_by_product={
                line.product: line.quantity for line in plan.products
            },
            completion_ratio=0.8,
            performance_score=0.8,
            simulation_ticks_used=spec.deadline_ticks,
            interventions_used=0,
            model_seconds=0,
            tool_seconds=0,
            runner_wall_seconds=0,
            terminal_state_digest=f"epoch-{epoch}",
        )
        policy.observe(spec, outcome, context)
        plans.append(plan)

    first_products = [plan.products[0].product for plan in plans[:3]]
    assert set(first_products[:2]) == {"iron-plate", "copper-plate"}
    assert first_products[2] == "electronic-circuit"
    first_circuit = plans[2].products[0]
    assert first_circuit.quantity <= 20
    assert plans[2].candidate.deadline_ticks <= MAX_COMMISSIONING_DEADLINE_TICKS
    # One-shot deliveries establish commissioning/consolidation evidence, but
    # cannot by themselves authorize a sustained qualification probe.
    assert all(plan.order_kind == "one_shot" for plan in plans[3:])
    assert all(plan.evidence["intent"] != "stress" for plan in plans)
    assert any(len(plan.products) > 1 for plan in plans)


def test_attempts_only_are_not_capacity_or_throughput_evidence():
    catalog, context, pool = _setup()
    policy = EvidenceDrivenCustomerPolicy()
    candidate = pool[0]
    policy.records[candidate.item_name] = ProductEvidence(
        candidate.item_name,
        attempts=4,
        last_epoch=4,
        completion_scores=[0.0] * 4,
    )

    assert not policy._has_evidence(candidate, context)
    quantity, _, evidence = policy._size_line(
        candidate,
        "throughput",
        context,
        catalog,
        __import__("random").Random(3),
    )
    assert quantity > 0
    assert evidence["evidence_kind"] == "none"
    assert evidence["basis"] == "commissioning_cold_start"


def test_zero_delivery_with_capability_progress_replays_parent_at_lower_pressure():
    catalog, context, pool = _setup()
    policy = EvidenceDrivenCustomerPolicy()
    first = policy.choose(
        pool,
        context=context,
        catalog=catalog,
        difficulty_model=UncalibratedDifficultyModel(),
        selection_seed=991,
    )
    spec = build_epoch_spec(
        session_id="steel-replay",
        epoch_index=1,
        selection_seed=991,
        candidate=first.candidate,
        context=context,
        benchmark_version=ADAPTIVE_BENCHMARK_VERSION,
        calibration_version=CONTRACT_CALIBRATION_VERSION,
        order_kind=first.order_kind,
        products=first.products,
        policy_evidence=first.evidence,
    )
    outcome = ContractEpochOutcome(
        session_id="steel-replay",
        epoch_index=1,
        commitment_hash=spec.commitment_hash,
        status="expired",
        delivered_quantity=0,
        requested_quantity=spec.quantity,
        delivered_by_product={line.product: 0.0 for line in spec.products},
        requested_by_product={line.product: line.quantity for line in spec.products},
        completion_ratio=0.0,
        performance_score=0.0,
        simulation_ticks_used=spec.deadline_ticks,
        interventions_used=4,
        model_seconds=0.0,
        tool_seconds=0.0,
        runner_wall_seconds=0.0,
        terminal_state_digest="after",
        capability_delta=CapabilityDelta(
            before_state_digest="before",
            after_state_digest="after",
            target_id=spec.item_name,
            new_technologies=("steel-processing",),
            path_progress=1,
            meaningful_progress=True,
        ),
    )
    policy.observe(spec, outcome, context)
    retry = policy.choose(
        pool,
        context=context,
        catalog=catalog,
        difficulty_model=UncalibratedDifficultyModel(),
        selection_seed=2,
    )

    assert retry.products[0].product == first.products[0].product
    assert retry.mode == "replay_backoff"
    assert retry.evidence["selection_reason"] == "capability_progress_replay"
    assert retry.products[0].quantity <= first.products[0].quantity
    assert not policy.records[first.products[0].product].positive_delivery


def test_zero_delivery_lubricant_does_not_unlock_scaled_throughput():
    catalog, context, pool = _setup()
    policy = EvidenceDrivenCustomerPolicy()
    candidate = pool[0]
    spec = build_epoch_spec(
        session_id="lubricant",
        epoch_index=1,
        selection_seed=1,
        candidate=candidate,
        context=context,
        benchmark_version=ADAPTIVE_BENCHMARK_VERSION,
        calibration_version=CONTRACT_CALIBRATION_VERSION,
    )
    outcome = ContractEpochOutcome(
        session_id="lubricant",
        epoch_index=1,
        commitment_hash=spec.commitment_hash,
        status="expired",
        delivered_quantity=0,
        requested_quantity=spec.quantity,
        delivered_by_product={candidate.item_name: 0.0},
        completion_ratio=0.0,
        simulation_ticks_used=spec.deadline_ticks,
        interventions_used=1,
        model_seconds=0.0,
        tool_seconds=0.0,
        runner_wall_seconds=0.0,
        terminal_state_digest="after",
    )
    policy.observe(spec, outcome, None)
    _, _, evidence = policy._size_line(
        candidate,
        "throughput",
        context,
        catalog,
        __import__("random").Random(1),
    )

    assert policy.records[candidate.item_name].attempts == 1
    assert policy.records[candidate.item_name].zero_delivery_count == 1
    assert not policy.records[candidate.item_name].capacity_evidence
    assert evidence["basis"] == "commissioning_cold_start"


def test_nested_order_windows_are_the_only_sustained_depot_evidence():
    catalog, context, pool = _setup()
    candidate = pool[0]
    spec = build_epoch_spec(
        session_id="windowed",
        epoch_index=1,
        selection_seed=1,
        candidate=candidate,
        context=context,
        benchmark_version=ADAPTIVE_BENCHMARK_VERSION,
        calibration_version=CONTRACT_CALIBRATION_VERSION,
        order_kind="sustained",
        products=(
            # Keep the fixture small; telemetry is normalized against the
            # committed line rather than the candidate's stale quantity.
            ProductDemandSpec(product=candidate.item_name, quantity=100),
        ),
    )
    positive = ContractEpochOutcome(
        session_id="windowed",
        epoch_index=1,
        commitment_hash=spec.commitment_hash,
        status="fulfilled",
        delivered_quantity=100,
        requested_quantity=100,
        delivered_by_product={candidate.item_name: 100.0},
        completion_ratio=1.0,
        simulation_ticks_used=100000,
        interventions_used=0,
        model_seconds=0.0,
        tool_seconds=0.0,
        runner_wall_seconds=0.0,
        terminal_state_digest="after",
        delivery_telemetry={
            "physical": {"raw_rates_300s": {candidate.item_name: 60.0}},
            "order": {
                "window_ticks": 100000,
                "lines": {
                    candidate.item_name: {
                        "requested": 100.0,
                        "accepted": 100.0,
                        "slice_scores": [1.0, 0.0],
                    }
                },
            },
        },
    )
    policy = EvidenceDrivenCustomerPolicy()
    policy.observe(spec, positive, None)
    record = policy.records[candidate.item_name]
    assert record.sustained_window_scores == [1.0, 0.0]
    assert not record.sustained_evidence
    assert record.completion_scores == [0.5]

    certified = positive.model_copy(
        update={
            "delivery_telemetry": {
                "order": {
                    "window_ticks": 100000,
                    "lines": {
                        candidate.item_name: {
                            "requested": 100.0,
                            "accepted": 100.0,
                            "slice_scores": [1.0, 0.5],
                        }
                    },
                }
            }
        }
    )
    certified_policy = EvidenceDrivenCustomerPolicy()
    certified_policy.observe(spec, certified, None)
    assert certified_policy.records[candidate.item_name].sustained_evidence

    zero = positive.model_copy(
        update={
            "delivered_quantity": 0,
            "delivered_by_product": {candidate.item_name: 0.0},
            "completion_ratio": 0.0,
            "status": "expired",
            "delivery_telemetry": {
                "order": {
                    "window_ticks": 100000,
                    "lines": {
                        candidate.item_name: {
                            "requested": 100.0,
                            "accepted": 0.0,
                            "slice_scores": [0.0, 0.0],
                        }
                    },
                }
            },
        }
    )
    policy2 = EvidenceDrivenCustomerPolicy()
    policy2.observe(spec, zero, None)
    assert not policy2.records[candidate.item_name].sustained_evidence


def test_frontier_lane_rejects_deep_nuclear_jump():
    catalog, context, pool = _setup()
    nuclear = _candidate(catalog, context, "electronic-circuit", 5, "frontier")
    policy = EvidenceDrivenCustomerPolicy()
    # At epoch 3 the schedule asks for frontier, but only a one-band frontier
    # may pass.  The available same-band anchors are retained instead.
    policy.completed_epochs = 2
    plan = policy.choose(
        [pool[0], pool[1], nuclear],
        context=context,
        catalog=catalog,
        difficulty_model=UncalibratedDifficultyModel(),
        selection_seed=3,
    )

    assert plan.products[0].product in {"iron-plate", "copper-plate"}
    assert plan.evidence["lane"] == "anchor"
    assert "frontier" in plan.evidence["selection_reason"]


def test_selection_is_state_and_evidence_driven_not_epoch_schedule():
    catalog, context, pool = _setup()
    first = EvidenceDrivenCustomerPolicy()
    later = EvidenceDrivenCustomerPolicy()
    later.completed_epochs = 19

    first_plan = first.choose(
        pool,
        context=context,
        catalog=catalog,
        difficulty_model=UncalibratedDifficultyModel(),
        selection_seed=17,
    )
    later_plan = later.choose(
        pool,
        context=context,
        catalog=catalog,
        difficulty_model=UncalibratedDifficultyModel(),
        selection_seed=17,
    )

    assert first_plan.products == later_plan.products
    assert first_plan.evidence["intent"] in INTENTS
    assert first_plan.evidence["intent"] == later_plan.evidence["intent"]
    assert first_plan.evidence["utility_components"]
    assert "intent_utilities" in first_plan.evidence


def test_mixed_probe_does_not_require_independent_capacity_evidence():
    catalog, context, pool = _setup()
    policy = EvidenceDrivenCustomerPolicy()

    secondary = policy._secondary_candidate_for_compose(
        pool[0], candidates=pool[:2], context=context
    )

    assert secondary is not None
    assert secondary.item_name != pool[0].item_name
    assert not policy._has_evidence(pool[0], context)
    assert not policy._has_evidence(secondary, context)


def test_structural_recovery_is_consumed_after_one_retry():
    catalog, context, pool = _setup()
    policy = EvidenceDrivenCustomerPolicy()
    first = policy.choose(
        pool,
        context=context,
        catalog=catalog,
        difficulty_model=UncalibratedDifficultyModel(),
        selection_seed=991,
    )
    spec = build_epoch_spec(
        session_id="recovery-once",
        epoch_index=1,
        selection_seed=991,
        candidate=first.candidate,
        context=context,
        benchmark_version=ADAPTIVE_BENCHMARK_VERSION,
        calibration_version=CONTRACT_CALIBRATION_VERSION,
        order_kind=first.order_kind,
        products=first.products,
        policy_evidence=first.evidence,
    )
    progressed = ContractEpochOutcome(
        session_id="recovery-once",
        epoch_index=1,
        commitment_hash=spec.commitment_hash,
        status="expired",
        delivered_quantity=0,
        requested_quantity=spec.quantity,
        delivered_by_product={line.product: 0.0 for line in spec.products},
        requested_by_product={line.product: line.quantity for line in spec.products},
        completion_ratio=0.0,
        performance_score=0.0,
        simulation_ticks_used=spec.deadline_ticks,
        interventions_used=0,
        model_seconds=0.0,
        tool_seconds=0.0,
        runner_wall_seconds=0.0,
        terminal_state_digest="progressed",
        capability_delta=CapabilityDelta(
            before_state_digest="before",
            after_state_digest="after",
            target_id=spec.item_name,
            new_technologies=("steel-processing",),
            path_progress=1,
            meaningful_progress=True,
        ),
    )
    policy.observe(spec, progressed, context)
    retry = policy.choose(
        pool,
        context=context,
        catalog=catalog,
        difficulty_model=UncalibratedDifficultyModel(),
        selection_seed=2,
    )
    assert retry.evidence["intent"] == "recover"

    retry_spec = build_epoch_spec(
        session_id="recovery-once",
        epoch_index=2,
        selection_seed=2,
        candidate=retry.candidate,
        context=context,
        benchmark_version=ADAPTIVE_BENCHMARK_VERSION,
        calibration_version=CONTRACT_CALIBRATION_VERSION,
        order_kind=retry.order_kind,
        products=retry.products,
        policy_evidence=retry.evidence,
    )
    policy.observe(
        retry_spec,
        progressed.model_copy(
            update={
                "epoch_index": 2,
                "commitment_hash": retry_spec.commitment_hash,
                "terminal_state_digest": "retry-failed",
                "capability_delta": None,
            }
        ),
        context,
    )
    follow_up = policy.choose(
        pool,
        context=context,
        catalog=catalog,
        difficulty_model=UncalibratedDifficultyModel(),
        selection_seed=3,
    )
    assert follow_up.evidence["intent"] != "recover"


def test_rate_only_capability_delta_is_not_meaningful_progress():
    catalog, before, _ = _setup()
    after = before.model_copy(
        update={
            "state_digest": "after-rate-only",
            "captured_tick": 3600,
            "production_rates_60s": {"iron-plate": 60.0},
            "production_rates_300s": {"iron-plate": 60.0},
        }
    )

    delta = compare_capability_snapshots(
        before,
        after,
        target_product="iron-plate",
        catalog=catalog,
    )

    assert delta.production_rate_deltas == {"iron-plate": 60.0}
    assert delta.path_progress == 0
    assert not delta.meaningful_progress


def test_deepen_uses_a_low_rate_probe_after_one_shot_delivery():
    catalog, context, pool = _setup()
    candidate = pool[0]
    policy = EvidenceDrivenCustomerPolicy()
    policy.records[candidate.item_name] = ProductEvidence(
        product=candidate.item_name,
        attempts=1,
        positive_delivery_count=1,
        delivered_rates=[20.0],
    )

    mode = policy._mode_for_intent(
        candidate,
        intent="deepen",
        context=context,
        rng=random.Random(1),
    )

    assert mode == "sustained_commissioning"
    _, deadline, evidence = policy._size_line(
        candidate, mode, context, catalog, random.Random(1)
    )
    assert evidence["basis"] == "sustained_commissioning_probe"
    assert evidence["automated_capacity_evidence"] is False
    assert deadline >= 45 * 60 * 60


def test_failed_commissioning_probe_retries_only_after_later_recovery():
    _, context, pool = _setup()
    candidate = pool[0]
    policy = EvidenceDrivenCustomerPolicy()
    record = ProductEvidence(
        product=candidate.item_name,
        attempts=2,
        positive_delivery_count=1,
        commissioning_probe_count=1,
        last_commissioning_probe_epoch=2,
        commissioning_probe_failure_count=1,
        last_epoch=2,
    )
    policy.records[candidate.item_name] = record

    # A failed probe must not immediately schedule another probe.
    assert policy._mode_for_intent(
        candidate, intent="deepen", context=context, rng=random.Random(1)
    ) == "consolidation"

    # A later fully successful non-probe delivery reopens one probe attempt.
    record.last_non_probe_success_epoch = 3
    record.last_epoch = 3
    record.positive_delivery_count = 2
    assert policy._mode_for_intent(
        candidate, intent="deepen", context=context, rng=random.Random(1)
    ) == "sustained_commissioning"

    # Once that retry has also failed, another immediate retry is blocked.
    record.commissioning_probe_count = 2
    record.commissioning_probe_failure_count = 2
    record.last_commissioning_probe_epoch = 4
    record.last_epoch = 4
    assert policy._mode_for_intent(
        candidate, intent="deepen", context=context, rng=random.Random(1)
    ) == "consolidation"


def test_deepen_escalates_from_provenance_safe_automated_production():
    catalog, context, pool = _setup()
    candidate = pool[0]
    context = context.model_copy(
        update={
            "automated_production_rates_60s": {candidate.item_name: 60.0},
            "automated_production_rates_300s": {candidate.item_name: 45.0},
        }
    )
    policy = EvidenceDrivenCustomerPolicy()
    policy.records[candidate.item_name] = ProductEvidence(
        product=candidate.item_name,
        attempts=1,
        positive_delivery_count=1,
        delivered_rates=[20.0],
    )

    mode = policy._mode_for_intent(
        candidate,
        intent="deepen",
        context=context,
        rng=random.Random(1),
    )
    _, _, evidence = policy._size_line(
        candidate, mode, context, catalog, random.Random(1)
    )

    assert mode == "throughput"
    assert evidence["basis"] == "automated_production_throughput_lcb"
    assert evidence["effective_mode"] == "throughput"


def test_handcrafted_one_shot_flow_is_not_sustained_capacity_evidence():
    catalog, context, pool = _setup()
    candidate = pool[0]
    context = context.model_copy(
        update={
            # This is the legacy aggregate flow projection. It intentionally
            # looks productive even though no provenance-safe rate exists.
            "production_rates_60s": {candidate.item_name: 120.0},
            "production_rates_300s": {candidate.item_name: 120.0},
            "delivery_rates_60s": {candidate.item_name: 120.0},
            "delivery_rates_300s": {candidate.item_name: 24.0},
        }
    )
    policy = EvidenceDrivenCustomerPolicy()
    spec = build_epoch_spec(
        session_id="manual-one-shot",
        epoch_index=1,
        selection_seed=1,
        candidate=candidate,
        context=context,
        benchmark_version=ADAPTIVE_BENCHMARK_VERSION,
        calibration_version=CONTRACT_CALIBRATION_VERSION,
        order_kind="one_shot",
        products=(ProductDemandSpec(product=candidate.item_name, quantity=13),),
    )
    outcome = ContractEpochOutcome(
        session_id="manual-one-shot",
        epoch_index=1,
        commitment_hash=spec.commitment_hash,
        status="fulfilled",
        delivered_quantity=13,
        requested_quantity=13,
        delivered_by_product={candidate.item_name: 13.0},
        requested_by_product={candidate.item_name: 13.0},
        completion_ratio=1.0,
        performance_score=1.0,
        simulation_ticks_used=3600,
        interventions_used=1,
        model_seconds=0.0,
        tool_seconds=0.0,
        runner_wall_seconds=0.0,
        terminal_state_digest="manual-one-shot-after",
    )
    policy.observe(spec, outcome, context)

    record = policy.records[candidate.item_name]
    assert record.positive_delivery
    assert not record.observed_production
    assert not record.automated_capacity_evidence
    assert policy._mode_for_intent(
        candidate,
        intent="deepen",
        context=context,
        rng=random.Random(1),
    ) == "sustained_commissioning"
    _, _, evidence = policy._size_line(
        candidate, "sustained_commissioning", context, catalog, random.Random(1)
    )
    assert evidence["effective_mode"] == "sustained_commissioning"
    assert evidence["basis"] == "sustained_commissioning_probe"


def test_commissioning_probe_delivery_never_authorizes_sustained_capacity():
    catalog, context, pool = _setup()
    candidate = pool[0]
    policy = EvidenceDrivenCustomerPolicy()
    probe = policy._build_plan(
        [candidate],
        mode="sustained_commissioning",
        context=context,
        catalog=catalog,
        difficulty_model=UncalibratedDifficultyModel(),
        rating=CapabilityRating(
            mu=0.0,
            sigma=2.0,
            conservative_score=-6.0,
            rated_epoch_count=0,
        ),
        rng=random.Random(1),
        lane="anchor",
        reason="commissioning_probe",
        selection_seed=1,
        intent="deepen",
    )
    spec = build_epoch_spec(
        session_id="commissioning-probe",
        epoch_index=1,
        selection_seed=1,
        candidate=probe.candidate,
        context=context,
        benchmark_version=ADAPTIVE_BENCHMARK_VERSION,
        calibration_version=CONTRACT_CALIBRATION_VERSION,
        order_kind=probe.order_kind,
        products=probe.products,
        policy_evidence=probe.evidence,
    )
    assert spec.order_kind == "sustained"
    assert spec.throughput_audit is not None
    outcome = ContractEpochOutcome(
        session_id=spec.session_id,
        epoch_index=spec.epoch_index,
        commitment_hash=spec.commitment_hash,
        status="fulfilled",
        delivered_quantity=spec.quantity,
        requested_quantity=spec.quantity,
        delivered_by_product={candidate.item_name: float(spec.quantity)},
        requested_by_product={candidate.item_name: float(spec.quantity)},
        completion_ratio=1.0,
        performance_score=1.0,
        simulation_ticks_used=spec.deadline_ticks,
        interventions_used=10,
        model_seconds=0.0,
        tool_seconds=0.0,
        runner_wall_seconds=0.0,
        terminal_state_digest="probe-after",
        delivery_telemetry={
            "order": {
                "window_ticks": spec.deadline_ticks,
                "lines": {
                    candidate.item_name: {
                        "accepted": spec.quantity,
                        "slice_scores": [1.0],
                    }
                },
            }
        },
    )
    policy.observe(spec, outcome, context)
    record = policy.records[candidate.item_name]
    assert record.commissioning_probe_count == 1
    assert not record.sustained_evidence
    assert not record.automated_capacity_evidence

    audited = outcome.model_copy(
        update={
            "epoch_index": 2,
            "throughput_audit": ThroughputAuditResult(
                lease_id="lease",
                session_id=spec.session_id,
                epoch_index=2,
                audit_worker_id="worker",
                candidate_tick=0,
                candidate_state_hash="candidate",
                detector_window_seconds=5,
                target_rates_per_minute={candidate.item_name: 1.0},
                burn_in_seconds=0,
                holdout_seconds=30,
                holdout_ticks=1800,
                subwindow_seconds=10,
                subwindow_ticks=[600, 600, 600],
                production_rates_per_minute={candidate.item_name: 2.0},
                depot_rates_per_minute={candidate.item_name: 2.0},
                production_subwindow_rates={candidate.item_name: [2.0]},
                depot_subwindow_rates={candidate.item_name: [2.0]},
                line_scores={candidate.item_name: 1.0},
                passed=True,
            ),
        }
    )
    policy.observe(spec, audited, context)
    assert policy.records[candidate.item_name].automated_capacity_evidence


def test_low_service_score_is_not_reliable_stress_evidence():
    record = ProductEvidence(
        product="iron-plate",
        sustained_depot_count=1,
        sustained_window_scores=[0.1, 0.2],
        sustained_window_rates=[2.0, 3.0],
    )
    assert record.sustained_evidence
    assert not record.sustained_reliable

    record.sustained_window_scores = [0.9, 0.95]
    assert record.sustained_reliable
