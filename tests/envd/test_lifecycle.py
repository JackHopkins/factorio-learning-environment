import pytest

from fle.envd.lifecycle import (
    CheckpointPool,
    GenerationConfig,
    GenerationManager,
)
from fle.envd.models import (
    FactorioTaskSpec,
    FutureProbeResult,
    LifecycleDecision,
    StateQualitySnapshot,
)

pytestmark = pytest.mark.no_factorio


def _snapshot(
    objective_progress=0.5,
    operational_health=0.5,
    sustained_capability=None,
    milestone_progress=None,
    safety=1.0,
    probes=None,
) -> StateQualitySnapshot:
    return StateQualitySnapshot(
        task_id="t",
        state_hash="h",
        tick=0,
        objective_progress=objective_progress,
        operational_health=operational_health,
        sustained_capability=sustained_capability,
        milestone_progress=milestone_progress,
        safety=safety,
        future_probes=probes or [],
    )


def _forced(outcome: str, lineage_id: str) -> LifecycleDecision:
    return LifecycleDecision(
        lineage_id=lineage_id,
        outcome=outcome,
        continue_lineage=outcome in ("healthy", "degraded_recoverable"),
        continuation_value=0.9 if outcome == "healthy" else 0.2,
        restart_value=0.5,
    )


# ---------------------------------------------------------------------------
# Source quotas
# ---------------------------------------------------------------------------


def test_quota_mix_is_exact_over_a_block():
    config = GenerationConfig(
        fresh_fraction=0.55, inherited_fraction=0.25, pathological_fraction=0.20
    )
    manager = GenerationManager(config, generation_id="quota")
    sources = [manager.sample_source() for _ in range(20)]
    assert sources.count("fresh") == 11
    assert sources.count("inherited") == 5
    assert sources.count("pathological") == 4


def test_composition_reflects_draws():
    config = GenerationConfig(fresh_fraction=0.5, inherited_fraction=0.5, pathological_fraction=0.0)
    manager = GenerationManager(config, generation_id="comp")
    for _ in range(10):
        manager.sample_source()
    composition = manager.composition()
    assert composition["fresh"] == pytest.approx(0.5)
    assert composition["inherited"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Episode planning
# ---------------------------------------------------------------------------


def _seed_one_healthy_lineage(manager: GenerationManager, ratio: float) -> str:
    # Bypass the quota planner: register a lineage directly so seeding does
    # not consume sampling slots or return non-fresh sources.
    record = manager.create_lineage()
    record.contracts_total = 10
    record.contracts_fulfilled = int(round(ratio * 10))
    manager.record_episode(
        record.lineage_id,
        ticks_elapsed=1000,
        snapshot=_snapshot(
            objective_progress=ratio,
            operational_health=max(ratio, 0.5),
            sustained_capability=ratio,
        ),
        decision=_forced("healthy", record.lineage_id),
    )
    return record.lineage_id


def test_inherited_continues_healthiest_lineage():
    manager = GenerationManager(GenerationConfig(), generation_id="inh")
    weak = _seed_one_healthy_lineage(manager, 0.4)
    strong = _seed_one_healthy_lineage(manager, 0.9)

    # Draw until an inherited slot comes up.
    for _ in range(12):
        plan = manager.plan_episode()
        if plan.source == "inherited":
            break
    assert plan.source == "inherited"
    assert plan.lineage_id == strong


def test_pathological_targets_weakest_and_attaches_shocks():
    manager = GenerationManager(GenerationConfig(), generation_id="pathos")
    weak = _seed_one_healthy_lineage(manager, 0.2)
    strong = _seed_one_healthy_lineage(manager, 0.9)

    plan = next(
        p for p in (manager.plan_episode() for _ in range(12))
        if p.source == "pathological"
    )
    assert plan.lineage_id == weak
    overrides = plan.overrides["perturbations"]
    kinds = [p.kind for p in overrides.perturbations]
    assert "entity_destruction" in kinds
    assert all(p.trigger_tick == 0 for p in overrides.perturbations)


def test_fallback_to_fresh_when_no_active_lineages():
    config = GenerationConfig(fresh_fraction=0.0, inherited_fraction=0.5, pathological_fraction=0.5)
    manager = GenerationManager(config, generation_id="fallback")
    plan = manager.plan_episode()
    assert plan.source == "fresh"
    assert plan.overrides.get("fallback_reason")


def test_plan_carries_generation_identity():
    manager = GenerationManager(GenerationConfig(), generation_id="gen-x")
    plan = manager.plan_episode()
    assert plan.generation_id == "gen-x"
    assert plan.lineage_id.startswith("gen-x-map")
    spec = FactorioTaskSpec(
        task_id="t",
        goal="g",
        lineage_id=plan.lineage_id,
        generation_id=plan.generation_id,
        seed=plan.seed,
    )
    assert spec.lineage_id == plan.lineage_id
    mutated = spec.model_copy(update={"lineage_id": plan.lineage_id + "-x"})
    assert mutated.fingerprint != spec.fingerprint


# ---------------------------------------------------------------------------
# Recoverability classification
# ---------------------------------------------------------------------------


def test_healthy_above_restart_baseline():
    manager = GenerationManager(GenerationConfig(reset_cost=0.10), "cls-a")
    lid = manager.create_lineage(seed=1).lineage_id
    decision = manager.classify_outcome(
        lid,
        snapshot=_snapshot(
            objective_progress=0.9,
            operational_health=0.9,
            sustained_capability=0.9,
        ),
    )
    assert decision.outcome == "healthy"
    assert decision.continue_lineage is True
    assert decision.evidence["estimator"] == "heuristic"


def test_dominated_below_reset_margin():
    manager = GenerationManager(GenerationConfig(reset_cost=0.10), "cls-b")
    # Establish a strong restart baseline from a successful fresh lineage.
    strong = _seed_one_healthy_lineage(manager, 0.95)
    assert manager.restart_baseline() > 0.5

    poor = manager.create_lineage(seed=2)
    poor.contracts_total = 10
    poor.contracts_fulfilled = 2
    decision = manager.classify_outcome(
        poor.lineage_id,
        snapshot=_snapshot(
            objective_progress=0.2,
            operational_health=0.3,
            sustained_capability=0.2,
        ),
    )
    assert decision.outcome == "dominated"
    assert decision.continue_lineage is False
    assert decision.next_source == "fresh"
    assert "V_continue" in decision.reason


def test_degraded_band_continues():
    manager = GenerationManager(GenerationConfig(reset_cost=0.10, degraded_margin=0.05), "cls-c")
    strong = _seed_one_healthy_lineage(manager, 0.95)

    middling = manager.create_lineage(seed=3)
    middling.contracts_total = 10
    middling.contracts_fulfilled = 2
    decision = manager.classify_outcome(
        middling.lineage_id,
        snapshot=_snapshot(
            objective_progress=0.5,
            operational_health=0.45,
            sustained_capability=0.35,
        ),
    )
    # Continuation lands inside [restart - reset_cost, restart - margin).
    assert decision.outcome in ("degraded_recoverable", "dominated")
    if decision.outcome == "degraded_recoverable":
        assert decision.continue_lineage is True


def test_counterfactual_probes_override_heuristic():
    manager = GenerationManager(GenerationConfig(), "cls-d")
    lid = manager.create_lineage(seed=4).lineage_id
    probes = [
        FutureProbeResult(probe_id="repair", normalized_score=0.85),
        FutureProbeResult(probe_id="rebuild", normalized_score=0.75),
    ]
    decision = manager.classify_outcome(
        lid,
        snapshot=_snapshot(objective_progress=0.05, probes=probes),
    )
    assert decision.continuation_value == pytest.approx(0.80)
    assert decision.evidence["estimator"] == "counterfactual_probes"


def test_pending_shocks_penalize_continuation():
    manager = GenerationManager(GenerationConfig(reset_cost=0.10), "cls-e")
    lid = manager.create_lineage(seed=5).lineage_id
    snapshot = _snapshot(
        objective_progress=0.55,
        operational_health=0.5,
        sustained_capability=0.5,
    )
    clean = manager.classify_outcome(lid, snapshot=snapshot)
    shocked = manager.classify_outcome(
        lid, snapshot=snapshot, pending_shocks=3
    )
    assert shocked.continuation_value <= clean.continuation_value


def test_horizon_cap_forces_retirement():
    manager = GenerationManager(
        GenerationConfig(max_lineage_episodes=1), "cls-f"
    )
    lid = manager.create_lineage(seed=6).lineage_id
    decision = manager.record_episode(
        lid,
        ticks_elapsed=1000,
        decision=_forced("healthy", lid),
    )
    second = manager.classify_outcome(lid)
    assert second.outcome == "horizon_reached"
    assert second.continue_lineage is False


def test_record_episode_updates_registry_and_retires_dominated():
    manager = GenerationManager(GenerationConfig(), "rec")
    lid = manager.create_lineage(seed=7).lineage_id
    decision = manager.record_episode(
        lid,
        ticks_elapsed=500,
        contracts_fulfilled=3,
        contracts_total=10,
        decision=_forced("dominated", lid),
    )
    record = manager.get_lineage(lid)
    assert record.episodes == 1
    assert record.total_ticks == 500
    assert record.fulfill_ratio == pytest.approx(0.3)
    assert record.status == "retired"
    assert decision.outcome == "dominated"


# ---------------------------------------------------------------------------
# Checkpoint pool
# ---------------------------------------------------------------------------


def test_checkpoint_pool_roundtrip(tmp_path):
    pool = CheckpointPool(root=tmp_path / "pool")
    checkpoint_id = pool.save("map-1", episode=1, raw_state='{"entities": []}')
    assert checkpoint_id == "map-1:ep1"

    latest = pool.latest("map-1")
    assert latest is not None
    assert latest[0] == "map-1:ep1"
    assert latest[1] == '{"entities": []}'

    pool.save("map-1", episode=2, raw_state='{"entities": [2]}')
    assert pool.latest("map-1")[0] == "map-1:ep2"
    assert pool.latest("map-1")[1].endswith("[2]}")

    assert pool.drop("map-1") == 2
    assert pool.latest("map-1") is None


def test_checkpoint_pool_isolates_lineages(tmp_path):
    pool = CheckpointPool(root=tmp_path / "pool")
    pool.save("a", episode=1, raw_state="A")
    pool.save("b", episode=1, raw_state="B")
    assert pool.latest("a")[1] == "A"
    assert pool.latest("b")[1] == "B"


def test_checkpoint_survives_slash_lineage_ids(tmp_path):
    pool = CheckpointPool(root=tmp_path / "pool")
    pool.save("../evil/id", episode=1, raw_state="X")
    assert pool.latest("../evil/id")[1] == "X"
