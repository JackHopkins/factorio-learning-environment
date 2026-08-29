"""Externally-owned customer contracts: hidden demand schedules, sink-based
fulfillment measurement, and the fulfillment reward integral.

The customer is deliberately outside the factory and outside the agent's
action space.  A schedule is immutable input shipped inside the task spec;
the runtime only ever reveals orders whose issue tick has passed.  Fulfillment
is credited exclusively when items physically cross the boundary into
customer-owned sink depots, so internal production counts, inventory shuffles,
and crafting statistics cannot generate reward.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import random
import secrets
from dataclasses import dataclass, field
from typing import Any

from fle.envd.models import (
    CUSTOMER_GENERATOR_VERSION,
    ContractStatus,
    CustomerContractSpec,
    DemandOrderSpec,
    OpenContractView,
    ProductDemandSpec,
)

SLICE_TICKS = 3600
MIN_ITEMS_PER_SERVICE_WINDOW = 2
# Width of the sink-side delivery aggregation window.  Must match BUCKET_TICKS
# in fle/env/tools/admin/customer_depot/server.lua.  A bucket is attributed at
# its END tick: deliveries count only toward orders already open when the
# bucket closes, which can under-credit by at most one bucket but never grants
# credit before physical delivery.
DELIVERY_BUCKET_TICKS = 60
CUSTOMER_ENGINE_VERSION = "customer-engine-v3"


def _sustained_service_details(
    products: list[ProductDemandSpec] | tuple[ProductDemandSpec, ...],
    credits_by_product: dict[str, list[tuple[int, float]]],
    *,
    start_tick: int,
    deadline_ticks: int,
) -> dict[str, dict[str, Any]]:
    """Compute the canonical per-line sustained score and its audit slices."""

    window = max(int(deadline_ticks), 1)
    details: dict[str, dict[str, Any]] = {}
    for product in products:
        credits = sorted(credits_by_product.get(product.product, []))
        quantity = max(int(round(product.quantity)), 1)
        time_windows = max(1, math.ceil(window / SLICE_TICKS))
        quantity_windows = max(1, quantity // MIN_ITEMS_PER_SERVICE_WINDOW)
        window_count = min(time_windows, quantity_windows)
        weighted_score = 0.0
        slice_scores: list[float] = []
        window_quotas: list[int] = []
        for index in range(window_count):
            slice_start = start_tick + (index * window) // window_count
            slice_end = start_tick + ((index + 1) * window) // window_count
            slice_len = max(slice_end - slice_start, 0)
            if slice_len <= 0:
                continue
            requested = (
                ((index + 1) * quantity) // window_count
                - (index * quantity) // window_count
            )
            delivered = sum(
                amount
                for tick, amount in credits
                if slice_start <= tick < slice_end
            )
            ratio = min(delivered / max(requested, 1e-9), 1.0)
            slice_scores.append(round(ratio, 6))
            window_quotas.append(requested)
            weighted_score += ratio * slice_len / window
        details[product.product] = {
            "score": weighted_score,
            "slice_scores": slice_scores,
            "window_count": window_count,
            "window_quotas": window_quotas,
        }
    return details


def _canonical(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str
    ).encode()


def _stable_seed(*parts: Any) -> int:
    return int.from_bytes(hashlib.sha256(_canonical(parts)).digest()[:8], "big")


# ---------------------------------------------------------------------------
# Deterministic schedule generation
# ---------------------------------------------------------------------------

# Curated product pool.  Tier approximates supply-chain depth; ``rate`` is a
# coarse reference throughput (items/minute) a competent mid-game factory can
# sustain, used only for deadline sizing.  Calibration against measured
# capability is the curriculum layer's job, not the generator's.
_CATALOG: dict[str, dict[str, Any]] = {
    "iron-plate": {"tier": 0, "family": "smelting", "qty": 8000, "rate": 1500},
    "copper-plate": {"tier": 0, "family": "smelting", "qty": 6000, "rate": 1200},
    "steel-plate": {"tier": 1, "family": "smelting", "qty": 4000, "rate": 500},
    "stone-brick": {"tier": 0, "family": "smelting", "qty": 3000, "rate": 600},
    "concrete": {"tier": 1, "family": "structural", "qty": 3000, "rate": 500},
    "iron-gear-wheel": {"tier": 1, "family": "components", "qty": 4000, "rate": 700},
    "copper-cable": {"tier": 1, "family": "components", "qty": 5000, "rate": 900},
    "electronic-circuit": {"tier": 1, "family": "circuits", "qty": 5000, "rate": 600},
    "advanced-circuit": {"tier": 2, "family": "circuits", "qty": 2000, "rate": 180},
    "processing-unit": {"tier": 3, "family": "circuits", "qty": 500, "rate": 40},
    "engine-unit": {"tier": 1, "family": "logistics", "qty": 2500, "rate": 200},
    "electric-engine-unit": {"tier": 2, "family": "logistics", "qty": 1200, "rate": 90},
    "flying-robot-frame": {"tier": 2, "family": "robots", "qty": 300, "rate": 25},
    "construction-robot": {"tier": 3, "family": "robots", "qty": 500, "rate": 40},
    "logistic-robot": {"tier": 3, "family": "robots", "qty": 400, "rate": 35},
    "low-density-structure": {"tier": 2, "family": "rocket", "qty": 800, "rate": 50},
    "rocket-control-unit": {"tier": 3, "family": "rocket", "qty": 400, "rate": 25},
    "rocket-fuel": {"tier": 2, "family": "rocket", "qty": 500, "rate": 60},
    "nuclear-fuel": {"tier": 3, "family": "power", "qty": 100, "rate": 6},
    "rail": {"tier": 1, "family": "transport", "qty": 4000, "rate": 800},
    "locomotive": {"tier": 2, "family": "transport", "qty": 40, "rate": 4},
    "cargo-wagon": {"tier": 2, "family": "transport", "qty": 40, "rate": 4},
    "artillery-shell": {"tier": 3, "family": "military", "qty": 100, "rate": 5},
    "uranium-rounds-magazine": {
        "tier": 2,
        "family": "military",
        "qty": 600,
        "rate": 60,
    },
    "battery": {"tier": 2, "family": "components", "qty": 1200, "rate": 120},
    "plastic-bar": {"tier": 1, "family": "components", "qty": 4000, "rate": 600},
    "sulfur": {"tier": 1, "family": "chemistry", "qty": 2000, "rate": 350},
    "lubricant-barrel": {"tier": 1, "family": "chemistry", "qty": 800, "rate": 150},
}

_TIER_WEIGHTS = {
    0: (0.35, 0.15, 0.05),
    1: (0.45, 0.35, 0.20),
    2: (0.15, 0.35, 0.45),
    3: (0.05, 0.15, 0.30),
}


@dataclass(frozen=True)
class ScheduleConfig:
    """Difficulty knobs for procedural contract generation."""

    horizon_ticks: int
    difficulty: float = 0.5
    order_count: int = 6
    allow_sustained: bool = True
    allow_mixed: bool = True
    allow_surges: bool = True
    warmup_ticks: int = 36000


def _quantity(
    rng: random.Random, entry: dict[str, Any], config: ScheduleConfig
) -> float:
    scale = 0.5 + config.difficulty
    jitter = rng.uniform(0.75, 1.3)
    return max(1.0, round(entry["qty"] * scale * jitter))


def _deadline(
    rng: random.Random,
    issue_tick: int,
    total_quantity: float,
    entry: dict[str, Any],
    config: ScheduleConfig,
) -> int:
    reference_ticks = total_quantity / max(entry["rate"], 1e-9) * 60.0
    # Slack shrinks with difficulty; never below 1.5x the reference window.
    pressure = 5.0 - 3.5 * min(max(config.difficulty, 0.0), 1.0)
    slack = max(reference_ticks * pressure, 36000)
    jitter = rng.uniform(0.85, 1.2)
    return int(issue_tick + slack * jitter)


def generate_contract_schedule(
    config: ScheduleConfig, seed: int
) -> CustomerContractSpec:
    """Deterministically derive a hidden order stream from ``(config, seed)``.

    Same inputs yield byte-identical schedules across platforms and processes;
    the schedule is therefore reproducible offline from the task spec alone.
    """

    rng = random.Random(_stable_seed(CUSTOMER_GENERATOR_VERSION, seed, config))
    difficulty = min(max(config.difficulty, 0.0), 1.0)

    products = [
        (name, entry)
        for name, entry in _CATALOG.items()
        if entry["tier"] <= max(0, min(3, round(difficulty * 3)))
    ]

    def _pick() -> tuple[str, dict[str, Any]]:
        population = []
        weights_ = []
        tier_bias = int(difficulty * 2)
        for name, entry in products:
            population.append((name, entry))
            weights_.append(
                _TIER_WEIGHTS.get(entry["tier"], (1.0,))[
                    min(tier_bias, len(_TIER_WEIGHTS.get(entry["tier"], (1.0,))) - 1)
                ]
            )
        return rng.choices(population, weights=weights_, k=1)[0]

    orders: list[DemandOrderSpec] = []
    cursor = config.warmup_ticks
    seen_families: list[str] = []
    for index in range(config.order_count):
        archetype_roll = rng.random()
        sustained_viable = (
            config.allow_sustained and archetype_roll < 0.2 + 0.25 * difficulty
        )
        surge_viable = (
            config.allow_surges
            and seen_families
            and not sustained_viable
            and archetype_roll > 0.88 - 0.1 * difficulty
        )
        mixed_viable = (
            config.allow_mixed
            and not sustained_viable
            and not surge_viable
            and archetype_roll < 0.25 + 0.3 * difficulty
        )

        if sustained_viable:
            name, entry = _pick()
            minutes = rng.choice([10, 15, 20, 30])
            rate_scale = (0.4 + difficulty) * rng.uniform(0.8, 1.2)
            rate = max(1.0, entry["rate"] * 0.25 * rate_scale)
            quantity = round(rate * minutes)
            order = DemandOrderSpec(
                order_id=f"ord-{index:03d}-sus",
                kind="sustained",
                products=[ProductDemandSpec(product=name, quantity=float(quantity))],
                issue_tick=cursor,
                due_tick=int(cursor + minutes * 3600),
                weight=rng.uniform(1.0, 2.0),
            )
        elif surge_viable and seen_families:
            family = rng.choice(seen_families[-3:])
            candidates = [
                (name, entry) for name, entry in products if entry["family"] == family
            ]
            name, entry = rng.choice(candidates)
            multiplier = rng.choice([2.0, 2.5, 3.0])
            quantity = _quantity(rng, entry, config) * multiplier
            order = DemandOrderSpec(
                order_id=f"ord-{index:03d}-surge",
                kind="one_shot",
                products=[ProductDemandSpec(product=name, quantity=quantity)],
                issue_tick=cursor,
                due_tick=_deadline(rng, cursor, quantity, entry, config),
                weight=rng.uniform(1.5, 2.5),
            )
        elif mixed_viable:
            chosen: dict[str, dict[str, Any]] = {}
            for _ in range(rng.randint(2, 3)):
                name, entry = _pick()
                chosen.setdefault(name, entry)
            specs = []
            reference = 0.0
            for name, entry in chosen.items():
                quantity = _quantity(rng, entry, config)
                specs.append(ProductDemandSpec(product=name, quantity=quantity))
                reference += quantity / max(entry["rate"], 1e-9) * 60.0
            slack = max(reference * (5.0 - 3.5 * difficulty), 36000)
            order = DemandOrderSpec(
                order_id=f"ord-{index:03d}-mix",
                kind="one_shot",
                products=specs,
                issue_tick=cursor,
                due_tick=int(cursor + slack * rng.uniform(0.85, 1.2)),
                weight=rng.uniform(1.2, 2.0),
            )
        else:
            name, entry = _pick()
            quantity = _quantity(rng, entry, config)
            order = DemandOrderSpec(
                order_id=f"ord-{index:03d}-bulk",
                kind="one_shot",
                products=[ProductDemandSpec(product=name, quantity=quantity)],
                issue_tick=cursor,
                due_tick=_deadline(rng, cursor, quantity, entry, config),
                weight=rng.uniform(1.0, 2.0),
            )

        orders.append(order)
        seen_families.append(_CATALOG[order.products[0].product]["family"])
        gap = rng.uniform(0.5, 1.1) * (72000 - 36000 * difficulty)
        cursor = max(order.due_tick, int(cursor + gap))

    return CustomerContractSpec(
        generator_version=CUSTOMER_GENERATOR_VERSION,
        orders=sorted(orders, key=lambda o: (o.issue_tick, o.order_id)),
    )


# ---------------------------------------------------------------------------
# Runtime engine
# ---------------------------------------------------------------------------


@dataclass
class _OrderState:
    spec: DemandOrderSpec
    status: ContractStatus = "pending"
    fulfilled: dict[str, float] = field(default_factory=dict)
    absorbed: dict[str, float] = field(default_factory=dict)
    credits: dict[str, list[tuple[int, float]]] = field(default_factory=dict)
    completion_tick: int | None = None


@dataclass(frozen=True)
class DeliveryBucket:
    """Aggregated sink deliveries for one 60-tick window."""

    start_tick: int
    items: dict[str, float]


@dataclass
class OrderResult:
    order_id: str
    kind: str
    status: str
    required: bool
    weight: float
    requested: dict[str, float]
    accepted: dict[str, float]
    ratio: float
    lateness_penalty: float
    completion_tick: int | None = None
    delivery_telemetry: dict[str, Any] = field(default_factory=dict)

    def as_payload(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "kind": self.kind,
            "status": self.status,
            "required": self.required,
            "weight": self.weight,
            "requested": self.requested,
            "accepted": self.accepted,
            "ratio": self.ratio,
            "lateness_penalty": self.lateness_penalty,
            "completion_tick": self.completion_tick,
            "delivery_telemetry": self.delivery_telemetry,
        }


@dataclass
class ContractEvaluationResult:
    commitment: str
    engine_version: str
    finalized_at_tick: int
    order_results: list[OrderResult]
    aggregate_ratio: float
    fulfillment_reward: float
    penalty: float
    net_reward: float
    unattributed: dict[str, float]
    receipt: dict[str, Any]
    receipt_mac: str
    delivery_telemetry: dict[str, Any] = field(default_factory=dict)


class ContractEngine:
    """Authoritative in-worker state machine for one lease's demand schedule."""

    def __init__(self, spec: CustomerContractSpec, start_tick: int = 0):
        self.spec = spec
        self._orders: list[_OrderState] = [
            _OrderState(spec=order) for order in spec.orders
        ]
        self._current_tick = start_tick
        self._unattributed: dict[str, float] = {}
        self._revealed_count = 0

    # -- clock --------------------------------------------------------------

    @property
    def current_tick(self) -> int:
        return self._current_tick

    def _advance_to(self, tick: int) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        self._current_tick = max(self._current_tick, tick)
        for state in self._orders:
            spec = state.spec
            if state.status == "pending" and spec.issue_tick <= self._current_tick:
                state.status = "open"
                events.append(
                    {
                        "event": "contract_issued",
                        "order_id": spec.order_id,
                        "tick": spec.issue_tick,
                    }
                )
            if state.status == "open" and spec.close_tick <= self._current_tick:
                complete = (
                    self._sustained_ratio(state) >= 1.0 - 1e-9
                    if spec.kind == "sustained"
                    else all(
                        state.fulfilled.get(p.product, 0.0) >= p.quantity - 1e-9
                        for p in spec.products
                    )
                )
                state.status = "fulfilled" if complete else "expired"
                if state.completion_tick is None and complete:
                    state.completion_tick = spec.close_tick
                events.append(
                    {
                        "event": (
                            "contract_fulfilled" if complete else "contract_expired"
                        ),
                        "order_id": spec.order_id,
                        "tick": spec.close_tick,
                    }
                )
        return events

    # -- deliveries ---------------------------------------------------------

    def sync(
        self, current_tick: int, buckets: list[DeliveryBucket]
    ) -> list[dict[str, Any]]:
        """Advance the clock and attribute chronological delivery buckets."""

        events: list[dict[str, Any]] = []
        for bucket in sorted(buckets, key=lambda b: b.start_tick):
            bucket_end = bucket.start_tick + DELIVERY_BUCKET_TICKS - 1
            events.extend(self._advance_to(min(bucket_end, current_tick)))
            self._attribute(bucket, min(bucket_end, current_tick))
        events.extend(self._advance_to(current_tick))
        return events

    def _absorb_capacity(self, state: _OrderState, product: str) -> float:
        requested = next(
            p.quantity for p in state.spec.products if p.product == product
        )
        already = state.absorbed.get(product, 0.0)
        return max(requested - already, 0.0)

    def _attribute(self, bucket: DeliveryBucket, tick: int) -> None:
        for product, amount in sorted(bucket.items.items()):
            remaining = float(amount)
            for state in self._states_open_for(product, tick):
                if state.spec.kind == "sustained":
                    credit = remaining
                else:
                    capacity = self._absorb_capacity(state, product)
                    if capacity <= 1e-9:
                        continue
                    credit = min(capacity, remaining)
                state.absorbed[product] = state.absorbed.get(product, 0.0) + credit
                state.fulfilled[product] = state.fulfilled.get(product, 0.0) + credit
                state.credits.setdefault(product, []).append((tick, credit))
                remaining -= credit
                if state.spec.kind == "one_shot" and self._order_complete(state):
                    state.completion_tick = tick
                if remaining <= 1e-9:
                    break
            if remaining > 1e-9:
                self._unattributed[product] = (
                    self._unattributed.get(product, 0.0) + remaining
                )

    def _states_open_for(self, product: str, tick: int) -> list[_OrderState]:
        open_states = [
            state
            for state in self._orders
            if state.status == "open"
            and any(p.product == product for p in state.spec.products)
        ]
        return sorted(open_states, key=lambda s: (s.spec.issue_tick, s.spec.order_id))

    def _order_complete(self, state: _OrderState) -> bool:
        return all(
            state.fulfilled.get(p.product, 0.0) >= p.quantity - 1e-9
            for p in state.spec.products
        )

    @staticmethod
    def _delivery_telemetry(state: _OrderState) -> dict[str, Any]:
        """Expose raw bucket coverage separately from sustained service."""

        spec = state.spec
        window = max(spec.due_tick - spec.issue_tick, 1)
        bucket_count = max(1, math.ceil(window / DELIVERY_BUCKET_TICKS))
        service = _sustained_service_details(
            spec.products,
            state.credits,
            start_tick=spec.issue_tick,
            deadline_ticks=window,
        )
        lines: dict[str, Any] = {}
        for product in spec.products:
            credits = sorted(state.credits.get(product.product, []))
            active_buckets = {
                int(tick // DELIVERY_BUCKET_TICKS)
                for tick, amount in credits
                if amount > 0
            }
            line_service = service[product.product]
            lines[product.product] = {
                "requested": float(product.quantity),
                "accepted": round(
                    min(state.fulfilled.get(product.product, 0.0), product.quantity),
                    6,
                ),
                "raw_bucket_count": len(active_buckets),
                "raw_bucket_coverage_ratio": round(
                    len(active_buckets) / bucket_count, 6
                ),
                "slice_scores": line_service["slice_scores"],
                "service_window_count": line_service["window_count"],
                "service_window_quotas": line_service["window_quotas"],
                "sustained_service_score": round(line_service["score"], 6),
            }
        return {
            "bucket_ticks": DELIVERY_BUCKET_TICKS,
            "window_ticks": window,
            "lines": lines,
        }

    # -- observation --------------------------------------------------------

    def student_view(self) -> list[OpenContractView]:
        views: list[OpenContractView] = []
        for state in self._orders:
            if state.status == "pending":
                continue
            spec = state.spec
            views.append(
                OpenContractView(
                    order_id=spec.order_id,
                    kind=spec.kind,
                    products=list(spec.products),
                    issued_at_tick=spec.issue_tick,
                    due_tick=spec.due_tick,
                    grace_ticks=spec.grace_ticks,
                    status=state.status,
                    completion_ratio=round(
                        self._sustained_ratio(state)
                        if spec.kind == "sustained"
                        else self._one_shot_ratio(state),
                        6,
                    ),
                    fulfilled={
                        p.product: round(state.fulfilled.get(p.product, 0.0), 4)
                        for p in spec.products
                    },
                    remaining={
                        p.product: round(
                            max(p.quantity - state.fulfilled.get(p.product, 0.0), 0.0),
                            4,
                        )
                        for p in spec.products
                    },
                )
            )
        return views

    # -- scoring ------------------------------------------------------------

    @staticmethod
    def _one_shot_ratio(state: _OrderState) -> float:
        ratios = []
        for product in state.spec.products:
            requested = product.quantity
            accepted = min(state.fulfilled.get(product.product, 0.0), requested)
            ratios.append(accepted / requested if requested > 0 else 1.0)
        return sum(ratios) / len(ratios) if ratios else 1.0

    @staticmethod
    def _sustained_ratio(state: _OrderState) -> float:
        """Score a sustained order by slicing its window.

        Each slice is scored ``min(1, delivered/requested)`` against the
        pro-rated slice quantity, so steady supply beats burst-and-idle: a
        burst fills one slice and starves the rest.
        """

        spec = state.spec
        window = max(spec.due_tick - spec.issue_tick, 1)
        details = _sustained_service_details(
            spec.products,
            state.credits,
            start_tick=spec.issue_tick,
            deadline_ticks=window,
        )
        scores = [details[product.product]["score"] for product in spec.products]
        return sum(scores) / len(scores) if scores else 1.0

    def evaluate(
        self,
        finalized_at_tick: int,
        *,
        signing_key: bytes | None = None,
        receipt_context: dict[str, Any] | None = None,
    ) -> ContractEvaluationResult:
        self._advance_to(finalized_at_tick)
        results: list[OrderResult] = []
        weighted_ratio = 0.0
        weighted_penalty = 0.0
        total_weight = 0.0
        for state in self._orders:
            # Never-revealed demand contributes nothing to the integral: an
            # order the customer has not yet issued cannot dilute fulfillment.
            if state.status == "pending":
                continue
            spec = state.spec
            ratio = (
                self._sustained_ratio(state)
                if spec.kind == "sustained"
                else self._one_shot_ratio(state)
            )
            lateness = max(0.0, 1.0 - ratio)
            results.append(
                OrderResult(
                    order_id=spec.order_id,
                    kind=spec.kind,
                    status=state.status,
                    required=spec.required,
                    weight=spec.weight,
                    requested={p.product: p.quantity for p in spec.products},
                    accepted={
                        p.product: min(state.fulfilled.get(p.product, 0.0), p.quantity)
                        for p in spec.products
                    },
                    ratio=ratio,
                    lateness_penalty=lateness,
                    completion_tick=state.completion_tick,
                    delivery_telemetry=self._delivery_telemetry(state),
                )
            )
            weighted_ratio += spec.weight * ratio
            weighted_penalty += spec.weight * lateness
            total_weight += spec.weight

        aggregate = weighted_ratio / total_weight if total_weight else 1.0
        penalty = (
            self.spec.lateness_penalty_weight * weighted_penalty / total_weight
            if total_weight
            else 0.0
        )
        receipt_payload = {
            "engine_version": CUSTOMER_ENGINE_VERSION,
            "commitment": self.spec.commitment,
            "finalized_at_tick": finalized_at_tick,
            "receipt_context": receipt_context or {},
            "aggregate_ratio": aggregate,
            "order_results": [result.as_payload() for result in results],
            "unattributed": self._unattributed,
        }
        mac = _sign_payload(receipt_payload, signing_key or _resolve_key())
        return ContractEvaluationResult(
            commitment=self.spec.commitment,
            engine_version=CUSTOMER_ENGINE_VERSION,
            finalized_at_tick=finalized_at_tick,
            order_results=results,
            aggregate_ratio=aggregate,
            fulfillment_reward=weighted_ratio / total_weight if total_weight else 0.0,
            penalty=penalty,
            net_reward=(
                weighted_ratio - self.spec.lateness_penalty_weight * weighted_penalty
            )
            / total_weight
            if total_weight
            else 0.0,
            unattributed=dict(self._unattributed),
            receipt=receipt_payload,
            receipt_mac=mac,
            delivery_telemetry={
                result.order_id: result.delivery_telemetry for result in results
            },
        )


def _resolve_key() -> bytes:
    env_name = "FLE_CUSTOMER_RECEIPT_KEY"
    secret = os.environ.get(env_name)
    if secret:
        return secret.encode()
    # Ephemeral session key: receipts stay verifiable within this process
    # only.  Benchmark deployments must pin FLE_CUSTOMER_RECEIPT_KEY.
    return secrets.token_bytes(32)


def _sign_payload(payload: dict[str, Any], key: bytes) -> str:
    return hmac.new(key, _canonical(payload), hashlib.sha256).hexdigest()


def verify_receipt(payload: dict[str, Any], mac: str, key: bytes) -> bool:
    return hmac.compare_digest(_sign_payload(payload, key), mac)


def success_from_evaluation(
    result: ContractEvaluationResult, spec: CustomerContractSpec
) -> bool:
    required_results = [r for r in result.order_results if r.required]
    required_orders = [order for order in spec.orders if order.required]
    if not required_results:
        # A schedule with required demand cannot be passed by finalizing before
        # its first required order is issued. Optional-only schedules remain
        # vacuously successful.
        return not required_orders
    per_order = all(
        r.ratio + 1e-9 >= _order_success_floor(spec) for r in required_results
    )
    return per_order and result.aggregate_ratio + 1e-9 >= spec.success_ratio


def _order_success_floor(spec: CustomerContractSpec) -> float:
    # Required orders must be fully met unless the aggregate threshold was
    # explicitly relaxed below 1.0, in which case orders may miss by the
    # complementary margin.
    return min(1.0, spec.success_ratio)


# ---------------------------------------------------------------------------
# Single active order (adaptive contract epochs)
# ---------------------------------------------------------------------------

ACTIVE_ORDER_ENGINE_VERSION = "active-order-v4"


@dataclass
class ActiveOrderOutcome:
    """Detailed delivery accounting for one committed epoch order."""

    engine_version: str
    item_name: str
    requested_quantity: int
    delivered_quantity: float
    requested_by_product: dict[str, float]
    delivered_by_product: dict[str, float]
    completion_ratio: float
    status: str  # fulfilled | partial | expired | abandoned
    activation_tick: int
    terminal_tick: int
    first_delivery_tick: int | None
    completion_tick: int | None
    unattributed_delivered: float
    delivery_telemetry: dict[str, Any] = field(default_factory=dict)


class ActiveOrder:
    """Deterministic state machine for exactly one open customer order.

    Unlike :class:`ContractEngine` this holds a single committed order whose
    clock starts at activation and closes at fulfillment or deadline expiry.
    It performs no selection, rating, or calibration -- callers own those.
    """

    __slots__ = (
        "item_name",
        "requested_quantity",
        "order_kind",
        "products",
        "deadline_ticks",
        "_activation_tick",
        "_delivered",
        "_unattributed",
        "_credits",
        "_first_delivery_tick",
        "_completion_tick",
        "_status",
        "_terminal_tick",
        "_now",
        "_qualification",
    )

    def __init__(
        self,
        item_name: str,
        requested_quantity: int,
        deadline_ticks: int,
        *,
        activation_tick: int,
        products: list[ProductDemandSpec] | tuple[ProductDemandSpec, ...] | None = None,
        order_kind: str = "one_shot",
    ):
        if requested_quantity <= 0:
            raise ValueError("requested_quantity must be positive")
        if deadline_ticks <= 0:
            raise ValueError("deadline_ticks must be positive")
        lines = tuple(products or (ProductDemandSpec(product=item_name, quantity=float(requested_quantity)),))
        if len(lines) != len({line.product for line in lines}):
            raise ValueError("adaptive order products must be unique")
        if order_kind not in {"one_shot", "sustained"}:
            raise ValueError("order_kind must be one_shot or sustained")
        self.item_name = lines[0].product
        self.requested_quantity = round(sum(line.quantity for line in lines))
        self.order_kind = order_kind
        self.products = lines
        self.deadline_ticks = deadline_ticks
        self._activation_tick = activation_tick
        self._delivered = {line.product: 0.0 for line in lines}
        self._unattributed = {line.product: 0.0 for line in lines}
        self._credits: dict[str, list[tuple[int, float]]] = {
            line.product: [] for line in lines
        }
        self._first_delivery_tick: int | None = None
        self._completion_tick: int | None = None
        self._status: str = "open"
        self._terminal_tick: int | None = None
        self._now: int | None = None
        self._qualification: dict[str, Any] | None = None

    # -- clock ---------------------------------------------------------------

    @property
    def elapsed_ticks(self) -> int:
        endpoint = (
            self._terminal_tick
            if self._terminal_tick is not None
            else (self._now if self._now is not None else self._activation_tick)
        )
        return max(endpoint - self._activation_tick, 0)

    @property
    def remaining_ticks(self) -> int:
        if self._status != "open":
            return 0
        return max(
            self.deadline_ticks
            - ((self._now or self._activation_tick) - self._activation_tick),
            0,
        )

    def sync(self, current_tick: int) -> dict[str, Any] | None:
        """Advance the clock; expires the order once its deadline passes."""

        if self._status != "open":
            return None
        self._now = max(current_tick, self._activation_tick)
        if (current_tick - self._activation_tick) >= self.deadline_ticks:
            complete = self._completion_ratio() >= 1.0 - 1e-9
            self._status = "fulfilled" if complete else "expired"
            self._terminal_tick = self._activation_tick + self.deadline_ticks
            if complete and self._completion_tick is None:
                self._completion_tick = self._terminal_tick
            return {
                "event": ("contract_fulfilled" if complete else "contract_expired"),
                "item": self.item_name,
                "products": [line.product for line in self.products],
                "tick": self._terminal_tick,
            }
        return None

    # -- deliveries ------------------------------------------------------------

    def attribute(
        self, amount: float, tick: int, product: str | None = None
    ) -> dict[str, Any] | None:
        """Credit sink-verified units while the order remains open."""

        product = product or self.item_name
        if product not in self._delivered:
            return None
        if self._status != "open" or amount <= 0:
            if amount > 0 and self._status == "fulfilled":
                self._unattributed[product] += amount
            return None
        # The order closes at its deadline.  Buckets are attributed at their
        # end tick, so a bucket that closes on/after the due boundary is late
        # even if it was opened while the order was active.
        if tick < self._activation_tick or tick >= self._activation_tick + self.deadline_ticks:
            self._unattributed[product] += amount
            return None
        self._now = max(self._now or self._activation_tick, tick)
        requested = next(line.quantity for line in self.products if line.product == product)
        capacity = max(requested - self._delivered[product], 0.0)
        credit = amount if self.order_kind == "sustained" else min(capacity, amount)
        overflow = amount - credit
        if credit <= 1e-9:
            self._unattributed[product] += overflow
            return None
        self._delivered[product] += credit
        self._credits[product].append((tick, credit))
        if self._first_delivery_tick is None:
            self._first_delivery_tick = tick
        event = {
            "event": "contract_progress",
            "item": product,
            "amount": credit,
            "tick": tick,
        }
        if self.order_kind == "one_shot" and self._all_lines_filled():
            self._status = "fulfilled"
            self._completion_tick = tick
            self._terminal_tick = tick
            event["event"] = "contract_fulfilled"
        if overflow > 1e-9:
            self._unattributed[product] += overflow
        return event

    def _all_lines_filled(self) -> bool:
        return all(
            self._delivered[line.product] >= line.quantity - 1e-9
            for line in self.products
        )

    def _completion_ratio(self) -> float:
        if self._qualification is not None:
            return 1.0
        if self.order_kind == "one_shot":
            ratios = [
                min(self._delivered[line.product] / line.quantity, 1.0)
                for line in self.products
            ]
            return sum(ratios) / len(ratios)
        details = _sustained_service_details(
            self.products,
            self._credits,
            start_tick=self._activation_tick,
            deadline_ticks=self.deadline_ticks,
        )
        product_scores = [details[line.product]["score"] for line in self.products]
        return sum(product_scores) / len(product_scores)

    def _delivery_telemetry(self) -> dict[str, Any]:
        """Return raw bucket coverage and service scores for every line."""

        bucket_count = max(1, math.ceil(self.deadline_ticks / DELIVERY_BUCKET_TICKS))
        service = _sustained_service_details(
            self.products,
            self._credits,
            start_tick=self._activation_tick,
            deadline_ticks=self.deadline_ticks,
        )
        lines: dict[str, Any] = {}
        for line in self.products:
            credits = sorted(self._credits[line.product])
            active_buckets = {
                int(tick // DELIVERY_BUCKET_TICKS)
                for tick, amount in credits
                if amount > 0
            }
            line_service = service[line.product]
            lines[line.product] = {
                "requested": float(line.quantity),
                "accepted": round(
                    min(self._delivered[line.product], line.quantity), 6
                ),
                "raw_bucket_count": len(active_buckets),
                "raw_bucket_coverage_ratio": round(
                    len(active_buckets) / bucket_count, 6
                ),
                "slice_scores": line_service["slice_scores"],
                "service_window_count": line_service["window_count"],
                "service_window_quotas": line_service["window_quotas"],
                "sustained_service_score": round(line_service["score"], 6),
            }
        return {
            "bucket_ticks": DELIVERY_BUCKET_TICKS,
            "window_ticks": self.deadline_ticks,
            "lines": lines,
            "autonomous_qualification": self._qualification,
        }

    # -- lifecycle ---------------------------------------------------------

    def abandon(self, tick: int) -> None:
        """Agent-initiated abandonment; recorded verbatim, never a win."""
        if self._status == "open":
            self._now = max(self._now or self._activation_tick, tick)
            self._status = "abandoned"
            self._terminal_tick = tick

    def certify_sustained(self, tick: int, evidence: dict[str, Any]) -> dict[str, Any]:
        """Close a sustained order from a privileged autonomous audit."""

        if self.order_kind != "sustained":
            raise ValueError("Only sustained orders can be audit-certified")
        if self._status != "open":
            raise ValueError("Only an open sustained order can be certified")
        self._now = max(self._now or self._activation_tick, tick)
        self._status = "fulfilled"
        self._completion_tick = tick
        self._terminal_tick = tick
        self._qualification = dict(evidence)
        return {
            "event": "contract_fulfilled",
            "item": self.item_name,
            "products": [line.product for line in self.products],
            "tick": tick,
            "qualification": "autonomous_clone",
        }

    @property
    def status(self) -> str:
        return self._status

    @property
    def delivered(self) -> float:
        return sum(self._delivered.values())

    @property
    def first_delivery_tick(self) -> int | None:
        return self._first_delivery_tick

    @property
    def completion_tick(self) -> int | None:
        return self._completion_tick

    def student_view(self) -> OpenContractView:
        """Student-visible projection: no difficulty or rating internals."""
        return OpenContractView(
            order_id="epoch-order",
            kind=self.order_kind,
            products=list(self.products),
            issued_at_tick=self._activation_tick,
            due_tick=self._activation_tick + self.deadline_ticks,
            grace_ticks=0,
            completion_ratio=round(self._completion_ratio(), 6),
            status=(
                "fulfilled"
                if self._status == "fulfilled"
                else ("open" if self._status == "open" else "expired")
            ),
            fulfilled={
                line.product: round(
                    min(self._delivered[line.product], line.quantity), 4
                )
                for line in self.products
            },
            remaining={
                line.product: round(
                    max(line.quantity - self._delivered[line.product], 0.0), 4
                )
                for line in self.products
            },
        )

    def evaluate(self, terminal_tick: int | None = None) -> ActiveOrderOutcome:
        if terminal_tick is not None:
            tick = terminal_tick
        elif self._terminal_tick is not None:
            tick = self._terminal_tick
        elif self._now is not None:
            tick = self._now
        else:
            tick = self._activation_tick
        ratio = self._completion_ratio()
        status = self._status
        if status == "open":
            status = "fulfilled" if ratio >= 1.0 - 1e-9 else "partial"
        return ActiveOrderOutcome(
            engine_version=ACTIVE_ORDER_ENGINE_VERSION,
            item_name=self.item_name,
            requested_quantity=self.requested_quantity,
            delivered_quantity=sum(self._delivered.values()),
            requested_by_product={
                line.product: float(line.quantity) for line in self.products
            },
            delivered_by_product=dict(self._delivered),
            completion_ratio=ratio,
            status=status,
            activation_tick=self._activation_tick,
            terminal_tick=tick,
            first_delivery_tick=self._first_delivery_tick,
            completion_tick=self._completion_tick,
            unattributed_delivered=sum(self._unattributed.values()),
            delivery_telemetry=self._delivery_telemetry(),
        )


__all__ = [
    "SLICE_TICKS",
    "CUSTOMER_ENGINE_VERSION",
    "ACTIVE_ORDER_ENGINE_VERSION",
    "ActiveOrder",
    "ActiveOrderOutcome",
    "DeliveryBucket",
    "OrderResult",
    "ContractEvaluationResult",
    "ContractEngine",
    "ScheduleConfig",
    "generate_contract_schedule",
    "verify_receipt",
    "success_from_evaluation",
]
