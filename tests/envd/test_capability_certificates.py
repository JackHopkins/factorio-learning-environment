"""Unit tests for sustainable-capability evidence and its ledger."""

import pytest
from pydantic import ValidationError

from fle.envd.capability_certificates import (
    commissioning_certificate,
    contract_certificate,
    progress_vector,
    qualification_certificate,
)
from fle.envd.models import (
    CapabilityCertificate,
    CapabilityLedger,
    ContractContextSnapshot,
    ContractDifficultyFeatures,
    ContractEpochOutcome,
    ContractEpochSpec,
    ThroughputCheckResult,
)

pytestmark = pytest.mark.no_factorio


def _snapshot(**overrides) -> ContractContextSnapshot:
    fields = dict(
        session_id="s-1",
        epoch_index=0,
        captured_tick=1000,
        technology_ids=(),
        unlocked_recipe_ids=(),
        inventory_counts={},
        placed_entity_counts={},
        production_rates_60s={"iron-plate": 12.0},
        production_rates_300s={},
        power_capacity_kw=100.0,
        power_utilization=0.2,
        logistic_network_count=0,
        train_stop_count=0,
        pollution_total=None,
        evolution_factor=None,
        map_seed_hash="map",
        state_digest="state-1",
    )
    fields.update(overrides)
    return ContractContextSnapshot(**fields)


def test_passive_snapshot_is_commissioned_even_with_60_second_rate():
    certificate = commissioning_certificate(_snapshot(), product="iron-plate")

    assert certificate.status == "commissioned"
    assert certificate.is_sustainable is False
    assert certificate.is_autonomous is False
    with pytest.raises(ValidationError):
        CapabilityCertificate.model_validate(
            certificate.model_dump()
            | {
            "status": "autonomous",
            "evidence_source": "snapshot",
            "autonomous_validation": True,
            "qualification_window_ticks": 3600,
            "sustained_window_ticks": 3600,
            }
        )


def test_intervention_tainted_qualification_cannot_claim_autonomy():
    with pytest.raises(ValidationError, match="zero interventions"):
        qualification_certificate(
            certificate_id="q-1",
            demand_vector={"iron-plate": 12},
            observed_rate_per_minute={"iron-plate": 12},
            sustained_window_ticks=3600,
            qualification_window_ticks=3600,
            interventions_during_window=1,
        )


def test_mixed_demand_certificate_round_trips_and_is_joint():
    certificate = qualification_certificate(
        certificate_id="q-mixed",
        demand_vector={"iron-plate": 12, "electronic-circuit": 6},
        target_rate_per_minute={"iron-plate": 10, "electronic-circuit": 5},
        observed_rate_per_minute={"iron-plate": 12, "electronic-circuit": 6},
        sustained_window_ticks=3600,
        qualification_window_ticks=3600,
        capability_band=2,
    )
    restored = CapabilityCertificate.model_validate_json(certificate.model_dump_json())
    ledger = CapabilityLedger(session_id="s-1")
    ledger.record(restored)

    assert restored.demand_vector == {"iron-plate": 12.0, "electronic-circuit": 6.0}
    assert restored.products == ("electronic-circuit", "iron-plate")
    assert progress_vector(ledger).joint_sustained_throughput == 18.0


def test_observed_sustained_is_not_autonomous_without_frozen_qualification():
    certificate = CapabilityCertificate(
        certificate_id="sustained-1",
        demand_vector={"iron-plate": 20},
        observed_rate_per_minute={"iron-plate": 20},
        sustained_window_ticks=3600,
        status="observed_sustained",
        evidence_source="contract",
        reliability=0.8,
    )
    ledger = CapabilityLedger()
    ledger.record(certificate)
    current = ledger.current_progress()

    assert current.sustainable_capability_count == 1
    assert current.certified_capability_count == 0
    assert current.autonomy == 0.0
    assert current.observed_sustained_throughput == 20.0


def test_sustained_contract_is_observed_but_never_autonomous():
    context = _snapshot()
    spec = ContractEpochSpec.create(
        session_id="s-1",
        epoch_index=1,
        template_id="test",
        generation_seed=1,
        selection_seed=2,
        item_name="iron-plate",
        quantity=20,
        order_kind="sustained",
        deadline_ticks=3600,
        context=context,
        features=ContractDifficultyFeatures(
            product_id="iron-plate", product_tier=0, recipe_depth=1,
            missing_technology_count=0, missing_machine_type_count=0,
            required_new_intermediate_count=0, log_quantity=3.0,
            deadline_ticks=3600, required_rate_per_minute=20,
            existing_rate_per_minute=12, inventory_coverage_ratio=0,
            estimated_power_fraction=0, transport_complexity=0,
            stage_band=0,
        ),
        raw_difficulty=1.0,
        state_advantage=0.0,
        effective_difficulty=1.0,
    )
    outcome = ContractEpochOutcome(
        session_id="s-1", epoch_index=1,
        commitment_hash=spec.commitment_hash, status="fulfilled",
        delivered_quantity=20, requested_quantity=20,
        delivered_by_product={"iron-plate": 20},
        requested_by_product={"iron-plate": 20}, completion_ratio=1.0,
        performance_score=1.0, simulation_ticks_used=3600,
        interventions_used=5, model_seconds=1, tool_seconds=0,
        runner_wall_seconds=1, terminal_state_digest="after",
    )

    certificate = contract_certificate(spec, outcome)

    assert certificate.status == "observed_sustained"
    assert certificate.is_autonomous is False
    assert certificate.interventions_during_window == 5


def test_authoritative_check_promotes_sustained_contract_without_changing_score():
    context = _snapshot()
    spec = ContractEpochSpec.create(
        session_id="s-1", epoch_index=1, template_id="test",
        generation_seed=1, selection_seed=2, item_name="iron-plate",
        quantity=20, order_kind="sustained", deadline_ticks=3600,
        context=context,
        features=ContractDifficultyFeatures(
            product_id="iron-plate", product_tier=0, recipe_depth=1,
            missing_technology_count=0, missing_machine_type_count=0,
            required_new_intermediate_count=0, log_quantity=3.0,
            deadline_ticks=3600, required_rate_per_minute=20,
            existing_rate_per_minute=12, inventory_coverage_ratio=0,
            estimated_power_fraction=0, transport_complexity=0,
            stage_band=0,
        ),
        raw_difficulty=1.0, state_advantage=0.0, effective_difficulty=1.0,
    )
    check = ThroughputCheckResult(
        lease_id="lease-1", session_id="s-1", epoch_index=1,
        authoritative=True, start_tick=3600, end_tick=7200,
        window_ticks=3600, delivered_by_product={"iron-plate": 16},
        observed_rate_per_minute={"iron-plate": 16},
        target_rate_per_minute={"iron-plate": 20},
        line_scores={"iron-plate": 0.8}, performance_score=0.8,
        contract_status="expired",
    )
    outcome = ContractEpochOutcome(
        session_id="s-1", epoch_index=1,
        commitment_hash=spec.commitment_hash, status="expired",
        delivered_quantity=18, requested_quantity=20,
        delivered_by_product={"iron-plate": 18},
        requested_by_product={"iron-plate": 20}, completion_ratio=0.7,
        performance_score=0.7, simulation_ticks_used=3600,
        interventions_used=5, model_seconds=1, tool_seconds=0,
        runner_wall_seconds=1, terminal_state_digest="after",
        autonomous_throughput=check,
    )

    certificate = contract_certificate(spec, outcome)

    assert outcome.performance_score == 0.7
    assert certificate.status == "autonomous"
    assert certificate.autonomous_validation is True
    assert certificate.observed_rate_per_minute == {"iron-plate": 16.0}
    assert certificate.reliability == pytest.approx(0.7)


def test_ledger_retains_best_real_watermark_when_current_capability_shrinks():
    qualified = qualification_certificate(
        certificate_id="q-iron",
        demand_vector={"iron-plate": 20},
        observed_rate_per_minute={"iron-plate": 20},
        sustained_window_ticks=3600,
        qualification_window_ticks=3600,
        capability_band=3,
        session_id="s-1",
    )
    ledger = CapabilityLedger(session_id="s-1")
    ledger.record(qualified)
    ledger.record(commissioning_certificate(_snapshot(captured_tick=5000), product="iron-plate"))

    current = progress_vector(ledger)
    assert current.highest_certified_band == 0
    assert current.sustainable_capability_count == 0
    assert current.best_watermark["highest_certified_band"] == 3
