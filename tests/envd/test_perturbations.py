import pytest

from fle.envd.perturbations import (
    DisruptionConfig,
    PerturbationEngine,
    generate_disruption_schedule,
    interval_rates,
    product_interval_rates,
    RateSample,
)
from fle.envd.models import FactorioTaskSpec

pytestmark = pytest.mark.no_factorio


def _stats(total_output: float) -> dict:
    return {"output": {"iron-plate": total_output}}


# ---------------------------------------------------------------------------
# Schedule generation
# ---------------------------------------------------------------------------


def test_disruption_generation_is_deterministic():
    config = DisruptionConfig(horizon_ticks=720000, difficulty=0.5, count=4)
    first = generate_disruption_schedule(config, seed=7)
    second = generate_disruption_schedule(config, seed=7)
    assert first.model_dump() == second.model_dump()
    assert first.commitment == second.commitment


def test_disruption_seed_changes_schedule():
    config = DisruptionConfig(horizon_ticks=720000, difficulty=0.5, count=4)
    first = generate_disruption_schedule(config, seed=1)
    second = generate_disruption_schedule(config, seed=2)
    assert first.model_dump() != second.model_dump()


def test_generated_perturbations_are_sorted_and_valid():
    config = DisruptionConfig(
        horizon_ticks=1440000, difficulty=0.8, count=6, warmup_ticks=36000
    )
    spec = generate_disruption_schedule(config, seed=42)
    triggers = [p.trigger_tick for p in spec.perturbations]
    assert triggers == sorted(triggers)
    assert all(p.trigger_tick >= config.warmup_ticks for p in spec.perturbations)
    for perturbation in spec.perturbations:
        if perturbation.kind == "entity_destruction":
            assert (
                perturbation.parameters.get("entity_types")
                or perturbation.parameters.get("entity_names")
            )
            assert perturbation.parameters["count"] >= 1
        elif perturbation.kind == "resource_depletion":
            assert perturbation.parameters["radius"] > 0
        elif perturbation.kind == "enemy_wave":
            assert perturbation.parameters["count"] >= 1
            assert perturbation.parameters["tier"] in {
                "small",
                "medium",
                "big",
                "behemoth",
            }


def test_task_fingerprint_includes_perturbations():
    plain = FactorioTaskSpec(task_id="t", goal="g")
    config = DisruptionConfig(horizon_ticks=720000, count=2)
    disrupted = FactorioTaskSpec(
        task_id="t",
        goal="g",
        perturbations=generate_disruption_schedule(config, seed=3),
    )
    assert plain.fingerprint != disrupted.fingerprint


# ---------------------------------------------------------------------------
# Rate math
# ---------------------------------------------------------------------------


def test_interval_rates_basic():
    samples = [
        RateSample(tick=0, totals={}),
        RateSample(tick=100, totals={"iron-plate": 500}),
        RateSample(tick=300, totals={"iron-plate": 1300, "coal": 200}),
    ]
    rates = dict(interval_rates(samples))
    assert rates[100] == pytest.approx(5.0)
    assert rates[300] == pytest.approx((1300 - 500) / 200 + 200 / 200)

    per_product = dict(product_interval_rates(samples))
    assert per_product[100]["iron-plate"] == pytest.approx(5.0)
    assert per_product[300]["iron-plate"] == pytest.approx(4.0)
    assert per_product[300]["coal"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Firing and recovery
# ---------------------------------------------------------------------------


def _engine_with_recovery(min_ticks: int = 600) -> PerturbationEngine:
    spec = generate_disruption_schedule(
        DisruptionConfig(
            horizon_ticks=720000,
            difficulty=0.5,
            count=1,
            allow_enemy_waves=False,
            warmup_ticks=0,
        ),
        seed=11,
    )
    # Force a deterministic single entity_destruction shock at tick 2500.
    from fle.envd.models import DisruptionScheduleSpec, PerturbationSpec

    pinned = DisruptionScheduleSpec(
        generator_version=spec.generator_version,
        perturbations=[
            PerturbationSpec(
                perturbation_id="dis-000-belt_failure",
                kind="entity_destruction",
                trigger_tick=2500,
                parameters={
                    "entity_names": ["transport-belt"],
                    "count": 2,
                    "search_radius": 200,
                },
            )
        ],
        recovery_min_ticks=min_ticks,
    )
    return PerturbationEngine(pinned)


def test_perturbation_fires_once_at_trigger_tick():
    engine = _engine_with_recovery()
    fired = []

    def fire(command, params):
        fired.append((command, params))
        return {"destroyed": {"transport-belt": 2}, "total": 2}

    events = engine.sync(2000, _stats(12000), fire)
    assert fired == []
    assert events == []

    events = engine.sync(3000, _stats(17000), fire)
    assert len(fired) == 1
    assert fired[0][0] == "destroy_entities"
    applied = [e for e in events if e["event"] == "perturbation_applied"]
    assert len(applied) == 1
    assert applied[0]["status"] == "applied"

    engine.sync(4000, _stats(18000), fire)
    assert len(fired) == 1


def test_recovery_measured_from_baseline_after_shock():
    engine = _engine_with_recovery(min_ticks=600)

    def fire(command, params):
        return {"destroyed": {"transport-belt": 2}, "total": 2}

    engine.sync(1000, _stats(6000), fire)   # no interval yet
    engine.sync(2000, _stats(12000), fire)  # rate 6.0 -> baseline
    engine.sync(3000, _stats(17000), fire)  # fires; post rate 5.0 measured later
    engine.sync(4000, _stats(18000), fire)  # post rate 1.0: still broken
    events = engine.sync(5000, _stats(24000), fire)  # post rate 6.0: recovered

    recoveries = [e for e in events if e["event"] == "recovery_completed"]
    assert len(recoveries) == 1
    assert recoveries[0]["perturbation_id"] == "dis-000-belt_failure"
    # The shock applies at the first sync at/after its trigger (tick 3000),
    # so T_recovery runs from application to restored throughput (tick 5000).
    assert recoveries[0]["recovery_ticks"] == 2000
    assert recoveries[0]["tracked_products"]["iron-plate"] == pytest.approx(6.0)
    details = recoveries[0]["product_details"]["iron-plate"]
    assert details["restored"] is True

    summary = engine.summary()
    assert summary["applied"] == 1
    assert summary["mean_recovery_ticks"] == 2000


def test_zero_effect_shock_is_recorded_as_no_op():
    engine = _engine_with_recovery()

    def fire(command, params):
        return {"destroyed": {}, "total": 0, "affected_products": []}

    engine.sync(1000, _stats(6000), fire)
    events = engine.sync(3000, _stats(12000), fire)
    applied = [e for e in events if e["event"] == "perturbation_applied"]
    assert len(applied) == 1
    assert applied[0]["status"] == "no_op"
    summary = engine.summary()
    assert summary["applied"] == 0
    assert summary["no_op"] == 1
    assert summary["recoveries"] == []


def test_recovery_gated_on_affected_product_not_decoy_flood():
    from fle.envd.models import DisruptionScheduleSpec, PerturbationSpec

    spec = DisruptionScheduleSpec(
        perturbations=[
            PerturbationSpec(
                perturbation_id="d-gear",
                kind="entity_destruction",
                trigger_tick=2500,
                parameters={
                    "entity_names": ["assembling-machine-2"],
                    "count": 1,
                },
            )
        ],
        recovery_min_ticks=600,
    )
    engine = PerturbationEngine(spec)

    def fire(command, params):
        return {
            "destroyed": {"assembling-machine-2": 1},
            "total": 1,
            "affected_products": ["iron-gear-wheel"],
        }

    def stats(gear: float, decoy: float) -> dict:
        return {"output": {"iron-gear-wheel": gear, "cheap-decoy": decoy}}

    engine.sync(1000, stats(6000, 0), fire)
    engine.sync(2000, stats(12000, 0), fire)   # gear baseline rate 6.0
    engine.sync(3000, stats(17000, 0), fire)   # shock applies
    # Decoy floods massively while the gear line stays near-dead
    # (+10 items over 1000 ticks = 0.01/tick, far under threshold).
    events = engine.sync(4000, stats(17010, 40000), fire)
    assert not [e for e in events if e["event"] == "recovery_completed"]

    # The gear line comes back: only then does recovery complete.
    events = engine.sync(5000, stats(23010, 80000), fire)
    recoveries = [e for e in events if e["event"] == "recovery_completed"]
    assert len(recoveries) == 1
    assert set(recoveries[0]["tracked_products"]) == {"iron-gear-wheel"}
    assert not any("cheap-decoy" in key for key in recoveries[0]["product_details"])


def test_no_recovery_event_before_min_ticks():
    engine = _engine_with_recovery(min_ticks=100000)

    def fire(command, params):
        return {"destroyed": {"transport-belt": 2}, "total": 2}

    engine.sync(1000, _stats(6000), fire)
    engine.sync(2000, _stats(12000), fire)
    engine.sync(3000, _stats(17000), fire)
    events = engine.sync(5000, _stats(29000), fire)  # rate back to 6.0 quickly
    assert not [e for e in events if e["event"] == "recovery_completed"]
    assert engine.summary()["recoveries"][0]["recovered_tick"] is None


def test_zero_baseline_skips_recovery_tracking():
    from fle.envd.models import DisruptionScheduleSpec, PerturbationSpec

    spec = DisruptionScheduleSpec(
        perturbations=[
            PerturbationSpec(
                perturbation_id="d0",
                kind="entity_destruction",
                trigger_tick=100,
                parameters={"entity_names": ["transport-belt"], "count": 1},
            )
        ]
    )
    engine = PerturbationEngine(spec)

    def fire(command, params):
        return {"destroyed": {"transport-belt": 1}, "total": 1}

    engine.sync(200, _stats(0), fire)
    engine.sync(2000, _stats(0), fire)
    engine.sync(4000, _stats(0), fire)
    assert engine.summary()["recoveries"] == []


def test_fire_failure_is_recorded_not_raised():
    from fle.envd.models import DisruptionScheduleSpec, PerturbationSpec

    spec = DisruptionScheduleSpec(
        perturbations=[
            PerturbationSpec(
                perturbation_id="d0",
                kind="enemy_wave",
                trigger_tick=100,
                parameters={"count": 5},
            )
        ]
    )
    engine = PerturbationEngine(spec)

    def boom(command, params):
        raise RuntimeError("rcon down")

    events = engine.sync(200, None, boom)
    applied = [e for e in events if e["event"] == "perturbation_applied"]
    assert len(applied) == 1
    assert applied[0]["status"] == "failed"
    assert "rcon down" in applied[0]["result"]["error"]
    assert engine.summary()["failed"] == 1
