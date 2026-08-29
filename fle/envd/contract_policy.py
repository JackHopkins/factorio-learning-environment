"""Deterministic customer policy for adaptive evaluation.

This module deliberately borrows *signals* from PLR and ACCEL without
importing their training replay machinery.  The customer chooses among
auditable intents using the current factory snapshot and its evidence ledger.
A plan is resized before it is scored; otherwise the selector can score an
easy candidate and commit a materially harder one.

The policy keeps three kinds of factory evidence separate:

* positive depot delivery (the customer actually received something),
* observed production (the passive snapshot reports a positive rate), and
* sustained depot evidence (positive delivery across a sustained window).

An attempted order by itself is never evidence of capacity.  This distinction
is important for zero-delivery failures: they may create useful capability
progress and therefore deserve replay, but they must not inflate a later
throughput order.
"""

from __future__ import annotations

import math
import random
import statistics
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterable

from fle.envd.contract_features import TICKS_PER_MINUTE, ProductCatalog
from fle.envd.contract_generator import (
    STAGE_REFERENCE_RATES,
    ContractCandidate,
    DifficultyModel,
    _evaluate_difficulty,
    _features_for,
    analytic_feasibility,
    round_to_batch,
)
from fle.envd.models import (
    CapabilityRating,
    ContractContextSnapshot,
    ContractEpochOutcome,
    ContractEpochSpec,
    ProductDemandSpec,
)


# ``LANE_*`` remains exported for old audit readers.  It is no longer the
# decision authority: intent utilities below are recomputed from state and
# evidence for every selection.
POLICY_VERSION = "evidence-driven-customer-v5"

LANE_SCHEDULE: tuple[str, ...] = (
    "anchor",
    "anchor",
    "frontier",
    "anchor",
    "replay",
    "anchor",
    "frontier",
    "replay",
    "anchor",
    "anchor",
    "frontier",
    "replay",
    "anchor",
    "anchor",
    "replay",
    "anchor",
    "anchor",
    "replay",
    "accel",
    "replay",
)
LANE_WEIGHTS: dict[str, float] = {
    "anchor": 0.50,
    "replay": 0.30,
    "frontier": 0.15,
    "accel": 0.05,
}

INTENTS: tuple[str, ...] = (
    "expand",
    "deepen",
    "compose",
    "recover",
    "retain",
    "stress",
)
INTENT_TO_LANE: dict[str, str] = {
    "expand": "frontier",
    "deepen": "anchor",
    "compose": "anchor",
    "recover": "replay",
    "retain": "anchor",
    "stress": "accel",
}
STALE_CAPABILITY_EPOCHS = 2

# These are evaluator-side bounds, not a substitute for generator feasibility
# rejection.  In particular, a missing-research estimate must never create a
# multi-day order deadline merely because an optimistic analytic term grew.
MIN_COMMISSIONING_DEADLINE_TICKS = 15 * TICKS_PER_MINUTE
MAX_COMMISSIONING_DEADLINE_TICKS = 4 * 60 * TICKS_PER_MINUTE
MIN_SERVICE_DEADLINE_TICKS = 10 * TICKS_PER_MINUTE
MAX_SERVICE_DEADLINE_TICKS = 4 * 60 * TICKS_PER_MINUTE
# A commissioning probe creates pressure to automate without treating a
# hand-delivered burst as a throughput estimate.
COMMISSIONING_PROBE_WINDOW_MINUTES = 45.0
COMMISSIONING_PROBE_RATE_FRACTION = 0.10
FRONTIER_MAX_BAND_STEP = 1
EPSILON = 1e-9
SUSTAINED_CERTIFICATION_SCORE = 0.60


@dataclass
class ProductEvidence:
    """Per-product evidence ledger.

    ``attempts`` remains for audit only.  Capacity properties below require
    positive delivery or a positive measured production rate, so creating an
    order cannot bootstrap a false throughput baseline.
    """

    product: str
    attempts: int = 0
    fulfilled: int = 0
    last_epoch: int = 0
    completion_scores: list[float] = field(default_factory=list)
    delivered_rates: list[float] = field(default_factory=list)
    measured_rates: list[float] = field(default_factory=list)
    measured_depot_rates: list[float] = field(default_factory=list)
    sustained_window_scores: list[float] = field(default_factory=list)
    sustained_window_rates: list[float] = field(default_factory=list)
    positive_delivery_count: int = 0
    observed_production_count: int = 0
    sustained_depot_count: int = 0
    zero_delivery_count: int = 0
    capability_progress_count: int = 0
    failure_streak: int = 0
    last_status: str | None = None
    last_quantity: float = 0.0
    last_deadline_ticks: int = 0
    # Stored at the end to preserve positional compatibility with v3 records.
    last_capability_progress_epoch: int = 0
    commissioning_probe_count: int = 0
    last_commissioning_probe_epoch: int = 0
    commissioning_probe_failure_count: int = 0
    last_non_probe_success_epoch: int = 0

    @property
    def completion_mean(self) -> float:
        return statistics.fmean(self.completion_scores) if self.completion_scores else 0.0

    @property
    def positive_delivery(self) -> bool:
        """Whether a customer-visible positive delivery was observed."""

        # ``delivered_rates`` was the original public field.  Treat a manually
        # constructed legacy record containing it as positive delivery while
        # still refusing records that contain only ``attempts``.
        return self.positive_delivery_count > 0 or any(rate > 0 for rate in self.delivered_rates)

    @property
    def observed_production(self) -> bool:
        return self.observed_production_count > 0 or any(rate > 0 for rate in self.measured_rates)

    @property
    def automated_capacity_evidence(self) -> bool:
        """Whether provenance-safe production or sustained depot evidence exists."""

        return self.observed_production or self.sustained_evidence

    @property
    def capacity_evidence(self) -> bool:
        """Positive depot delivery or passive production evidence."""

        return self.positive_delivery or self.observed_production

    @property
    def sustained_evidence(self) -> bool:
        return self.sustained_depot_count > 0

    @property
    def sustained_reliable(self) -> bool:
        """Whether service evidence is strong enough for stress selection."""

        return bool(
            self.sustained_window_scores
            and statistics.fmean(self.sustained_window_scores) >= 0.80
            and any(rate > EPSILON for rate in self.sustained_window_rates)
        )

    @property
    def empirical_depot_rates(self) -> list[float]:
        """Windowed customer-sink rates, including zero-service windows."""

        return [
            max(float(rate), 0.0)
            for rate in self.sustained_window_rates
        ]

    @property
    def empirical_rates(self) -> list[float]:
        rates = self.delivered_rates + self.measured_rates + self.sustained_window_rates
        return [float(rate) for rate in rates if float(rate) > 0]

    @property
    def rate_center(self) -> float:
        rates = self.empirical_rates
        return statistics.median(rates) if rates else 0.0

    @property
    def rate_spread(self) -> float:
        rates = self.empirical_rates
        if len(rates) < 2:
            return self.rate_center / math.sqrt(max(self.attempts + 1, 1))
        return statistics.pstdev(rates)


@dataclass(frozen=True)
class AdaptiveOrderPlan:
    candidate: ContractCandidate
    order_kind: str
    products: tuple[ProductDemandSpec, ...]
    mode: str
    evidence: dict[str, Any]


@dataclass(frozen=True)
class _PlanEvaluation:
    plan: AdaptiveOrderPlan
    score: float
    lane: str
    reason: str
    intent: str = "deepen"
    utility_components: dict[str, float] = field(default_factory=dict)


class EvidenceDrivenCustomerPolicy:
    """Joint breadth, pressure, and recovery policy over one factory."""

    def __init__(self, *, recent_window: int = 4) -> None:
        self.records: dict[str, ProductEvidence] = {}
        self.recent_products: deque[str] = deque(maxlen=recent_window)
        self.completed_epochs = 0
        self.frontier_failure_streak = 0
        self.frontier_success_count = 0
        self._last_lane: str | None = None
        self._last_product: str | None = None
        self._last_epoch_outcome: str | None = None
        # A structural retry is an immediate follow-up, not a permanent lane.
        # Remembering the consumed epoch prevents a failed target from
        # capturing every subsequent order when no other evidence changes.
        self._recovery_consumed_epochs: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Evidence ingestion
    # ------------------------------------------------------------------

    def observe(
        self,
        spec: ContractEpochSpec,
        outcome: ContractEpochOutcome,
        post_context: ContractContextSnapshot | None,
    ) -> None:
        """Record valid outcome evidence without rating infrastructure noise."""

        if outcome.status in {"infrastructure_error", "invalid"}:
            return

        elapsed_minutes = max(float(outcome.simulation_ticks_used) / TICKS_PER_MINUTE, 1e-6)
        lines = spec.products or (
            ProductDemandSpec(product=spec.item_name, quantity=float(spec.quantity)),
        )
        delivered_map = dict(outcome.delivered_by_product or {})
        if not delivered_map:
            delivered_map[spec.item_name] = float(outcome.delivered_quantity)

        delta = outcome.capability_delta
        # ``meaningful_progress`` is a persisted summary and older producers
        # could set it from a rate change.  Only structural movement on the
        # committed path can authorize recovery or frontier continuation.
        target_path = (
            set((delta.evidence or {}).get("target_path", ())) if delta else set()
        )
        target_technologies = {
            node.removeprefix("technology:")
            for node in target_path
            if node.startswith("technology:")
        }
        target_products = {
            node.removeprefix("product:")
            for node in target_path
            if node.startswith("product:")
        }
        progress = bool(
            delta is not None
            and (
                delta.path_progress > 0
                or bool(
                    set(delta.evidence.get("structural_path_delta", ())) & target_path
                )
                or bool(set(delta.new_technologies) & target_technologies)
                or bool(set(delta.new_recipes) & target_products)
            )
        )
        sustained_windows = self._window_evidence(outcome)
        for line in lines:
            record = self.records.setdefault(line.product, ProductEvidence(line.product))
            delivered_value = delivered_map.get(line.product, 0.0)
            if line.product not in delivered_map and len(lines) == 1:
                # Preserve compatibility with pre-v2 outcomes that only
                # populated the scalar delivery field.
                delivered_value = outcome.delivered_quantity
            delivered = min(
                max(float(delivered_value), 0.0),
                float(line.quantity),
            )
            line_windows = sustained_windows.get(line.product, ())
            score = (
                statistics.fmean(window_score for window_score, _ in line_windows)
                if spec.order_kind == "sustained" and line_windows
                else min(delivered / max(float(line.quantity), EPSILON), 1.0)
            )
            record.attempts += 1
            record.fulfilled += int(score >= 1.0 - EPSILON)
            record.last_epoch = spec.epoch_index
            record.last_status = outcome.status
            record.last_quantity = float(line.quantity)
            record.last_deadline_ticks = int(spec.deadline_ticks)
            record.completion_scores.append(score)

            positive = delivered > EPSILON
            if positive:
                record.positive_delivery_count += 1
                record.delivered_rates.append(delivered / elapsed_minutes)
            else:
                record.zero_delivery_count += 1

            measured = (
                self._context_production_rate(post_context, line.product)
                if post_context is not None
                else 0.0
            )
            # A passing intervention-free audit is provenance-safe even when
            # the public post-context has no rate yet (for example, a probe
            # that was completed in the cloned holdout). Manual probe service
            # never reaches this path because it is neither authoritative nor
            # audit-backed.
            authoritative = outcome.autonomous_throughput
            if (
                authoritative is not None
                and authoritative.authoritative
                and authoritative.interventions_during_window == 0
                and authoritative.performance_score >= SUSTAINED_CERTIFICATION_SCORE
            ):
                measured = max(
                    measured,
                    float(
                        (authoritative.observed_rate_per_minute or {}).get(
                            line.product, 0.0
                        )
                    ),
                )
            audit = outcome.throughput_audit
            if audit is not None and audit.passed:
                measured = max(
                    measured,
                    float(
                        (audit.production_rates_per_minute or {}).get(
                            line.product, 0.0
                        )
                    ),
                )
            if measured > EPSILON:
                record.observed_production_count += 1
                record.measured_rates.append(measured)

            if post_context is not None:
                depot_rate = self._context_delivery_rate(post_context, line.product)
                if depot_rate > EPSILON:
                    record.measured_depot_rates.append(depot_rate)

            is_commissioning_probe = bool(
                spec.order_kind == "sustained"
                and (spec.policy_evidence or {}).get("commissioning_probe")
            )
            if spec.order_kind == "sustained":
                if is_commissioning_probe:
                    # Keep probe delivery as ordinary positive evidence, but
                    # do not let manual service create sustained-capacity evidence.
                    record.commissioning_probe_count += 1
                    record.last_commissioning_probe_epoch = spec.epoch_index
                    if outcome.status != "fulfilled" or score < 1.0 - EPSILON:
                        record.commissioning_probe_failure_count += 1
                else:
                    for window_score, window_rate in line_windows:
                        record.sustained_window_scores.append(window_score)
                        # Zero windows are part of the throughput distribution;
                        # dropping them would inflate the next target rate.
                        record.sustained_window_rates.append(max(window_rate, 0.0))
                    # Only per-window evidence establishes sustained service.
                    # Aggregate delivery remains positive-delivery evidence but
                    # cannot by itself authorize a throughput target.
                    if (
                        line_windows
                        and score >= SUSTAINED_CERTIFICATION_SCORE
                        and any(rate > EPSILON for _, rate in line_windows)
                    ):
                        record.sustained_depot_count += 1

            # A capability delta names the primary target.  Do not credit a
            # secondary mixed-order line for progress it did not unlock.
            line_progress = progress and (
                len(lines) == 1 or (delta is not None and line.product == delta.target_id)
            )
            if line_progress:
                record.capability_progress_count += 1
                record.last_capability_progress_epoch = spec.epoch_index

            if outcome.status != "fulfilled" or score < 1.0 - EPSILON:
                record.failure_streak += 1
            else:
                record.failure_streak = 0
                if not is_commissioning_probe and positive:
                    record.last_non_probe_success_epoch = spec.epoch_index
            self.recent_products.append(line.product)

        selected_intent = (spec.policy_evidence or {}).get("intent")
        if selected_intent == "expand" or spec.mixture_class == "frontier":
            if outcome.status == "fulfilled":
                self.frontier_failure_streak = 0
                self.frontier_success_count += 1
            else:
                self.frontier_failure_streak += 1
        self.completed_epochs = max(self.completed_epochs, spec.epoch_index)
        self._last_product = spec.item_name
        self._last_epoch_outcome = outcome.status

    @staticmethod
    def _window_evidence(
        outcome: ContractEpochOutcome,
    ) -> dict[str, tuple[tuple[float, float], ...]]:
        """Normalize optional backend window telemetry without a hard schema tie."""

        raw = None
        for name in (
            "delivery_windows",
            "sustained_delivery_windows",
            "depot_delivery_windows",
            "delivery_window_evidence",
            "delivery_telemetry",
        ):
            value = getattr(outcome, name, None)
            if value:
                raw = value
                break
        if not raw:
            return {}
        if hasattr(raw, "model_dump"):
            raw = raw.model_dump(mode="json")

        # The backend persists physical telemetry and the order's authoritative
        # window scores together.  Only the order section can establish
        # sustained depot evidence; physical buckets remain useful context but
        # do not prove that this order was serviced steadily.
        window_ticks = 0
        if isinstance(raw, dict) and ("order" in raw or "physical" in raw):
            order = raw.get("order")
            if isinstance(order, dict):
                try:
                    window_ticks = int(order.get("window_ticks") or 0)
                except (TypeError, ValueError):
                    window_ticks = 0
                raw = order
            else:
                raw = {}
        if isinstance(raw, dict) and "lines" in raw:
            try:
                window_ticks = int(raw.get("window_ticks") or window_ticks or 0)
            except (TypeError, ValueError):
                pass
            raw = raw.get("lines") or {}

        normalized: dict[str, list[tuple[float, float]]] = {}
        if isinstance(raw, dict):
            entries: Iterable[tuple[str, Any]] = raw.items()
        else:
            entries = (("", raw),)
        for product, values in entries:
            # A list-form payload may carry its product key in each item.
            # Keep it auditable instead of placing all lines under "".
            if isinstance(values, dict):
                line_product = values.get("product")
                if line_product:
                    product = str(line_product)
                if "slice_scores" in values:
                    scores = values.get("slice_scores") or ()
                    try:
                        requested = max(float(values.get("requested") or 0.0), 0.0)
                    except (TypeError, ValueError):
                        requested = 0.0
                    window_minutes = window_ticks / TICKS_PER_MINUTE
                    try:
                        accepted = max(float(values.get("accepted") or 0.0), 0.0)
                    except (TypeError, ValueError):
                        accepted = 0.0
                    sustained_score = values.get("sustained_service_score", 0.0)
                    aggregate_rate = (
                        accepted / window_minutes
                        if window_minutes > 0
                        else 0.0
                    )
                    converted = [
                        {
                            "score": score,
                            # ``slice_scores`` are normalized fractions. When
                            # no explicit per-slice rate exists, derive one
                            # from the requested quantity and order window.
                            "rate_per_minute": (
                                float(score) * requested / window_minutes
                                if window_minutes > 0
                                else aggregate_rate
                            ),
                        }
                        for score in scores
                    ]
                    if not converted and accepted > EPSILON:
                        converted = [
                            {
                                "score": sustained_score,
                                "rate_per_minute": aggregate_rate,
                            }
                        ]
                    values = converted
                elif "sustained_service_score" in values:
                    try:
                        accepted = max(float(values.get("accepted") or 0.0), 0.0)
                    except (TypeError, ValueError):
                        accepted = 0.0
                    aggregate_rate = (
                        accepted / (window_ticks / TICKS_PER_MINUTE)
                        if window_ticks > 0
                        else 0.0
                    )
                    values = [
                        {
                            "score": values.get("sustained_service_score", 0.0),
                            "rate_per_minute": aggregate_rate,
                        }
                    ]
                else:
                    values = values.get(
                        "windows",
                        values.get("evidence", values.get("samples", ())),
                    )
            if not isinstance(values, (list, tuple)):
                continue
            for value in values:
                value_product = (
                    value.get("product")
                    if isinstance(value, dict)
                    else None
                )
                normalized_product = str(value_product or product)
                score = rate = 0.0
                if isinstance(value, dict):
                    score = value.get("completion_ratio", value.get("score", 0.0))
                    rate = value.get(
                        "depot_rate_per_minute",
                        value.get("rate_per_minute", value.get("rate", 0.0)),
                    )
                elif isinstance(value, (list, tuple)) and value:
                    score = value[0]
                    rate = value[1] if len(value) > 1 else 0.0
                else:
                    score = value
                try:
                    normalized.setdefault(normalized_product, []).append(
                        (min(max(float(score), 0.0), 1.0), max(float(rate), 0.0))
                    )
                except (TypeError, ValueError):
                    continue
        return {key: tuple(values) for key, values in normalized.items()}

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def choose(
        self,
        pool: list[ContractCandidate],
        *,
        context: ContractContextSnapshot,
        catalog: ProductCatalog,
        difficulty_model: DifficultyModel,
        selection_seed: int,
        rating: CapabilityRating | None = None,
    ) -> AdaptiveOrderPlan:
        """Build and select a complete plan from evidence-driven intents.

        The candidate pool is still generated by the versioned contract
        generator.  This method decides *why* to issue an order, scoring every
        eligible intent against the same frozen context.  ``selection_seed``
        only breaks otherwise equivalent choices, making the policy replayable
        without introducing an epoch schedule.
        """

        rng = random.Random(selection_seed)
        candidates = self._representatives(pool)
        if not candidates:
            raise ValueError("evidence policy received no accepted candidates")
        current_rating = rating or CapabilityRating(
            mu=0.0,
            sigma=2.0,
            conservative_score=-6.0,
            rated_epoch_count=0,
        )

        recovery = self._recovery_candidates(candidates)
        proposals: list[
            tuple[str, list[ContractCandidate], str, str, dict[str, float], str]
        ] = []
        intent_utilities: dict[str, float] = {}
        for intent in INTENTS:
            if intent == "compose":
                for primary in self._candidates_for_intent(
                    candidates, intent=intent, context=context, recovery=recovery
                ):
                    secondary = self._secondary_candidate_for_compose(
                        primary, candidates=candidates, context=context
                    )
                    if secondary is None:
                        continue
                    chosen = [primary, secondary]
                    score, components = self._intent_utility(
                        chosen,
                        intent=intent,
                        context=context,
                        rating=current_rating,
                    )
                    score += rng.random() * 0.05
                    components["seed_jitter"] = round(
                        score - sum(components.values()), 6
                    )
                    reason = "mixed_probe_uncertainty" if any(
                        not self._has_evidence(c, context) for c in chosen
                    ) else "mixed_probe_composition"
                    proposals.append(
                        (
                            intent,
                            chosen,
                            "throughput"
                            if all(
                                self._has_automated_capacity(c, context)
                                for c in chosen
                            )
                            else "consolidation",
                            reason,
                            components,
                            "anchor",
                        )
                    )
                    intent_utilities[intent] = max(intent_utilities.get(intent, -math.inf), score)
                continue

            eligible = self._candidates_for_intent(
                candidates, intent=intent, context=context, recovery=recovery
            )
            for primary in eligible:
                score, components = self._intent_utility(
                    [primary],
                    intent=intent,
                    context=context,
                    rating=current_rating,
                )
                score += rng.random() * 0.05
                components["seed_jitter"] = round(
                    score - sum(components.values()), 6
                )
                reason = self._intent_reason(intent, primary, context)
                mode = self._mode_for_intent(
                    primary, intent=intent, context=context, rng=rng
                )
                lane = INTENT_TO_LANE[intent]
                if intent == "expand" and primary.mixture_class != "frontier":
                    # A breadth bootstrap is an expansion intent but remains
                    # an anchor in the legacy lane field.
                    lane = "anchor"
                proposals.append((intent, [primary], mode, reason, components, lane))
                intent_utilities[intent] = max(
                    intent_utilities.get(intent, -math.inf), score
                )

        if not proposals:
            raise ValueError("no in-envelope candidate for any customer intent")

        evaluations: list[_PlanEvaluation] = []
        for intent, chosen, mode, reason, components, lane in proposals:
            plan = self._build_plan(
                chosen,
                mode=mode,
                context=context,
                catalog=catalog,
                difficulty_model=difficulty_model,
                rating=current_rating,
                rng=rng,
                lane=lane,
                reason=reason,
                selection_seed=selection_seed,
                intent=intent,
                utility_components=components,
            )
            score = sum(components.values())
            # A final deterministic difficulty tie-break is kept separate from
            # utility, so the audit record remains a faithful decomposition.
            evaluations.append(
                _PlanEvaluation(
                    plan=plan,
                    score=score,
                    lane=lane,
                    reason=reason,
                    intent=intent,
                    utility_components=dict(components),
                )
            )

        selected = max(
            evaluations,
            key=lambda item: (
                item.score,
                -float(item.plan.candidate.effective_difficulty or 0.0),
                item.plan.candidate.item_name,
            ),
        )
        selected.plan.evidence["intent_utilities"] = {
            key: round(value, 6) for key, value in sorted(intent_utilities.items())
        }
        selected.plan.evidence["selected_utility"] = round(selected.score, 6)
        selected.plan.evidence["selected_intent"] = selected.intent
        if selected.intent == "recover":
            self._recovery_consumed_epochs[selected.plan.candidate.item_name] = self.completed_epochs
        self._last_lane = selected.lane
        return selected.plan

    def _candidates_for_intent(
        self,
        candidates: list[ContractCandidate],
        *,
        intent: str,
        context: ContractContextSnapshot,
        recovery: list[ContractCandidate],
    ) -> list[ContractCandidate]:
        """Return candidates eligible for one intent.

        Eligibility is deliberately conservative about graph distance but does
        not require prior success.  In particular, composition can probe two
        unknown local products together; their uncertainty is charged in the
        utility rather than silently filtering the experiment out.
        """

        current_band = self._current_band(context)

        def local(candidate: ContractCandidate) -> bool:
            features = candidate.features
            if features is None:
                return False
            if candidate.mixture_class == "frontier":
                return self._frontier_step_allowed(candidate, current_band)
            return int(features.stage_band) <= current_band

        if intent == "recover":
            return list(recovery)
        if intent == "expand":
            result = []
            for candidate in candidates:
                if not local(candidate) or candidate.mixture_class == "stress":
                    continue
                if (
                    candidate.mixture_class == "frontier"
                    and self.frontier_failure_streak >= 2
                ):
                    # A frontier that has failed repeatedly must either wait
                    # for a new structural state or be explicitly recovered;
                    # it cannot monopolize the expansion intent.
                    continue
                record = self.records.get(candidate.item_name)
                # Unseen same-band lines establish breadth.  Frontier lines
                # remain eligible after evidence so the frontier can continue
                # moving, subject to the one-edge graph guard.
                if candidate.mixture_class == "frontier" or not (
                    record and record.capacity_evidence
                ):
                    result.append(candidate)
            return self._rotate_recent(result)
        if intent == "deepen":
            eligible = [
                candidate
                for candidate in candidates
                if local(candidate)
                and candidate.mixture_class != "stress"
                and self._has_evidence(candidate, context)
            ]
            uncertified = [
                candidate
                for candidate in eligible
                if not (
                    self.records.get(candidate.item_name)
                    and self.records[candidate.item_name].sustained_reliable
                )
            ]
            return self._rotate_recent(uncertified or eligible)
        if intent == "compose":
            return [candidate for candidate in candidates if local(candidate)]
        if intent == "retain":
            return self._rotate_recent(
                [
                    candidate
                    for candidate in candidates
                    if local(candidate)
                    and self._is_stale(candidate.item_name)
                    and self._has_evidence(candidate, context)
                ]
            )
        if intent == "stress":
            return self._rotate_recent(
                [
                    candidate
                    for candidate in candidates
                    if local(candidate)
                    and candidate.mixture_class == "stress"
                    and self._has_evidence(candidate, context, require_sustained=True)
                ]
            )
        raise ValueError(f"unknown customer intent: {intent}")

    def _is_stale(self, product: str) -> bool:
        record = self.records.get(product)
        return bool(
            record is not None
            and record.attempts > 0
            and self.completed_epochs - record.last_epoch >= STALE_CAPABILITY_EPOCHS
        )

    def _intent_reason(
        self,
        intent: str,
        candidate: ContractCandidate,
        context: ContractContextSnapshot,
    ) -> str:
        if intent == "expand":
            record = self.records.get(candidate.item_name)
            if record is None or not record.capacity_evidence:
                return (
                    "frontier_guard_fallback_establish_breadth"
                    if candidate.mixture_class != "frontier"
                    else "establish_breadth"
                )
            return (
                "frontier_guard_fallback_nearby_expansion"
                if candidate.mixture_class != "frontier"
                else "nearby_frontier_expansion"
            )
        return {
            "deepen": "qualify_sustainable_throughput",
            # Preserve the historical audit token while ``intent`` identifies
            # the new state-driven decision explicitly.
            "recover": "capability_progress_replay",
            "retain": "stale_capability_revalidation",
            "stress": "stress_certified_capacity",
        }.get(intent, "evidence_driven_selection")

    def _intent_utility(
        self,
        chosen: list[ContractCandidate],
        *,
        intent: str,
        context: ContractContextSnapshot,
        rating: CapabilityRating | None,
    ) -> tuple[float, dict[str, float]]:
        """Score an intent and expose every term in the audit record."""

        rating = rating or CapabilityRating(
            mu=0.0,
            sigma=2.0,
            conservative_score=-6.0,
            rated_epoch_count=0,
        )

        terms: list[dict[str, float]] = []
        for candidate in chosen:
            record = self.records.get(candidate.item_name)
            attempts = record.attempts if record else 0
            uncertainty = 1.0 / math.sqrt(attempts + 1)
            capacity = float(self._has_evidence(candidate, context))
            certified = float(bool(record and record.sustained_reliable))
            breadth = float(not capacity)
            age = (
                min(max(self.completed_epochs - record.last_epoch, 0) / 4.0, 1.0)
                if record
                else 0.0
            )
            structural = min(
                float(record.capability_progress_count if record else 0) / 2.0,
                1.0,
            )
            difficulty = float(candidate.effective_difficulty or 0.0)
            distance = abs(difficulty - rating.mu) / max(float(rating.sigma), 0.5)
            nearness = math.exp(-distance)
            local_difficulty = min(max(difficulty / 10.0, 0.0), 1.0)
            recent = min(
                sum(candidate.item_name == product for product in self.recent_products),
                2,
            ) / 2.0
            rate = min(self._live_rate(context, candidate.item_name) / 60.0, 1.0)
            terms.append(
                {
                    "uncertainty": uncertainty,
                    "capacity": capacity,
                    "certified": certified,
                    "breadth": breadth,
                    "staleness": age,
                    "structural_progress": structural,
                    "rating_nearness": nearness,
                    "difficulty_pressure": local_difficulty,
                    "recent_penalty": recent,
                    "live_capacity": rate,
                }
            )

        mean = lambda key: statistics.fmean(term[key] for term in terms)
        components: dict[str, float]
        if intent == "expand":
            # Breadth receives a slight preference over a speculative frontier
            # so the first orders establish a measurable baseline, after which
            # a nearby frontier naturally wins as breadth becomes certified.
            frontier = float(chosen[0].mixture_class == "frontier")
            frontier_readiness = mean("capacity")
            components = {
                "base": 1.0,
                "uncertainty_value": 1.25 * mean("uncertainty"),
                "breadth_value": 1.35 * mean("breadth"),
                # A cold frontier probe waits until basic breadth has been
                # sampled, while certified capacity earns a positive push.
                "frontier_value": frontier
                * (
                    0.35 * frontier_readiness
                    - 0.20 * (1.0 - frontier_readiness)
                ),
                "rating_value": 0.35 * mean("rating_nearness"),
                "difficulty_cost": -0.35 * mean("difficulty_pressure"),
                "recent_cost": -0.65 * mean("recent_penalty"),
            }
        elif intent == "deepen":
            components = {
                "base": 0.85,
                "capacity_value": 0.75 * mean("capacity"),
                "certification_gap_value": 1.15 * (1.0 - mean("certified")),
                "uncertainty_value": 0.30 * mean("uncertainty"),
                "rating_value": 0.45 * mean("rating_nearness"),
                "staleness_cost": -0.55 * mean("staleness"),
                "recent_cost": -0.70 * mean("recent_penalty"),
            }
        elif intent == "compose":
            frontier_pair = float(
                any(candidate.mixture_class == "frontier" for candidate in chosen)
            )
            components = {
                "base": 1.35,
                "joint_probe_value": 0.75,
                "uncertainty_value": 0.95 * mean("uncertainty"),
                "breadth_value": 0.15 * mean("breadth"),
                "capacity_value": 0.90 * mean("capacity"),
                "rating_value": 0.35 * mean("rating_nearness"),
                "difficulty_cost": -0.40 * mean("difficulty_pressure"),
                "recent_cost": -0.70 * mean("recent_penalty"),
                "frontier_pair_cost": -0.40 * frontier_pair * mean("breadth"),
            }
        elif intent == "recover":
            components = {
                "base": 2.70,
                "structural_value": 1.10 * mean("structural_progress"),
                "failure_value": 0.65,
                "uncertainty_value": 0.45 * mean("uncertainty"),
                "rating_value": 0.30 * mean("rating_nearness"),
            }
        elif intent == "retain":
            components = {
                "base": 0.65,
                "staleness_value": 1.60 * mean("staleness"),
                "certification_value": 0.85 * mean("certified"),
                "capacity_value": 0.35 * mean("capacity"),
                "uncertainty_value": 0.25 * mean("uncertainty"),
                "recent_cost": -0.60 * mean("recent_penalty"),
            }
        elif intent == "stress":
            components = {
                "base": 0.70,
                "certification_value": 1.05 * mean("certified"),
                "capacity_value": 0.80 * mean("live_capacity"),
                "rating_value": 0.40 * mean("rating_nearness"),
                "staleness_value": 0.20 * mean("staleness"),
                "recent_cost": -0.65 * mean("recent_penalty"),
            }
        else:
            raise ValueError(f"unknown customer intent: {intent}")
        return sum(components.values()), components

    def _mode_for_intent(
        self,
        candidate: ContractCandidate,
        *,
        intent: str,
        context: ContractContextSnapshot,
        rng: random.Random,
    ) -> str:
        if intent == "recover":
            return "replay_backoff"
        if intent == "expand":
            return "commissioning"
        if intent == "stress":
            return "accel_stress"
        if intent == "deepen":
            # A one-shot delivery proves only that some items reached the
            # customer. Escalate to sustained service after provenance-safe
            # automated production or a sustained depot window is observed.
            if self._has_automated_capacity(candidate, context):
                return "throughput"
            record = self.records.get(candidate.item_name)
            if record is None or not record.positive_delivery:
                return "consolidation"
            recovery_epoch = max(
                record.last_non_probe_success_epoch,
                record.last_capability_progress_epoch,
            )
            probe_available = record.commissioning_probe_count == 0 or (
                record.commissioning_probe_failure_count > 0
                and recovery_epoch > record.last_commissioning_probe_epoch
            )
            return "sustained_commissioning" if probe_available else "consolidation"
        if intent == "retain":
            return (
                "throughput"
                if self._has_automated_capacity(candidate, context)
                else "consolidation"
            )
        return self._mode_for(
            candidate,
            lane=INTENT_TO_LANE.get(intent, "anchor"),
            context=context,
            rng=rng,
            recovery=False,
        )

    def _secondary_candidate_for_compose(
        self,
        primary: ContractCandidate,
        *,
        candidates: list[ContractCandidate],
        context: ContractContextSnapshot,
    ) -> ContractCandidate | None:
        alternatives = [
            candidate
            for candidate in candidates
            if candidate.item_name != primary.item_name
            and candidate.mixture_class != "stress"
            and candidate.features is not None
            and int(candidate.features.stage_band) <= self._current_band(context) + 1
            and (
                candidate.mixture_class != "frontier"
                or self._frontier_step_allowed(candidate, self._current_band(context))
            )
        ]
        if not alternatives:
            return None
        # Prefer a less-recent, lower-difficulty partner, but do not filter on
        # evidence: mixed probes are valuable precisely when both lines are new.
        return min(
            alternatives,
            key=lambda candidate: (
                sum(candidate.item_name == product for product in self.recent_products),
                float(candidate.effective_difficulty or 0.0),
                candidate.item_name,
            ),
        )

    def _lane_for(
        self,
        *,
        context: ContractContextSnapshot,
        candidates: list[ContractCandidate],
    ) -> str:
        scheduled = LANE_SCHEDULE[self.completed_epochs % len(LANE_SCHEDULE)]
        if scheduled == "frontier" and self.frontier_failure_streak >= 2:
            return "replay" if any(
                self.records.get(c.item_name) and self.records[c.item_name].capacity_evidence
                for c in candidates
            ) else "anchor"
        return scheduled

    def _recovery_candidates(self, candidates: list[ContractCandidate]) -> list[ContractCandidate]:
        result: list[ContractCandidate] = []
        for candidate in candidates:
            record = self.records.get(candidate.item_name)
            if record is None or record.attempts <= 0:
                continue
            structural_recovery = (
                record.capability_progress_count > 0
                and (
                    record.last_capability_progress_epoch == record.last_epoch
                    or (
                        record.last_capability_progress_epoch == 0
                        and record.last_epoch == self.completed_epochs
                    )
                )
            )
            if structural_recovery and self._recovery_consumed_epochs.get(candidate.item_name) == record.last_epoch:
                continue
            if structural_recovery and record.failure_streak > 0:
                result.append(candidate)
            elif (
                record.capability_progress_count == 0
                and
                record.zero_delivery_count > 0
                and record.last_epoch == self.completed_epochs
                and record.failure_streak > 0
            ):
                result.append(candidate)
        return sorted(result, key=lambda c: (c.item_name, c.effective_difficulty or 0.0))

    def _candidates_for_lane(
        self,
        candidates: list[ContractCandidate],
        *,
        lane: str,
        context: ContractContextSnapshot,
        recovery: list[ContractCandidate],
    ) -> list[ContractCandidate]:
        if recovery:
            return recovery
        current_band = self._current_band(context)
        if lane == "frontier":
            return [
                candidate
                for candidate in candidates
                if candidate.mixture_class == "frontier"
                and candidate.features is not None
                and self._frontier_step_allowed(candidate, current_band)
            ]
        if lane == "replay":
            return self._rotate_recent(
                [
                candidate
                for candidate in candidates
                if self.records.get(candidate.item_name)
                and self.records[candidate.item_name].attempts > 0
                ]
            )
        if lane == "accel":
            return [
                candidate
                for candidate in candidates
                if candidate.mixture_class == "stress"
                and self.records.get(candidate.item_name)
                and self.records[candidate.item_name].capacity_evidence
                and candidate.features is not None
                and candidate.features.stage_band <= current_band
            ]
        return self._rotate_recent(
            [
                candidate
                for candidate in candidates
                if candidate.mixture_class != "frontier"
                and candidate.features is not None
                and candidate.features.stage_band <= current_band
            ]
        )

    def _rotate_recent(
        self,
        candidates: list[ContractCandidate],
    ) -> list[ContractCandidate]:
        """Apply the hard part of the recent-product rotation when possible."""

        if len(candidates) <= 1 or self._last_product is None:
            return candidates
        alternatives = [
            candidate
            for candidate in candidates
            if candidate.item_name != self._last_product
        ]
        return alternatives or candidates

    def _frontier_step_allowed(self, candidate: ContractCandidate, current_band: int) -> bool:
        features = candidate.features
        if features is None:
            return False
        factory_band = getattr(features, "factory_band", None)
        target_band = getattr(features, "target_band", None)
        try:
            target_band = int(target_band if target_band is not None else features.stage_band)
            # The context is authoritative.  A v1 feature record can carry a
            # default zero factory band even when the frozen context is more
            # advanced, so a stale lower value must not reject a valid local
            # edge.  It can never broaden the edge beyond the current context.
            measured_factory_band = (
                current_band
                if factory_band is None
                else max(int(factory_band), current_band)
            )
            if target_band > measured_factory_band + FRONTIER_MAX_BAND_STEP:
                return False
            if target_band > current_band + FRONTIER_MAX_BAND_STEP:
                return False
            # Band labels alone are not enough to make a nuclear-scale jump
            # local.  Keep the same bounded topology checks used by candidate
            # generation for direct/offline callers of this policy.
            maximum_depth = max(3, current_band + 3)
            if int(features.recipe_depth) > maximum_depth:
                return False
            maximum_missing_technology = max(1, current_band + 1)
            return int(features.missing_technology_count) <= maximum_missing_technology
        except (TypeError, ValueError):
            return features.stage_band <= current_band + FRONTIER_MAX_BAND_STEP

    @staticmethod
    def _current_band(context: ContractContextSnapshot) -> int:
        explicit = getattr(context, "factory_band", None)
        explicit_band: int | None = None
        if explicit is not None:
            try:
                explicit_band = max(0, min(int(explicit), 5))
            except (TypeError, ValueError):
                explicit_band = None
        try:
            from fle.envd.contract_features import classify_progression_band

            classified_band = max(0, min(int(classify_progression_band(context)), 5))
            # During the wire-model rollout ``factory_band`` may be omitted or
            # carry its default zero even when the snapshot already proves
            # electricity/automation.  Never let that stale lower value make
            # ordinary same-band anchors look unavailable.
            return max(classified_band, explicit_band or 0)
        except Exception:
            return explicit_band or 0

    @staticmethod
    def _context_production_rate(
        context: ContractContextSnapshot,
        product: str,
    ) -> float:
        """Return only FLE provenance-adjusted production rates.

        The compatibility ``production_rates_*`` fields may contain
        hand-crafted output in snapshots produced before the cheap
        ``get_recent_rate`` detector existed.  Sustained-capacity decisions
        use the explicit automated projection instead.
        """

        return max(
            float(
                (getattr(context, "automated_production_rates_60s", {}) or {}).get(
                    product, 0.0
                )
            ),
            float(
                (getattr(context, "automated_production_rates_300s", {}) or {}).get(
                    product, 0.0
                )
            ),
        )

    @staticmethod
    def _context_delivery_rate(
        context: ContractContextSnapshot,
        product: str,
    ) -> float:
        """Read physical depot rates without relabeling them as production."""

        rates = [
            float((getattr(context, "delivery_rates_60s", {}) or {}).get(product, 0.0)),
            float((getattr(context, "delivery_rates_300s", {}) or {}).get(product, 0.0)),
        ]
        telemetry = getattr(context, "delivery_telemetry", None)
        if telemetry is not None:
            if hasattr(telemetry, "raw_rates_60s"):
                rates.extend(
                    [
                        float(telemetry.raw_rates_60s.get(product, 0.0)),
                        float(telemetry.raw_rates_300s.get(product, 0.0)),
                    ]
                )
            elif isinstance(telemetry, dict):
                raw_60 = telemetry.get("raw_rates_60s", {}) or {}
                raw_300 = telemetry.get("raw_rates_300s", {}) or {}
                rates.extend(
                    [
                        float(raw_60.get(product, 0.0)),
                        float(raw_300.get(product, 0.0)),
                    ]
                )
        return max(rates, default=0.0)

    @classmethod
    def _live_rate(cls, context: ContractContextSnapshot, product: str) -> float:
        return max(
            cls._context_production_rate(context, product),
            cls._context_delivery_rate(context, product),
        )

    def _representatives(self, pool: list[ContractCandidate]) -> list[ContractCandidate]:
        by_product: dict[str, ContractCandidate] = {}
        for candidate in pool:
            if not candidate.accepted or candidate.features is None:
                continue
            current = by_product.get(candidate.item_name)
            if current is None or self._candidate_key(candidate) < self._candidate_key(current):
                by_product[candidate.item_name] = candidate
        return sorted(by_product.values(), key=lambda candidate: candidate.item_name)

    @staticmethod
    def _candidate_key(candidate: ContractCandidate) -> tuple[float, int, str]:
        return (
            float(candidate.effective_difficulty or 0.0),
            int(candidate.deadline_ticks or 0),
            candidate.item_name,
        )

    def _has_evidence(
        self,
        candidate: ContractCandidate,
        context: ContractContextSnapshot,
        *,
        require_sustained: bool = False,
    ) -> bool:
        record = self.records.get(candidate.item_name)
        live_rate = self._live_rate(context, candidate.item_name)
        if require_sustained:
            return bool(record and record.sustained_reliable)
        return bool((record and record.capacity_evidence) or live_rate > EPSILON)

    def _has_automated_capacity(
        self,
        candidate: ContractCandidate,
        context: ContractContextSnapshot,
    ) -> bool:
        """Whether a product may escalate to a sustained service order."""

        record = self.records.get(candidate.item_name)
        return bool(
            (record and record.automated_capacity_evidence)
            or self._context_production_rate(context, candidate.item_name) > EPSILON
        )

    def _selection_score(
        self,
        candidate: ContractCandidate,
        rng: random.Random | None = None,
        *,
        rating: CapabilityRating | None = None,
    ) -> float:
        """Auditable legacy score used by callers probing a single candidate."""

        rating = rating or CapabilityRating(
            mu=0.0,
            sigma=2.0,
            conservative_score=-6.0,
            rated_epoch_count=0,
        )
        record = self.records.get(candidate.item_name)
        attempts = record.attempts if record else 0
        completion = record.completion_mean if record else 0.5
        progress = record.capability_progress_count if record else 0
        uncertainty = 1.0 / math.sqrt(attempts + 1)
        staleness = (
            1.0
            if record is None
            else min(max(self.completed_epochs - record.last_epoch, 0) / 4.0, 1.0)
        )
        difficulty = float(candidate.effective_difficulty or 0.0)
        nearness = math.exp(-abs(difficulty - rating.mu) / max(rating.sigma, 0.5))
        frontier = float(candidate.mixture_class == "frontier")
        recent = sum(candidate.item_name == product for product in self.recent_products)
        value = (
            2.0 * nearness
            + 0.45 * uncertainty
            + 0.30 * staleness
            + 0.40 * min(progress, 2)
            + 0.20 * (1.0 - completion)
            + 0.10 * frontier
            - 0.25 * recent
        )
        return value + (rng.random() * 1e-6 if rng is not None else 0.0)

    def _mode_for(
        self,
        candidate: ContractCandidate,
        *,
        lane: str,
        context: ContractContextSnapshot,
        rng: random.Random,
        recovery: bool,
    ) -> str:
        if recovery:
            return "replay_backoff"
        if lane == "frontier":
            return "commissioning"
        if lane == "accel":
            return "accel_stress"
        record = self.records.get(candidate.item_name)
        context_capacity = max(
            self._context_production_rate(context, candidate.item_name),
            self._context_delivery_rate(context, candidate.item_name),
        ) > EPSILON
        if (record is None or not record.capacity_evidence) and not context_capacity:
            return "commissioning"
        sustained = self._has_automated_capacity(candidate, context)
        return (
            "throughput"
            if sustained and rng.random() < 0.55
            else "consolidation"
        )

    @staticmethod
    def _allow_mixed(*, lane: str, candidates: list[ContractCandidate], rng: random.Random) -> bool:
        return lane in {"anchor", "replay"} and len(candidates) >= 2 and rng.random() < 0.25

    def _secondary_candidate(
        self,
        primary: ContractCandidate,
        *,
        candidates: list[ContractCandidate],
        context: ContractContextSnapshot,
    ) -> ContractCandidate | None:
        alternatives = [candidate for candidate in candidates if candidate.item_name != primary.item_name]
        if not alternatives:
            return None
        current_band = self._current_band(context)
        same_band = [
            candidate
            for candidate in alternatives
            if candidate.features is not None and candidate.features.stage_band <= current_band
        ]
        return sorted(same_band or alternatives, key=self._candidate_key)[0]

    def _build_plan(
        self,
        chosen: list[ContractCandidate],
        *,
        mode: str,
        context: ContractContextSnapshot,
        catalog: ProductCatalog,
        difficulty_model: DifficultyModel,
        rating: CapabilityRating,
        rng: random.Random,
        lane: str,
        reason: str,
        selection_seed: int,
        intent: str = "deepen",
        utility_components: dict[str, float] | None = None,
    ) -> AdaptiveOrderPlan:
        line_plans = [self._size_line(candidate, mode, context, catalog, rng) for candidate in chosen]
        effective_mode = mode
        if mode == "throughput" and not all(
            line_plan[2].get("effective_mode") == "throughput"
            for line_plan in line_plans
        ):
            # Keep direct callers and mixed legacy records from emitting a
            # sustained order after sizing fell back due to missing
            # provenance-safe capacity evidence.
            effective_mode = "consolidation"
        deadline = min(max(plan[1] for plan in line_plans), MAX_SERVICE_DEADLINE_TICKS)
        products = tuple(
            ProductDemandSpec(product=candidate.item_name, quantity=float(quantity))
            for candidate, (quantity, _, _) in zip(chosen, line_plans)
        )
        line_evaluations: list[tuple[Any, float, float, float, dict[str, Any]]] = []
        for candidate, product, (quantity, line_deadline, line_evidence) in zip(chosen, products, line_plans):
            line_features = _features_for(
                context,
                candidate.item_name,
                round(product.quantity),
                int(line_deadline),
                catalog,
                candidate.features.stage_band,
            )
            raw, advantage, effective = _evaluate_difficulty(
                difficulty_model, line_features, candidate.template_id
            )
            line_evidence = dict(line_evidence)
            line_evidence.update(
                {
                    "stage_band": line_features.stage_band,
                    "factory_band": getattr(line_features, "factory_band", self._current_band(context)),
                    "target_band": getattr(line_features, "target_band", line_features.stage_band),
                    "line_deadline_ticks": int(line_deadline),
                    "raw_difficulty": raw,
                    "state_advantage": advantage,
                    "effective_difficulty": effective,
                    "rating_distance": round(abs(effective - rating.mu), 6),
                }
            )
            line_evaluations.append((line_features, raw, advantage, effective, line_evidence))

        primary = chosen[0]
        features = line_evaluations[0][0]
        raw = statistics.fmean(item[1] for item in line_evaluations)
        advantage = statistics.fmean(item[2] for item in line_evaluations)
        effective = statistics.fmean(item[3] for item in line_evaluations)
        composition_penalty = 0.6 * (len(products) - 1)
        service_penalty = 0.4 if effective_mode in {"throughput", "accel_stress"} else 0.0
        candidate = primary.model_copy(
            update={
                "quantity": round(products[0].quantity),
                "deadline_ticks": int(deadline),
                "analytic_minimum_ticks": analytic_feasibility(
                    catalog, primary.item_name, round(products[0].quantity), context
                ),
                "features": features,
                "raw_difficulty": raw + composition_penalty + service_penalty,
                "state_advantage": advantage,
                "effective_difficulty": effective + composition_penalty + service_penalty,
            }
        )
        line_evidence = {
            chosen_candidate.item_name: evidence
            for chosen_candidate, (_, _, _, _, evidence) in zip(chosen, line_evaluations)
        }
        mutation = None
        if lane == "accel":
            mutation = self._accel_mutation(chosen[0], line_evaluations[0][4])
        evidence = {
            "policy": POLICY_VERSION,
            "intent": intent,
            "intent_reason": reason,
            "utility_components": {
                key: round(float(value), 6)
                for key, value in (utility_components or {}).items()
            },
            "lane": lane,
            # Kept as a compatibility diagnostic.  This value is not used to
            # select an order and has no implied long-run target share.
            "lane_target_share": LANE_WEIGHTS.get(lane),
            "selection_reason": reason,
            "mixed_probe": {
                "enabled": len(chosen) > 1,
                "independent_evidence_required": False,
                "components": {
                    candidate.item_name: {
                        "capacity_evidence": self._has_evidence(candidate, context),
                        "sustained_evidence": self._has_evidence(
                            candidate, context, require_sustained=True
                        ),
                        "attempts": self.records.get(candidate.item_name).attempts
                        if self.records.get(candidate.item_name) is not None
                        else 0,
                    }
                    for candidate in chosen
                },
            },
            "parent_epoch_index": (
                self.records.get(primary.item_name).last_epoch
                if self.records.get(primary.item_name) is not None
                else None
            ),
            "parent_product_id": primary.item_name if self.records.get(primary.item_name) is not None else None,
            "rating_before": rating.model_dump(mode="json"),
            "selection_seed": selection_seed,
            "frontier_failure_streak": self.frontier_failure_streak,
            "frontier_guard": {
                "factory_band": self._current_band(context),
                "max_band_step": FRONTIER_MAX_BAND_STEP,
                "eligible": lane != "frontier"
                or self._frontier_step_allowed(primary, self._current_band(context)),
            },
            "mutation": mutation,
            "commissioning_probe": effective_mode == "sustained_commissioning",
            "lines": line_evidence,
            "final_plan": {
                "raw_difficulty": round(raw + composition_penalty + service_penalty, 6),
                "state_advantage": round(advantage, 6),
                "effective_difficulty": round(effective + composition_penalty + service_penalty, 6),
                "rating_distance": round(abs(effective + composition_penalty + service_penalty - rating.mu), 6),
            },
        }
        return AdaptiveOrderPlan(
            candidate=candidate,
            order_kind=(
                "sustained"
                if effective_mode in {"throughput", "accel_stress", "sustained_commissioning"}
                else "one_shot"
            ),
            products=products,
            mode=effective_mode,
            evidence=evidence,
        )

    @staticmethod
    def _accel_mutation(candidate: ContractCandidate, line_evidence: dict[str, Any]) -> dict[str, Any]:
        return {
            "kind": "quantity_multiplier",
            "parent_product": candidate.item_name,
            "parent_quantity": int(candidate.quantity),
            "mutated_quantity": int(line_evidence.get("quantity", candidate.quantity)),
            "axis_count": 1,
        }

    def _plan_score(
        self,
        plan: AdaptiveOrderPlan,
        *,
        rating: CapabilityRating,
        lane: str,
        reason: str,
        context: ContractContextSnapshot,
    ) -> float:
        difficulty = float(plan.candidate.effective_difficulty or 0.0)
        distance = abs(difficulty - rating.mu)
        nearness = math.exp(-distance / max(float(rating.sigma), 0.5))
        information = 1.0 - math.exp(-distance / max(float(rating.sigma), 0.5))
        record = self.records.get(plan.candidate.item_name)
        replay_signal = 0.0
        if record is not None:
            replay_signal = min(
                1.0,
                0.20 * (1.0 - min(max(record.completion_mean, 0.0), 1.0))
                + 0.25 * record.capability_progress_count
                + 0.25 * record.failure_streak
                + 0.20 * (1.0 / math.sqrt(record.attempts + 1))
                + 0.25 * min(max(self.completed_epochs - record.last_epoch, 0) / 4.0, 1.0),
            )
        frontier_penalty = 0.0
        if lane == "frontier":
            frontier_penalty = 0.35 * self.frontier_failure_streak
            if not self._frontier_step_allowed(plan.candidate, self._current_band(context)):
                return -1e9
        if reason == "capability_progress_replay":
            replay_signal += 0.8
        if reason == "zero_delivery_backoff":
            replay_signal += 0.5
        lane_bonus = {"anchor": 0.20, "replay": 0.55, "frontier": 0.15, "accel": 0.10}[lane]
        recent = sum(
            plan.candidate.item_name == product for product in self.recent_products
        )
        # Keep the 80% recent-product rotation as a deterministic penalty.  It
        # matters even when a sparse pool has only anchor candidates; otherwise
        # rating-nearness can repeatedly select the same line forever.
        recent_penalty = 0.35 * min(recent, 2)
        return (
            3.0 * nearness
            + 0.35 * information
            + lane_bonus
            + replay_signal
            - frontier_penalty
            - recent_penalty
        )

    # ------------------------------------------------------------------
    # Pressure sizing
    # ------------------------------------------------------------------

    def _size_line(
        self,
        candidate: ContractCandidate,
        mode: str,
        context: ContractContextSnapshot,
        catalog: ProductCatalog,
        rng: random.Random,
    ) -> tuple[int, int, dict[str, Any]]:
        assert candidate.features is not None
        product = candidate.item_name
        record = self.records.get(product)
        production_rate = self._context_production_rate(context, product)
        delivery_rate = self._context_delivery_rate(context, product)
        live_rate = max(production_rate, delivery_rate)
        has_evidence = bool((record and record.capacity_evidence) or live_rate > EPSILON)
        automated_capacity = bool(
            (record and record.automated_capacity_evidence)
            or production_rate > EPSILON
        )
        requested_mode = mode
        depth = max(int(candidate.features.recipe_depth), 1)
        if not has_evidence:
            quantity = round_to_batch(max(5.0, 120.0 / (depth * depth)))
            analytic = analytic_feasibility(catalog, product, quantity, context)
            setup_minutes = 10.0 + 5.0 * depth + 10.0 * candidate.features.missing_technology_count
            deadline = max(
                int(setup_minutes * TICKS_PER_MINUTE),
                int(analytic * 1.75),
                MIN_COMMISSIONING_DEADLINE_TICKS,
            )
            deadline = min(deadline, MAX_COMMISSIONING_DEADLINE_TICKS)
            return quantity, deadline, {
                "basis": "commissioning_cold_start",
                "evidence_kind": "none",
                "requested_mode": requested_mode,
                "effective_mode": "commissioning",
                "automated_capacity_evidence": False,
                "recipe_depth": depth,
                "quantity": quantity,
                "deadline_ticks": deadline,
                "deadline_bound": MAX_COMMISSIONING_DEADLINE_TICKS,
            }

        if mode == "sustained_commissioning":
            # Do not size this from delivered_rates: those may be manual
            # bursts. This is an automation probe, not qualification.
            reference_rate = STAGE_REFERENCE_RATES.get(
                int(candidate.features.stage_band), 30.0
            )
            target_rate = max(
                1.0,
                reference_rate
                * COMMISSIONING_PROBE_RATE_FRACTION
                / max(depth, 1),
            )
            window = COMMISSIONING_PROBE_WINDOW_MINUTES
            quantity = max(1, round_to_batch(target_rate * window))
            analytic = analytic_feasibility(catalog, product, quantity, context)
            deadline = min(
                max(
                    int(window * TICKS_PER_MINUTE),
                    int(analytic * 1.25),
                    MIN_SERVICE_DEADLINE_TICKS,
                ),
                MAX_SERVICE_DEADLINE_TICKS,
            )
            return quantity, deadline, {
                "basis": "sustained_commissioning_probe",
                "requested_mode": requested_mode,
                "effective_mode": "sustained_commissioning",
                "automated_capacity_evidence": False,
                "evidence_kind": self._evidence_kind(
                    record,
                    live_rate,
                    delivery_rate=delivery_rate,
                    production_rate=production_rate,
                ),
                "live_production_rate": round(production_rate, 6),
                "live_delivery_rate": round(delivery_rate, 6),
                "target_rate": round(target_rate, 6),
                "window_minutes": window,
                "quantity": quantity,
                "deadline_ticks": deadline,
                "deadline_bound": MAX_SERVICE_DEADLINE_TICKS,
            }

        rates = list(record.empirical_rates if record else ())
        if live_rate > EPSILON:
            rates.append(live_rate)
        center = statistics.median(rates) if rates else STAGE_REFERENCE_RATES.get(candidate.features.stage_band, 30.0) * 0.25
        spread = (
            statistics.pstdev(rates)
            if len(rates) >= 2
            else center / math.sqrt(max((record.attempts if record else 0) + 1, 1))
        )
        completion = record.completion_mean if record else 0.5
        failure_streak = record.failure_streak if record else 0
        backoff = max(0.45, 1.0 - 0.15 * min(failure_streak, 3))
        if mode == "throughput":
            # Raw delivery rates can be a single terminal burst from a one-shot
            # order. Only recorded sustained windows are depot evidence. When
            # no such window exists, a provenance-safe automated production
            # rate is a valid fallback for sizing the first sustained probe.
            depot_rates = list(record.empirical_depot_rates if record else ())
            production_rates = list(record.measured_rates if record else ())
            if production_rate > EPSILON:
                production_rates.append(production_rate)
            throughput_rates = depot_rates or production_rates
            if not automated_capacity or not throughput_rates:
                mode = "consolidation"
        if mode == "throughput":
            window = rng.uniform(10.0, 20.0)
            throughput_center = statistics.fmean(throughput_rates)
            throughput_spread = (
                statistics.pstdev(throughput_rates)
                if len(throughput_rates) >= 2
                else throughput_center
            )
            lower_confidence_rate = max(
                throughput_center
                - 1.28
                * throughput_spread
                / math.sqrt(max(len(throughput_rates), 1)),
                0.0,
            )
            target_rate = max(
                lower_confidence_rate * (0.80 + 0.10 * completion) * backoff,
                1.0,
            )
            deadline = int(window * TICKS_PER_MINUTE)
            basis = (
                "sustained_depot_throughput_lcb"
                if depot_rates
                else "automated_production_throughput_lcb"
            )
        elif mode == "accel_stress":
            window = rng.uniform(12.0, 20.0)
            target_rate = max(center * (1.20 + 0.10 * completion), 1.0)
            deadline = int(window * TICKS_PER_MINUTE)
            basis = "accel_single_axis_quantity"
        else:
            window = rng.uniform(20.0, 45.0)
            exploration = max(spread * 0.20, center * 0.03)
            target_rate = max((center * (0.65 + 0.25 * completion) + exploration) * backoff, 1.0)
            conservative_rate = max(min(rates) if rates else center * 0.5, 1.0)
            deadline = int((target_rate * window / conservative_rate) * TICKS_PER_MINUTE * 1.15)
            basis = "empirical_capacity_consolidation"

        quantity = round_to_batch(target_rate * window)
        analytic = analytic_feasibility(catalog, product, quantity, context)
        if mode != "throughput":
            deadline = max(deadline, int(analytic * 1.25))
        deadline = min(max(deadline, MIN_SERVICE_DEADLINE_TICKS), MAX_SERVICE_DEADLINE_TICKS)
        if record is not None and record.last_quantity > 0 and failure_streak > 0:
            quantity = max(1, min(quantity, round_to_batch(record.last_quantity * 0.85)))
        return quantity, deadline, {
            "basis": basis,
            "requested_mode": requested_mode,
            "effective_mode": mode,
            "automated_capacity_evidence": automated_capacity,
            "evidence_kind": self._evidence_kind(
                record,
                live_rate,
                delivery_rate=delivery_rate,
                production_rate=production_rate,
            ),
            "live_production_rate": round(production_rate, 6),
            "live_delivery_rate": round(delivery_rate, 6),
            "observed_rate_center": round(center, 6),
            "observed_rate_spread": round(spread, 6),
            "completion_mean": round(completion, 6),
            "failure_streak": failure_streak,
            "target_rate": round(target_rate, 6),
            "depot_rate_lcb": round(lower_confidence_rate, 6)
            if basis
            in {
                "sustained_depot_throughput_lcb",
                "automated_production_throughput_lcb",
            }
            else None,
            "window_minutes": round(window, 6),
            "quantity": quantity,
            "deadline_ticks": deadline,
            "deadline_bound": MAX_SERVICE_DEADLINE_TICKS,
        }

    @staticmethod
    def _evidence_kind(
        record: ProductEvidence | None,
        live_rate: float,
        *,
        delivery_rate: float = 0.0,
        production_rate: float | None = None,
    ) -> str:
        if record is not None and record.sustained_evidence:
            return "sustained_depot"
        if delivery_rate > EPSILON:
            return "observed_depot_delivery"
        if (
            (production_rate if production_rate is not None else live_rate) > EPSILON
            or (record is not None and record.observed_production)
        ):
            return "observed_production"
        if record is not None and record.positive_delivery:
            return "positive_delivery"
        return "none"


__all__ = [
    "AdaptiveOrderPlan",
    "EvidenceDrivenCustomerPolicy",
    "INTENTS",
    "INTENT_TO_LANE",
    "LANE_SCHEDULE",
    "LANE_WEIGHTS",
    "MAX_COMMISSIONING_DEADLINE_TICKS",
    "MAX_SERVICE_DEADLINE_TICKS",
    "MIN_COMMISSIONING_DEADLINE_TICKS",
    "POLICY_VERSION",
    "ProductEvidence",
    "STALE_CAPABILITY_EPOCHS",
]
