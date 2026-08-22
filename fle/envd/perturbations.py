"""Hidden world disruptions: deterministic shock schedules and recovery
measurement.

The schedule ships inside the task spec like hidden unit tests; effects land
on whatever the live factory contains when a trigger tick passes.  For every
throughput-affecting disruption the engine estimates the pre-shock output
rate from production statistics and measures
``T_recovery = t(return to threshold x baseline) - t(failure)``.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from typing import Any, Callable

from fle.envd.models import (
    DISRUPTION_GENERATOR_VERSION,
    DisruptionScheduleSpec,
    PerturbationSpec,
)

# Kinds whose blast radius directly suppresses factory throughput and are
# therefore eligible for recovery tracking.
_THROUGHPUT_KINDS = {"resource_depletion", "entity_destruction"}

# Preset entity_destruction scenarios: (label, filters, count range).
_DESTRUCTION_PRESETS = [
    ("power_loss", {"entity_types": ["boiler", "generator"]}, (1, 2)),
    ("belt_failure", {"entity_names": ["transport-belt"]}, (4, 8)),
    ("module_removed", {"entity_types": ["assembling-machine"]}, (1, 2)),
    ("furnace_out", {"entity_types": ["furnace"]}, (2, 4)),
    ("inserter_jam", {"entity_types": ["inserter"]}, (3, 6)),
    ("rail_severed", {"entity_names": ["train-stop"]}, (1, 1)),
]

_ENEMY_TIERS = ("small", "small", "medium", "medium", "big")


def _stable_seed(*parts: Any) -> int:
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "big")


@dataclass(frozen=True)
class DisruptionConfig:
    """Difficulty knobs for procedural disruption generation."""

    horizon_ticks: int
    difficulty: float = 0.5
    count: int = 3
    allow_enemy_waves: bool = True
    warmup_ticks: int = 72000


def generate_disruption_schedule(
    config: DisruptionConfig, seed: int
) -> DisruptionScheduleSpec:
    """Deterministically derive a hidden disruption stream."""

    rng = random.Random(_stable_seed(DISRUPTION_GENERATOR_VERSION, seed, config))
    difficulty = min(max(config.difficulty, 0.0), 1.0)

    span = max(config.horizon_ticks - config.warmup_ticks, 1)
    slot = span / max(config.count, 1)
    perturbations: list[PerturbationSpec] = []
    for index in range(config.count):
        trigger = int(
            config.warmup_ticks + slot * index + rng.uniform(0.15, 0.85) * slot
        )
        roll = rng.random()
        if config.allow_enemy_waves and roll < 0.15 + 0.15 * difficulty:
            tier_index = min(
                int(difficulty * (len(_ENEMY_TIERS) - 1)) + rng.randint(0, 1),
                len(_ENEMY_TIERS) - 1,
            )
            perturbations.append(
                PerturbationSpec(
                    perturbation_id=f"dis-{index:03d}-wave",
                    kind="enemy_wave",
                    trigger_tick=trigger,
                    parameters={
                        "count": int(5 + 20 * difficulty * rng.uniform(0.7, 1.3)),
                        "tier": _ENEMY_TIERS[tier_index],
                    },
                )
            )
        elif roll < 0.45 - 0.1 * difficulty:
            radius = int(rng.uniform(16, 32))
            perturbations.append(
                PerturbationSpec(
                    perturbation_id=f"dis-{index:03d}-deplete",
                    kind="resource_depletion",
                    trigger_tick=trigger,
                    parameters={"radius": radius},
                )
            )
        else:
            label, filters, (low, high) = rng.choice(_DESTRUCTION_PRESETS)
            count = rng.randint(low, high)
            perturbations.append(
                PerturbationSpec(
                    perturbation_id=f"dis-{index:03d}-{label}",
                    kind="entity_destruction",
                    trigger_tick=trigger,
                    parameters={
                        **filters,
                        "count": count,
                        "search_radius": 200,
                    },
                )
            )

    return DisruptionScheduleSpec(
        generator_version=DISRUPTION_GENERATOR_VERSION,
        perturbations=sorted(perturbations, key=lambda p: p.trigger_tick),
    )


# ---------------------------------------------------------------------------
# Runtime engine
# ---------------------------------------------------------------------------


@dataclass
class RateSample:
    tick: int
    totals: dict[str, float] = field(default_factory=dict)

    @property
    def cumulative_output(self) -> float:
        return sum(self.totals.values())


@dataclass
class RecoveryTracker:
    perturbation_id: str
    fired_tick: int
    tracked: dict[str, float]
    recovered_tick: int | None = None

    @property
    def recovery_ticks(self) -> int | None:
        if self.recovered_tick is None:
            return None
        return self.recovered_tick - self.fired_tick


# Products with nonzero pre-shock output that recovery is gated on when a
# shock's affected set cannot be derived (pure logistics damage).  Gating on
# individual major products prevents flooding cheap items from masking a
# dead production line.
_FALLBACK_TOP_PRODUCTS = 3


def product_interval_rates(
    samples: list[RateSample],
) -> list[tuple[int, dict[str, float]]]:
    """Per-interval output rates (items/tick) for every observed product."""

    per_product: list[tuple[int, dict[str, float]]] = []
    for previous, current in zip(samples, samples[1:]):
        ticks = current.tick - previous.tick
        if ticks <= 0:
            continue
        products = set(previous.totals) | set(current.totals)
        deltas = {
            product: (
                current.totals.get(product, 0.0)
                - previous.totals.get(product, 0.0)
            )
            / ticks
            for product in products
        }
        per_product.append((current.tick, deltas))
    return per_product


def interval_rates(samples: list[RateSample]) -> list[tuple[int, float]]:
    """Per-interval output rates (items per tick) between samples."""

    rates: list[tuple[int, float]] = []
    for previous, current in zip(samples, samples[1:]):
        ticks = current.tick - previous.tick
        if ticks <= 0:
            continue
        rates.append((current.tick, (current.cumulative_output - previous.cumulative_output) / ticks))
    return rates


class PerturbationEngine:
    """Authoritative in-worker state machine for one lease's disruptions."""

    def __init__(self, spec: DisruptionScheduleSpec):
        self.spec = spec
        self._pending: list[PerturbationSpec] = sorted(
            spec.perturbations, key=lambda p: p.trigger_tick
        )
        self._samples: list[RateSample] = []
        self._applied: list[dict[str, Any]] = []
        self._recoveries: list[RecoveryTracker] = []

    # -- production telemetry ----------------------------------------------

    def record_output(
        self, tick: int, cumulative_outputs: dict[str, float] | None = None
    ) -> None:
        if self._samples and tick <= self._samples[-1].tick:
            return
        self._samples.append(
            RateSample(tick=tick, totals=dict(cumulative_outputs or {}))
        )

    def _baseline_rate(self, before_tick: int) -> float:
        """Mean total-output rate over intervals fully before ``before_tick``."""

        rates = [
            rate
            for end_tick, rate in interval_rates(self._samples)
            if end_tick <= before_tick
        ]
        recent = rates[-3:]
        if not recent:
            return 0.0
        return sum(recent) / len(recent)

    def _baseline_product_rates(self, before_tick: int) -> dict[str, float]:
        """Per-product mean output rates over pre-shock intervals."""

        history: dict[str, list[float]] = {}
        for end_tick, deltas in product_interval_rates(self._samples):
            if end_tick > before_tick:
                continue
            for product, rate in deltas.items():
                history.setdefault(product, []).append(rate)
        return {
            product: sum(recent[-3:]) / len(recent[-3:])
            for product, recent in history.items()
            if recent
        }

    def _latest_post_rate(self, after_tick: int) -> float | None:
        """Rate of the most recent interval measured entirely post-shock."""

        rates = [
            (end_tick, rate)
            for end_tick, rate in interval_rates(self._samples)
            if end_tick > after_tick
        ]
        if not rates:
            return None
        return rates[-1][1]

    def _latest_post_product_rates(self, after_tick: int) -> dict[str, float] | None:
        latest: tuple[int, dict[str, float]] | None = None
        for end_tick, deltas in product_interval_rates(self._samples):
            if end_tick > after_tick:
                latest = (end_tick, deltas)
        return dict(latest[1]) if latest else None

    # -- firing -------------------------------------------------------------

    @staticmethod
    def _command_for(perturbation: PerturbationSpec) -> tuple[str, dict[str, Any]]:
        if perturbation.kind == "resource_depletion":
            params = {
                key: value
                for key, value in perturbation.parameters.items()
                if key in {"radius", "resources", "position"}
            }
            return "deplete_area", params
        if perturbation.kind == "entity_destruction":
            params = {
                key: value
                for key, value in perturbation.parameters.items()
                if key
                in {"count", "entity_types", "entity_names", "search_radius", "position"}
            }
            return "destroy_entities", params
        if perturbation.kind == "enemy_wave":
            params = {
                key: value
                for key, value in perturbation.parameters.items()
                if key in {"count", "tier", "position"}
            }
            return "spawn_enemies", params
        raise ValueError(f"Unsupported perturbation kind {perturbation.kind!r}")

    def sync(
        self,
        current_tick: int,
        stats: dict[str, Any] | None,
        fire: Callable[[PerturbationSpec], dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        """Advance the clock: sample rates, fire due shocks, track recovery."""

        events: list[dict[str, Any]] = []
        if stats is not None:
            output = {
                str(name): float(value)
                for name, value in (stats.get("output") or {}).items()
            }
            self.record_output(current_tick, output)

        while self._pending and self._pending[0].trigger_tick <= current_tick:
            perturbation = self._pending.pop(0)
            throughput_kind = perturbation.kind in _THROUGHPUT_KINDS
            baselines = (
                self._baseline_product_rates(perturbation.trigger_tick)
                if throughput_kind
                else {}
            )
            total_baseline = (
                self._baseline_rate(perturbation.trigger_tick)
                if throughput_kind
                else None
            )
            result: dict[str, Any]
            status = "applied"
            if fire is None:
                result = {}
                status = "failed"
            else:
                try:
                    command, params = self._command_for(perturbation)
                    result = fire(command, params) or {}
                    if isinstance(result, dict) and result.get("error"):
                        status = "failed"
                    else:
                        # Application requires an observable effect; a shock
                        # that destroyed nothing is recorded as a no-op so a
                        # schedule cannot bank credit for missing targets.
                        effect = max(
                            float(result.get("total") or 0),
                            float(result.get("spawned") or 0),
                        )
                        if effect <= 0:
                            status = "no_op"
                except Exception as exc:  # noqa: BLE001 - degrade to failed state
                    result = {"error": str(exc)}
                    status = "failed"
            applied_tick = max(current_tick, perturbation.trigger_tick)

            tracked: dict[str, float] = {}
            if status == "applied" and throughput_kind:
                affected = set(result.get("affected_products") or [])
                for product, rate in baselines.items():
                    if product in affected and rate > 1e-9:
                        tracked[product] = rate
                if not tracked:
                    # No recipe-derived network available (pure logistics
                    # damage): gate on the largest pre-shock products so
                    # cheap-item flooding cannot fake restoration.
                    top = sorted(
                        baselines.items(), key=lambda kv: -kv[1]
                    )[:_FALLBACK_TOP_PRODUCTS]
                    tracked = {
                        product: rate
                        for product, rate in top
                        if rate > 1e-9
                    }

            record = {
                "event": "perturbation_applied",
                "perturbation_id": perturbation.perturbation_id,
                "kind": perturbation.kind,
                "trigger_tick": perturbation.trigger_tick,
                "applied_tick": applied_tick,
                "status": status,
                "result": result,
                "baseline_rate": total_baseline,
                "tracked_products": dict(tracked),
            }
            self._applied.append(record)
            events.append(record)
            if status == "applied" and tracked:
                self._recoveries.append(
                    RecoveryTracker(
                        perturbation_id=perturbation.perturbation_id,
                        fired_tick=applied_tick,
                        tracked=dict(tracked),
                    )
                )

        for tracker in self._recoveries:
            if tracker.recovered_tick is not None:
                continue
            latest = self._latest_post_product_rates(tracker.fired_tick)
            if latest is None:
                continue
            elapsed = current_tick - tracker.fired_tick
            threshold = self.spec.recovery_rate_threshold
            details = {
                product: {
                    "baseline_rate": baseline,
                    "recovered_rate": latest.get(product, 0.0),
                    "restored": (
                        latest.get(product, 0.0) >= threshold * baseline
                    ),
                }
                for product, baseline in sorted(tracker.tracked.items())
            }
            all_restored = all(
                detail["restored"] for detail in details.values()
            )
            if elapsed >= self.spec.recovery_min_ticks and all_restored:
                tracker.recovered_tick = current_tick
                events.append(
                    {
                        "event": "recovery_completed",
                        "perturbation_id": tracker.perturbation_id,
                        "recovered_tick": current_tick,
                        "recovery_ticks": tracker.recovery_ticks,
                        "tracked_products": dict(tracker.tracked),
                        "product_details": details,
                    }
                )
        return events

    # -- reporting ----------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        recoveries = [
            {
                "perturbation_id": tracker.perturbation_id,
                "fired_tick": tracker.fired_tick,
                "recovered_tick": tracker.recovered_tick,
                "recovery_ticks": tracker.recovery_ticks,
                "tracked_products": dict(tracker.tracked),
            }
            for tracker in self._recoveries
        ]
        return {
            "commitment": self.spec.commitment,
            "scheduled": len(self.spec.perturbations),
            "applied": sum(
                1 for record in self._applied if record["status"] == "applied"
            ),
            "no_op": sum(
                1 for record in self._applied if record["status"] == "no_op"
            ),
            "failed": sum(
                1 for record in self._applied if record["status"] == "failed"
            ),
            "pending": len(self._pending),
            "recoveries": recoveries,
            "mean_recovery_ticks": (
                sum(r["recovery_ticks"] for r in recoveries if r["recovery_ticks"])
                / max(sum(1 for r in recoveries if r["recovery_ticks"]), 1)
                if any(r["recovery_ticks"] for r in recoveries)
                else None
            ),
        }

    @property
    def applied_records(self) -> list[dict[str, Any]]:
        return list(self._applied)


__all__ = [
    "DisruptionConfig",
    "generate_disruption_schedule",
    "PerturbationEngine",
    "RecoveryTracker",
    "RateSample",
    "interval_rates",
    "product_interval_rates",
]
