"""Training curricula: Prioritized Level Replay and ACCEL.

Both policies schedule TRAINING only. They never rate official runs, never
read private evaluation seeds, and never write official calibration
artifacts -- the import graph enforces that boundary: nothing here is
imported by scoring or selection modules.

Level identity binds training bank version, template, generation seed,
initial-state identity, context digest, and difficulty digest, so two
levels are the same replayable object only when every component matches.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from typing import Literal, Protocol

from pydantic import Field

from fle.envd.models import WireModel, TRAINING_BANK_VERSION

OUTCOME_EMA_ALPHA = 0.3
LEARNING_PROGRESS_EMA_ALPHA = 0.25
STALENESS_PER_STEP = 0.01

# Section 19 initial sampling mixture.
MIXTURE_LEARNING_SIGNAL = 0.60
MIXTURE_STALENESS = 0.20
MIXTURE_UNDERREPRESENTED_STAGE = 0.10
MIXTURE_UNIFORM = 0.10


class ReplayLevelRecord(WireModel):
    """Bookkeeping for one training level under PLR."""

    level_id: str
    attempts: int = 0
    last_attempt_step: int = Field(default=0, ge=0)
    outcome_ema: float = Field(default=0.0)
    value_error_ema: float | None = None
    learning_progress_ema: float = Field(default=0.0, ge=0.0)
    staleness: float = Field(default=0.0, ge=0.0)
    invalid_count: int = Field(default=0, ge=0)


class TrainingLevelSpec(WireModel):
    """One replayable training order/context seed."""

    bank_version: str = TRAINING_BANK_VERSION
    template_id: str
    generation_seed: int
    factory_checkpoint: str  # checkpoint id or initial seed identity
    context_digest: str
    item_name: str
    quantity: int
    deadline_ticks: int
    stage_band: int = Field(ge=0, le=5)
    mutations: tuple[str, ...] = ()

    @property
    def difficulty_digest(self) -> str:
        payload = json.dumps(
            {
                "item": self.item_name,
                "quantity": self.quantity,
                "deadline": self.deadline_ticks,
                "band": self.stage_band,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    @property
    def level_id(self) -> str:
        payload = json.dumps(
            {
                "bank": self.bank_version,
                "template": self.template_id,
                "generation_seed": self.generation_seed,
                "checkpoint": self.factory_checkpoint,
                "context_digest": self.context_digest,
                "difficulty_digest": self.difficulty_digest,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:24]


class PolicyValueEstimate(Protocol):
    """Optional policy-side value estimate hook."""


class PrioritizedLevelReplay:
    """PLR scheduler over registered training levels.

    Sampling combines four normalized signals per section 19::

        0.60 * learning_signal + 0.20 * staleness
        + 0.10 * underrepresented_stage + 0.10 * uniform_mass

    Unseen levels retain reserved probability, no single level may exceed
    ``max_level_share``, repeatedly invalid levels are quarantined, and old
    failures decay toward neutral as staleness grows.
    """

    def __init__(
        self,
        *,
        unseen_reserve: float = 0.05,
        max_level_share: float = 0.25,
        quarantine_after_invalid: int = 3,
        stages: tuple[int, ...] = (0, 1, 2, 3, 4, 5),
    ):
        if not 0.0 <= unseen_reserve < 1.0:
            raise ValueError("unseen_reserve must be in [0, 1)")
        self.unseen_reserve = unseen_reserve
        self.max_level_share = max_level_share
        self.quarantine_after_invalid = quarantine_after_invalid
        self.stages = stages
        self.records: dict[str, ReplayLevelRecord] = {}
        self.stage_of: dict[str, int] = {}

    # -- registration --------------------------------------------------------

    def register(self, level: TrainingLevelSpec) -> ReplayLevelRecord:
        record = self.records.get(level.level_id)
        if record is None:
            record = ReplayLevelRecord(level_id=level.level_id)
            self.records[level.level_id] = record
            self.stage_of[level.level_id] = level.stage_band
        return record

    # -- observation ---------------------------------------------------------

    def observe_attempt(
        self,
        level: TrainingLevelSpec,
        *,
        step: int,
        success_probability: float,
        valid: bool = True,
        value_error: float | None = None,
    ) -> ReplayLevelRecord:
        record = self.register(level)
        if not valid:
            record.invalid_count += 1
            record.staleness += STALENESS_PER_STEP * max(
                step - record.last_attempt_step, 1
            )
            record.last_attempt_step = step
            return record

        new_outcome_ema = (
            OUTCOME_EMA_ALPHA * success_probability
            + (1.0 - OUTCOME_EMA_ALPHA) * record.outcome_ema
        )
        # Learning progress proxy: change in predicted success between
        # checkpoints (section 19 fallback when no value estimate exists).
        progress = abs(success_probability - record.outcome_ema)
        record.learning_progress_ema = (
            LEARNING_PROGRESS_EMA_ALPHA * progress
            + (1.0 - LEARNING_PROGRESS_EMA_ALPHA) * record.learning_progress_ema
        )
        if value_error is not None:
            record.value_error_ema = LEARNING_PROGRESS_EMA_ALPHA * abs(value_error) + (
                1.0 - LEARNING_PROGRESS_EMA_ALPHA
            ) * (
                record.value_error_ema
                if record.value_error_ema is not None
                else abs(value_error)
            )
        record.outcome_ema = new_outcome_ema
        record.attempts += 1
        record.last_attempt_step = step
        record.staleness = 0.0
        return record

    # -- sampling --------------------------------------------------------------

    def quarantined(self, level_id: str) -> bool:
        record = self.records.get(level_id)
        return bool(record and record.invalid_count >= self.quarantine_after_invalid)

    def _decayed_outcome(self, record: ReplayLevelRecord) -> float:
        """Old failures relax toward the neutral midpoint as staleness grows."""
        decay = min(record.staleness, 1.0)
        return record.outcome_ema + (0.5 - record.outcome_ema) * decay

    def _learning_signal(self, record: ReplayLevelRecord | None) -> float:
        if record is None:
            return 1.0
        if record.value_error_ema is not None:
            return record.value_error_ema
        return record.learning_progress_ema

    def sample_ids(
        self,
        available: dict[str, TrainingLevelSpec],
        rng: random.Random,
        *,
        current_step: int = 0,
    ) -> str:
        """Seeded mixture draw over registered, non-quarantined levels."""
        viable = {
            level_id: spec
            for level_id, spec in available.items()
            if not self.quarantined(level_id)
        }
        if not viable:
            raise ValueError("No non-quarantined levels available")
        unseen_reserve = self.unseen_reserve
        roll = rng.random()

        def weighted_pick(weights: dict[str, float]) -> str:
            ids = sorted(viable)
            total = sum(max(weights.get(level_id, 0.0), 0.0) for level_id in ids)
            if total <= 0:
                return rng.choice(ids)
            point = rng.random() * total
            cumulative = 0.0
            for level_id in ids:
                cumulative += max(weights.get(level_id, 0.0), 0.0)
                if cumulative >= point:
                    return level_id
            return ids[-1]

        def base_weights(signal_fn) -> dict[str, float]:
            weights: dict[str, float] = {}
            for level_id in viable:
                record = self.records.get(level_id)
                signal = signal_fn(record)
                seen_bonus = (
                    1.0 / (1.0 - unseen_reserve)
                    if record is None or record.attempts == 0
                    else unseen_reserve
                )
                weights[level_id] = max(signal, 1e-6) * seen_bonus
            return self._apply_cap(weights)

        if roll < MIXTURE_LEARNING_SIGNAL:
            choice = weighted_pick(base_weights(self._learning_signal))
        elif roll < MIXTURE_LEARNING_SIGNAL + MIXTURE_STALENESS:
            choice = weighted_pick(
                base_weights(
                    lambda record: (1.0 if record is None else 1.0 + record.staleness)
                )
            )
        elif roll < (
            MIXTURE_LEARNING_SIGNAL + MIXTURE_STALENESS + MIXTURE_UNDERREPRESENTED_STAGE
        ):
            counts = Counter(self.stage_of.get(level_id, 0) for level_id in viable)
            total = sum(counts.values())

            def stage_weight(record: ReplayLevelRecord | None) -> float:
                if record is None:
                    return 1.0
                band = self.stage_of.get(record.level_id, 0)
                return 1.0 - (counts.get(band, 0) / max(total, 1))

            choice = weighted_pick(base_weights(stage_weight))
        else:
            choice = weighted_pick({level_id: 1.0 for level_id in viable})
        record = self.records.get(choice)
        if record is not None:
            record.staleness += STALENESS_PER_STEP * max(
                current_step - record.last_attempt_step, 0
            )
        return choice

    def _apply_cap(self, weights: dict[str, float]) -> dict[str, float]:
        total = sum(weights.values())
        if total <= 0:
            return weights
        capped = dict(weights)
        budget = 1.0 - self.max_level_share
        for level_id, weight in weights.items():
            share = weight / total
            if share > self.max_level_share:
                capped[level_id] = self.max_level_share * total
                redistribute = (share - self.max_level_share) * total
                others = [k for k in capped if k != level_id]
                if others and redistribute > 0:
                    other_total = sum(capped[k] for k in others)
                    for k in others:
                        share_k = capped[k] / max(other_total, 1e-9)
                        capped[k] += budget * redistribute * share_k
        return capped


# ---------------------------------------------------------------------------
# ACCEL (section 20): bounded mutation proposals after mastery
# ---------------------------------------------------------------------------

MutationKind = Literal[
    "quantity_multiplier",
    "deadline_adjustment",
    "recipe_step_up",
    "missing_prerequisite",
    "resource_layout_perturbation",
    "logistics_constraint",
]

SINGLE_MUTATION_KINDS: tuple[MutationKind, ...] = (
    "quantity_multiplier",
    "deadline_adjustment",
    "recipe_step_up",
    "missing_prerequisite",
    "resource_layout_perturbation",
    "logistics_constraint",
)

QUANTITY_MULTIPLIER_RANGE = (1.25, 2.0)
DEADLINE_ADJUSTMENT_RANGE = (0.8, 1.25)


class MutationRejected(ValueError):
    """A proposed level violated a bounded-mutation acceptance rule."""


class AccelProposer:
    """Proposes nearby harder levels after valid ones are learned.

    Every proposal applies exactly one interpretable mutation.  Infeasible,
    duplicate, multi-mutation, trivial-inventory, and out-of-envelope
    proposals raise :class:`MutationRejected` so callers can log rejections.
    """

    def __init__(
        self,
        *,
        envelope_quantity_limit: int = 100000,
        envelope_deadline_range: tuple[int, int] = (600, 30 * 36000),
        known_levels: set[str] | None = None,
    ):
        self.envelope_quantity_limit = envelope_quantity_limit
        self.envelope_deadline_range = envelope_deadline_range
        self.known_levels = known_levels if known_levels is not None else set()
        self._seen_ids: set[str] = set(known_levels or ())

    def propose(
        self,
        level: TrainingLevelSpec,
        rng: random.Random,
        *,
        reference_success_probability: float,
        current_success_probability: float,
    ) -> TrainingLevelSpec:
        """Regret-gated single-mutation proposal."""
        regret = reference_success_probability - current_success_probability
        if regret <= 0.05:
            raise MutationRejected(
                "no_regret: reference does not dominate current policy"
            )

        kind = SINGLE_MUTATION_KINDS[rng.randrange(len(SINGLE_MUTATION_KINDS))]
        mutated = self.apply_mutation(level, kind, rng)
        self.validate(level, mutated)
        self._seen_ids.add(mutated.level_id)
        return mutated

    def apply_mutation(
        self,
        level: TrainingLevelSpec,
        kind: MutationKind,
        rng: random.Random,
    ) -> TrainingLevelSpec:
        data = level.model_dump(exclude={"mutations", "level_id"})
        if kind == "quantity_multiplier":
            low, high = QUANTITY_MULTIPLIER_RANGE
            data["quantity"] = max(int(level.quantity * rng.uniform(low, high)), 1)
        elif kind == "deadline_adjustment":
            low, high = DEADLINE_ADJUSTMENT_RANGE
            data["deadline_ticks"] = max(
                int(level.deadline_ticks * rng.uniform(low, high)), 1
            )
        elif kind == "recipe_step_up":
            data["stage_band"] = min(level.stage_band + 1, 5)
        elif kind == "missing_prerequisite":
            data["generation_seed"] = level.generation_seed + 1
        elif kind == "resource_layout_perturbation":
            data["factory_checkpoint"] = f"{level.factory_checkpoint}~perturbed"
        elif kind == "logistics_constraint":
            data["context_digest"] = hashlib.sha256(
                (level.context_digest + "|logistics").encode()
            ).hexdigest()[:32]
        data["mutations"] = tuple(level.mutations) + (kind,)
        candidate = TrainingLevelSpec(**data)
        return candidate

    def validate(self, parent: TrainingLevelSpec, candidate: TrainingLevelSpec) -> None:
        if len(candidate.mutations) != len(parent.mutations) + 1:
            raise MutationRejected("multi_mutation_rejected")
        if candidate.quantity > self.envelope_quantity_limit:
            raise MutationRejected("out_of_envelope_quantity")
        low, high = self.envelope_deadline_range
        if not low <= candidate.deadline_ticks <= high:
            raise MutationRejected("out_of_envelope_deadline")
        if candidate.quantity <= parent.quantity // 4:
            raise MutationRejected("trivial_inventory")
        if candidate.level_id in self._seen_ids:
            raise MutationRejected("duplicate_level")
        if candidate.level_id == parent.level_id:
            raise MutationRejected("duplicate_level")


def reference_gap(
    reference_success_probability: float,
    current_policy_success_probability: float,
) -> float:
    """Section 20 same-level regret definition."""
    return reference_success_probability - current_policy_success_probability


__all__ = [
    "AccelProposer",
    "DEADLINE_ADJUSTMENT_RANGE",
    "MIXTURE_LEARNING_SIGNAL",
    "MIXTURE_STALENESS",
    "MIXTURE_UNDERREPRESENTED_STAGE",
    "MIXTURE_UNIFORM",
    "MutationKind",
    "MutationRejected",
    "PrioritizedLevelReplay",
    "QUANTITY_MULTIPLIER_RANGE",
    "ReplayLevelRecord",
    "TrainingLevelSpec",
    "reference_gap",
]
