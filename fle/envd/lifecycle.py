"""Map lifecycle management across a training generation.

Implements the generation-level rollout policy:

- weight-update cadence is decoupled from map-reset cadence: one frozen
  policy plays out a generation composed of fresh seeds, inherited
  continuations, and deliberately pathological states;
- map retirement follows ``V_continue(s) < V_restart - C_reset``;
- doomed maps are terminated operationally but preserved pedagogically via
  their checkpoint and transition records.

Counterfactual branch probes, when present in a state-quality snapshot,
override the heuristic continuation estimate; without them the classifier
uses documented proxies so the loop is runnable before AgentENV forks are
enabled.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fle.envd.models import (
    DisruptionScheduleSpec,
    LifecycleDecision,
    LineageOutcome,
    PerturbationSpec,
    RolloutSource,
    StateQualitySnapshot,
)

SOURCE_ORDER: tuple[RolloutSource, ...] = ("fresh", "inherited", "pathological")

# Absolute floor below which a lineage is considered degraded even when no
# restart baseline exists yet.
_DEGRADED_FLOOR = 0.30


@dataclass(frozen=True)
class GenerationConfig:
    """Composition and horizon policy for one frozen-policy generation."""

    fresh_fraction: float = 0.55
    inherited_fraction: float = 0.25
    pathological_fraction: float = 0.20
    max_lineage_ticks: int = 8 * 216000
    max_lineage_episodes: int = 6
    # Margin required to keep a lineage whose continuation value trails the
    # fresh-start baseline: retire when V_continue < V_restart - C_reset.
    reset_cost: float = 0.10
    degraded_margin: float = 0.05
    rng_seed: int = 0

    def fractions(self) -> dict[RolloutSource, float]:
        return {
            "fresh": self.fresh_fraction,
            "inherited": self.inherited_fraction,
            "pathological": self.pathological_fraction,
        }


@dataclass
class LineageRecord:
    lineage_id: str
    seed: int
    status: str = "active"
    source_of_origin: RolloutSource = "fresh"
    episodes: int = 0
    total_ticks: int = 0
    contracts_fulfilled: int = 0
    contracts_total: int = 0
    outcomes: list[str] = field(default_factory=list)

    @property
    def fulfill_ratio(self) -> float:
        if self.contracts_total <= 0:
            return 0.0
        return self.contracts_fulfilled / self.contracts_total


@dataclass
class EpisodePlan:
    """What the trainer should launch next."""

    source: RolloutSource
    lineage_id: str | None
    seed: int
    generation_id: str
    episode_index: int
    overrides: dict[str, Any] = field(default_factory=dict)


class CheckpointPool:
    """Disk-backed GameState persistence keyed by lineage."""

    def __init__(self, root: Path | str | None = None):
        import os

        base = root or os.environ.get("FLE_LIFECYCLE_DIR", ".fle/lifecycle")
        self.root = Path(base)
        self.root.mkdir(parents=True, exist_ok=True)

    def _lineage_dir(self, lineage_id: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in lineage_id)
        path = self.root / safe
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save(
        self,
        lineage_id: str,
        episode: int,
        raw_state: str,
        quality_summary: dict[str, Any] | None = None,
    ) -> str:
        checkpoint_id = f"{lineage_id}:ep{episode}"
        payload = {
            "checkpoint_id": checkpoint_id,
            "lineage_id": lineage_id,
            "episode": episode,
            "state": raw_state,
            "quality": quality_summary or {},
        }
        path = self._lineage_dir(lineage_id) / f"ep{episode}.json"
        path.write_text(json.dumps(payload))
        return checkpoint_id

    def latest(self, lineage_id: str) -> tuple[str, str] | None:
        """Return ``(checkpoint_id, raw_state)`` for the newest checkpoint."""
        directory = self._lineage_dir(lineage_id)
        candidates = sorted(
            directory.glob("ep*.json"),
            key=lambda p: int(p.stem[2:]) if p.stem[2:].isdigit() else -1,
        )
        if not candidates:
            return None
        payload = json.loads(candidates[-1].read_text())
        return payload["checkpoint_id"], payload["state"]

    def get(self, checkpoint_id: str) -> tuple[str, str] | None:
        """Exact-id fetch for ids shaped ``<lineage>:ep<N>``."""
        lineage, separator, episode = checkpoint_id.rpartition(":ep")
        if not separator or not episode.isdigit():
            return None
        path = self._lineage_dir(lineage) / f"ep{episode}.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text())
        return checkpoint_id, payload["state"]

    def drop(self, lineage_id: str) -> int:
        directory = self._lineage_dir(lineage_id)
        removed = 0
        for path in directory.glob("ep*.json"):
            path.unlink()
            removed += 1
        return removed


class GenerationManager:
    """Deterministic rollout-source planner and lineage registry."""

    def __init__(
        self,
        config: GenerationConfig | None = None,
        generation_id: str = "gen-0",
        checkpoints: CheckpointPool | None = None,
    ):
        self.config = config or GenerationConfig()
        self.generation_id = generation_id
        self.checkpoints = checkpoints or CheckpointPool()
        self._rng = random.Random(f"lifecycle:{generation_id}:{self.config.rng_seed}")
        self._source_counts: dict[RolloutSource, int] = {
            "fresh": 0,
            "inherited": 0,
            "pathological": 0,
        }
        self._episodes_planned = 0
        self._lineages: dict[str, LineageRecord] = {}
        self._fresh_first_scores: list[float] = []
        self._sequence = 0

    # -- source sampling ----------------------------------------------------

    def sample_source(self) -> RolloutSource:
        """Quota-respecting largest-remainder draw; exact long-run mix."""

        self._episodes_planned += 1
        total = self._episodes_planned
        best_source: RolloutSource = SOURCE_ORDER[0]
        best_deficit = float("-inf")
        for source in SOURCE_ORDER:
            target = self.config.fractions()[source] * total
            deficit = target - self._source_counts[source]
            if deficit > best_deficit + 1e-9:
                best_deficit = deficit
                best_source = source
        self._source_counts[best_source] += 1
        return best_source

    def composition(self) -> dict[RolloutSource, float]:
        total = sum(self._source_counts.values()) or 1
        return {
            source: self._source_counts[source] / total
            for source in SOURCE_ORDER
        }

    # -- lineage registry ---------------------------------------------------

    def create_lineage(self, seed: int | None = None) -> LineageRecord:
        self._sequence += 1
        record = LineageRecord(
            lineage_id=f"{self.generation_id}-map{self._sequence:04d}",
            seed=self._rng.randint(0, 2**31 - 1) if seed is None else seed,
        )
        self._lineages[record.lineage_id] = record
        return record

    def get_lineage(self, lineage_id: str) -> LineageRecord:
        return self._lineages[lineage_id]

    def active_lineages(self) -> list[LineageRecord]:
        return [
            record
            for record in self._lineages.values()
            if record.status == "active"
        ]

    # -- episode planning ---------------------------------------------------

    def plan_episode(self, seed: int | None = None) -> EpisodePlan:
        """Decide the next rollout: source, lineage, and task overrides."""

        source = self.sample_source()
        if source == "fresh":
            record = self.create_lineage(seed)
            record.source_of_origin = "fresh"
            return EpisodePlan(
                source="fresh",
                lineage_id=record.lineage_id,
                seed=record.seed,
                generation_id=self.generation_id,
                episode_index=1,
                overrides={},
            )

        candidates = [
            record
            for record in self.active_lineages()
            if self._horizon_reached(record) is False
            # Continuation requires history: a lineage that has never run an
            # episode is neither inherited state nor a recovery target.
            if record.episodes >= 1
        ]
        if not candidates:
            # Quotas demand an inherited/pathological episode but nothing is
            # alive: fall back to fresh rather than fabricating history.
            record = self.create_lineage(seed)
            record.source_of_origin = "fresh"
            return EpisodePlan(
                source="fresh",
                lineage_id=record.lineage_id,
                seed=record.seed,
                generation_id=self.generation_id,
                episode_index=1,
                overrides={"fallback_reason": f"no active lineage for {source}"},
            )

        if source == "pathological":
            # Prefer genuinely degraded lineages so recovery skill is
            # exercised on real damage, not synthetic noise.
            ranked = sorted(
                candidates,
                key=lambda r: (r.fulfill_ratio, -r.episodes),
            )
            record = ranked[0]
            return EpisodePlan(
                source="pathological",
                lineage_id=record.lineage_id,
                seed=record.seed,
                generation_id=self.generation_id,
                episode_index=record.episodes + 1,
                overrides={
                    "perturbations": DisruptionScheduleSpec(
                        perturbations=[
                            PerturbationSpec(
                                perturbation_id="pathos-000-degrade",
                                kind="entity_destruction",
                                trigger_tick=0,
                                parameters={
                                    "entity_types": ["boiler", "generator"],
                                    "count": 2,
                                    "search_radius": 200,
                                },
                            ),
                            PerturbationSpec(
                                perturbation_id="pathos-001-deplete",
                                kind="resource_depletion",
                                trigger_tick=0,
                                parameters={"radius": 28},
                            ),
                        ]
                    )
                },
            )

        # Inherited: continue the healthiest active lineage.
        record = max(candidates, key=lambda r: r.fulfill_ratio)
        return EpisodePlan(
            source="inherited",
            lineage_id=record.lineage_id,
            seed=record.seed,
            generation_id=self.generation_id,
            episode_index=record.episodes + 1,
            overrides={},
        )

    # -- outcome recording --------------------------------------------------

    def record_episode(
        self,
        lineage_id: str,
        *,
        ticks_elapsed: int,
        contracts_fulfilled: int = 0,
        contracts_total: int = 0,
        snapshot: StateQualitySnapshot | None = None,
        decision: LifecycleDecision | None = None,
    ) -> LifecycleDecision:
        record = self._lineages[lineage_id]
        record.episodes += 1
        record.total_ticks += max(ticks_elapsed, 0)
        record.contracts_total += contracts_total
        record.contracts_fulfilled += contracts_fulfilled

        decision = decision or self.classify_outcome(
            lineage_id,
            snapshot=snapshot,
        )
        record.outcomes.append(decision.outcome)
        if decision.outcome == "degraded_recoverable":
            record.status = "active"
        elif decision.outcome == "healthy":
            record.status = "active"
        else:
            record.status = "retired"

        if (
            record.source_of_origin == "fresh"
            and record.episodes == 1
            and snapshot is not None
        ):
            score = self._episode_score(snapshot, record)
            self._fresh_first_scores.append(score)
        return decision

    def restart_baseline(self) -> float:
        """Mean first-episode value of fresh lineages: the V_restart proxy."""

        if not self._fresh_first_scores:
            return 0.5
        return sum(self._fresh_first_scores) / len(self._fresh_first_scores)

    # -- classification -----------------------------------------------------

    @staticmethod
    def _episode_score(
        snapshot: StateQualitySnapshot | None, record: LineageRecord
    ) -> float:
        if snapshot is None:
            return min(record.fulfill_ratio, 1.0)
        parts = [snapshot.objective_progress]
        if snapshot.sustained_capability is not None:
            parts.append(snapshot.sustained_capability)
        if snapshot.milestone_progress is not None:
            parts.append(snapshot.milestone_progress)
        parts.append(min(record.fulfill_ratio, 1.0))
        return sum(parts) / len(parts)

    def _continuation_value(
        self,
        record: LineageRecord,
        snapshot: StateQualitySnapshot | None,
    ) -> tuple[float, dict[str, Any]]:
        probes = snapshot.future_probes if snapshot is not None else []
        if probes:
            value = sum(p.normalized_score for p in probes) / len(probes)
            return value, {
                "estimator": "counterfactual_probes",
                "probes": len(probes),
            }

        components: list[tuple[float, float]] = []  # (value, weight)
        if snapshot is not None:
            components.append((snapshot.objective_progress, 0.25))
            components.append((snapshot.operational_health or 0.5, 0.25))
            components.append(
                ((snapshot.sustained_capability or 0.5), 0.15)
            )
            components.append(((snapshot.safety or 1.0), 0.10))
        components.append((min(record.fulfill_ratio, 1.0), 0.25))

        total_weight = sum(weight for _, weight in components)
        if total_weight <= 0:
            return 0.0, {"estimator": "heuristic", "components": 0}
        value = sum(v * w for v, w in components) / total_weight
        # Repeated hard failures erode expected continuation value.
        penalty = 0.05 * max(record.outcomes.count("dominated") - 1, 0)
        return max(value - penalty, 0.0), {
            "estimator": "heuristic",
            "components": len(components),
            "dominance_penalty": penalty,
        }

    def _horizon_reached(self, record: LineageRecord) -> bool:
        return (
            record.total_ticks >= self.config.max_lineage_ticks
            or record.episodes >= self.config.max_lineage_episodes
        )

    def classify_outcome(
        self,
        lineage_id: str,
        *,
        snapshot: StateQualitySnapshot | None = None,
        pending_shocks: int = 0,
    ) -> LifecycleDecision:
        record = self._lineages[lineage_id]

        if self._horizon_reached(record):
            return LifecycleDecision(
                lineage_id=lineage_id,
                outcome="horizon_reached",
                continue_lineage=False,
                next_source="fresh",
                continuation_value=0.0,
                restart_value=self.restart_baseline(),
                reset_cost=self.config.reset_cost,
                reason="lineage horizon cap reached",
            )

        continuation, evidence = self._continuation_value(record, snapshot)
        restart = self.restart_baseline()
        if pending_shocks:
            evidence["pending_unrecovered_shocks"] = pending_shocks
            continuation = max(continuation - 0.05 * pending_shocks, 0.0)

        if continuation < restart - self.config.reset_cost:
            outcome: LineageOutcome = "dominated"
            continue_lineage = False
            next_source: RolloutSource | None = "fresh"
            reason = (
                f"V_continue({continuation:.3f}) < "
                f"V_restart({restart:.3f}) - C_reset({self.config.reset_cost})"
            )
        elif continuation < max(
            restart - self.config.degraded_margin, _DEGRADED_FLOOR
        ):
            outcome = "degraded_recoverable"
            continue_lineage = True
            next_source = None
            reason = "below healthy band but not economically dominated"
        else:
            outcome = "healthy"
            continue_lineage = True
            next_source = None
            reason = "operating above the restart baseline"

        return LifecycleDecision(
            lineage_id=lineage_id,
            outcome=outcome,
            continue_lineage=continue_lineage,
            next_source=next_source,
            continuation_value=round(continuation, 4),
            restart_value=round(restart, 4),
            reset_cost=self.config.reset_cost,
            reason=reason,
            evidence=evidence,
        )


__all__ = [
    "GenerationConfig",
    "GenerationManager",
    "EpisodePlan",
    "LineageRecord",
    "CheckpointPool",
]
