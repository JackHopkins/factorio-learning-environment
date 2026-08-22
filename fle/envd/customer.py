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
# Width of the sink-side delivery aggregation window.  Must match BUCKET_TICKS
# in fle/env/tools/admin/customer_depot/server.lua.  A bucket is attributed at
# its END tick: deliveries count only toward orders already open when the
# bucket closes, which can under-credit by at most one bucket but never grants
# credit before physical delivery.
DELIVERY_BUCKET_TICKS = 60
CUSTOMER_ENGINE_VERSION = "customer-engine-v1"


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
    "uranium-rounds-magazine": {"tier": 2, "family": "military", "qty": 600, "rate": 60},
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


def _quantity(rng: random.Random, entry: dict[str, Any], config: ScheduleConfig) -> float:
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
            weights_.append(_TIER_WEIGHTS.get(entry["tier"], (1.0,))[
                min(tier_bias, len(_TIER_WEIGHTS.get(entry["tier"], (1.0,))) - 1)
            ])
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
                complete = all(
                    state.fulfilled.get(p.product, 0.0) >= p.quantity - 1e-9
                    for p in spec.products
                )
                state.status = "fulfilled" if complete else "expired"
                if state.completion_tick is None and complete:
                    state.completion_tick = spec.close_tick
                events.append(
                    {
                        "event": (
                            "contract_fulfilled"
                            if complete
                            else "contract_expired"
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
                capacity = self._absorb_capacity(state, product)
                if capacity <= 1e-9:
                    continue
                credit = min(capacity, remaining)
                state.absorbed[product] = state.absorbed.get(product, 0.0) + credit
                state.fulfilled[product] = (
                    state.fulfilled.get(product, 0.0) + credit
                )
                state.credits.setdefault(product, []).append((tick, credit))
                remaining -= credit
                if self._order_complete(state):
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
                    fulfilled={
                        p.product: round(state.fulfilled.get(p.product, 0.0), 4)
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
        total_score = 0.0
        for product in spec.products:
            credits = sorted(state.credits.get(product.product, []))
            slice_count = max(1, math.ceil(window / SLICE_TICKS))
            per_slice_requested = product.quantity * SLICE_TICKS / window
            product_score = 0.0
            for index in range(slice_count):
                slice_start = spec.issue_tick + index * SLICE_TICKS
                slice_end = slice_start + SLICE_TICKS
                delivered = sum(
                    qty for tick, qty in credits if slice_start <= tick < slice_end
                )
                slice_len = min(SLICE_TICKS, max(spec.due_tick - slice_start, 0))
                if slice_len <= 0:
                    continue
                slice_ratio = (
                    min(1.0, delivered / per_slice_requested)
                    if per_slice_requested > 0
                    else 1.0
                )
                product_score += slice_ratio * (slice_len / window)
            total_score += product_score
        return total_score / len(spec.products) if spec.products else 1.0

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
                        p.product: min(
                            state.fulfilled.get(p.product, 0.0), p.quantity
                        )
                        for p in spec.products
                    },
                    ratio=ratio,
                    lateness_penalty=lateness,
                    completion_tick=state.completion_tick,
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
            net_reward=(weighted_ratio - self.spec.lateness_penalty_weight * weighted_penalty)
            / total_weight
            if total_weight
            else 0.0,
            unattributed=dict(self._unattributed),
            receipt=receipt_payload,
            receipt_mac=mac,
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


def verify_receipt(
    payload: dict[str, Any], mac: str, key: bytes
) -> bool:
    return hmac.compare_digest(_sign_payload(payload, key), mac)


def success_from_evaluation(
    result: ContractEvaluationResult, spec: CustomerContractSpec
) -> bool:
    required_results = [r for r in result.order_results if r.required]
    if not required_results:
        return True
    per_order = all(r.ratio + 1e-9 >= _order_success_floor(spec) for r in required_results)
    return per_order and result.aggregate_ratio + 1e-9 >= spec.success_ratio


def _order_success_floor(spec: CustomerContractSpec) -> float:
    # Required orders must be fully met unless the aggregate threshold was
    # explicitly relaxed below 1.0, in which case orders may miss by the
    # complementary margin.
    return min(1.0, spec.success_ratio)


__all__ = [
    "SLICE_TICKS",
    "CUSTOMER_ENGINE_VERSION",
    "DeliveryBucket",
    "OrderResult",
    "ContractEvaluationResult",
    "ContractEngine",
    "ScheduleConfig",
    "generate_contract_schedule",
    "verify_receipt",
    "success_from_evaluation",
]
