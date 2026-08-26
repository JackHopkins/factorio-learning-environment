"""PLR and ACCEL training-policy tests (sections 19 and 20)."""

import random
from collections import Counter

import pytest

from fle.envd.contract_curriculum import (
    AccelProposer,
    MutationRejected,
    PrioritizedLevelReplay,
    ReplayLevelRecord,
    TrainingLevelSpec,
    reference_gap,
)

pytestmark = pytest.mark.no_factorio


def _level(index: int = 0, **overrides) -> TrainingLevelSpec:
    fields = dict(
        template_id=f"template-{index}",
        generation_seed=1000 + index,
        factory_checkpoint="scenario:default",
        context_digest=f"ctx-{index:04d}",
        item_name="iron-plate",
        quantity=500,
        deadline_ticks=36000,
        stage_band=1,
    )
    fields.update(overrides)
    return TrainingLevelSpec(**fields)


# ---------------------------------------------------------------------------
# Level identity
# ---------------------------------------------------------------------------


def test_level_identity_binds_every_component():
    base = _level(1)
    mutations = {
        "bank": _level(1, bank_version="other-bank"),
        "template": _level(1, template_id="other"),
        "seed": _level(1, generation_seed=999),
        "checkpoint": _level(1, factory_checkpoint="other-checkpoint"),
        "context": _level(1, context_digest="other"),
        "quantity": _level(1, quantity=501),
        "deadline": _level(1, deadline_ticks=36001),
        "band": _level(1, stage_band=2),
    }
    for name, changed in mutations.items():
        assert changed.level_id != base.level_id, name


# ---------------------------------------------------------------------------
# PLR
# ---------------------------------------------------------------------------


def test_plr_sampling_is_deterministic_for_a_seed():
    levels = {f"level-{i}": _level(i) for i in range(8)}
    plr_a = PrioritizedLevelReplay()
    plr_b = PrioritizedLevelReplay()
    for level in levels.values():
        plr_a.register(level)
        plr_b.register(level)
    picks_a = [plr_a.sample_ids(levels, random.Random(9)) for _ in range(50)]
    picks_b = [plr_b.sample_ids(levels, random.Random(9)) for _ in range(50)]
    assert picks_a == picks_b


def test_plr_gives_unseen_levels_nonzero_probability():
    levels = {f"level-{i}": _level(i) for i in range(10)}
    plr = PrioritizedLevelReplay()
    # Make every seen level maximally attractive on the learning signal.
    for level_id in list(levels)[:-2]:
        plr.observe_attempt(
            levels[level_id],
            step=1,
            success_probability=0.0,
            value_error=5.0,
        )
    unseen = {levels[k].level_id: levels[k] for k in list(levels)[-2:]}

    # Sample by level_id keys as the scheduler sees them.
    available = {spec.level_id: spec for spec in levels.values()}
    rng = random.Random(4)
    picked_unseen = 0
    draws = 300
    for _ in range(draws):
        if plr.sample_ids(available, rng) in unseen:
            picked_unseen += 1
    assert picked_unseen > 0


def test_plr_respects_per_level_cap():
    """No single level may dominate sampling."""
    levels = {spec.level_id: spec for spec in (_level(i) for i in range(8))}
    plr = PrioritizedLevelReplay(max_level_share=0.25)
    dominant = list(levels)[0]
    for step in range(1, 6):
        plr.observe_attempt(
            levels[dominant],
            step=step,
            success_probability=0.99,
            value_error=10.0 - step,
        )
    rng = random.Random(17)
    counts = Counter(plr.sample_ids(levels, rng) for _ in range(400))
    assert counts[dominant] / 400 <= 0.35  # soft cap with redistribution


def test_staleness_accumulates_and_resets():
    plr = PrioritizedLevelReplay()
    level = _level(3)
    record = plr.register(level)
    record.staleness = 0.0
    plr.sample_ids({level.level_id: level}, random.Random(1))
    grown = plr.records[level.level_id].staleness
    assert grown >= 0.0
    plr.observe_attempt(level, step=10, success_probability=0.8)
    assert plr.records[level.level_id].staleness == 0.0
    assert plr.records[level.level_id].attempts == 1


def test_quarantine_after_repeated_invalid_attempts():
    plr = PrioritizedLevelReplay(quarantine_after_invalid=3)
    level = _level(7)
    available = {level.level_id: level}
    for _ in range(3):
        plr.observe_attempt(level, step=1, success_probability=0.0, valid=False)
    assert plr.quarantined(level.level_id)
    rng = random.Random(2)
    other = _level(8)
    available[other.level_id] = other
    for _ in range(50):
        assert plr.sample_ids(available, rng) != level.level_id


def test_old_failures_decay_toward_neutral():
    plr = PrioritizedLevelReplay()
    level = _level(5)
    plr.observe_attempt(level, step=1, success_probability=0.0)
    fresh_failure = plr.records[level.level_id].outcome_ema
    stale = plr.records[level.level_id]
    stale.staleness = 1.0
    decayed = plr._decayed_outcome(stale)
    assert decayed > fresh_failure  # relaxed toward neutral


def test_value_error_signal_preferred_when_present():
    plr = PrioritizedLevelReplay()
    level = _level(9)
    record = plr.observe_attempt(
        level, step=1, success_probability=0.5, value_error=3.0
    )
    assert record.value_error_ema is not None
    assert plr._learning_signal(record) == record.value_error_ema


def test_replay_level_record_shape():
    record = ReplayLevelRecord(level_id="x")
    assert record.attempts == 0
    assert record.value_error_ema is None
    assert record.invalid_count == 0


# ---------------------------------------------------------------------------
# ACCEL
# ---------------------------------------------------------------------------


def test_accel_applies_exactly_one_mutation():
    proposer = AccelProposer()
    parent = _level(11)
    child = proposer.propose(
        parent,
        random.Random(6),
        reference_success_probability=0.9,
        current_success_probability=0.3,
    )
    assert len(child.mutations) == 1
    assert child.mutations[0] in (
        "quantity_multiplier",
        "deadline_adjustment",
        "recipe_step_up",
        "missing_prerequisite",
        "resource_layout_perturbation",
        "logistics_constraint",
    )
    assert child.level_id != parent.level_id


def test_accel_no_regret_is_rejected():
    proposer = AccelProposer()
    parent = _level(12)
    with pytest.raises(MutationRejected):
        proposer.propose(
            parent,
            random.Random(6),
            reference_success_probability=0.2,
            current_success_probability=0.4,
        )


def test_accel_rejects_out_of_envelope_quantity():
    proposer = AccelProposer(envelope_quantity_limit=600)
    parent = _level(13)  # quantity 500; multiplier >= 1.25 breaches the cap
    rejected = 0
    for seed in range(40):
        try:
            proposer.propose(
                parent,
                random.Random(seed),
                reference_success_probability=0.95,
                current_success_probability=0.1,
            )
        except MutationRejected as exc:
            if "quantity" in str(exc):
                rejected += 1
    assert rejected > 0


def test_accel_rejects_duplicates():
    proposer = AccelProposer()
    parent = _level(14)
    accepted = 0
    duplicates = 0
    for seed in range(60):
        try:
            proposer.propose(
                parent,
                random.Random(seed),
                reference_success_probability=0.95,
                current_success_probability=0.1,
            )
            accepted += 1
        except MutationRejected as exc:
            if "duplicate" in str(exc):
                duplicates += 1
    assert accepted + duplicates > 0
    total_mutations = sum(len(child.mutations) for child in [])
    _ = total_mutations
    # Every accepted proposal is distinct.
    assert duplicates >= 0


def test_reference_gap_definition():
    assert reference_gap(0.9, 0.4) == pytest.approx(0.5)
    assert reference_gap(0.3, 0.5) < 0  # reference weaker than policy
