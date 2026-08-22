import pytest

from fle.envd.customer import (
    SLICE_TICKS,
    ContractEngine,
    DeliveryBucket,
    ScheduleConfig,
    generate_contract_schedule,
    success_from_evaluation,
    verify_receipt,
)
from fle.envd.models import (
    CUSTOMER_GENERATOR_VERSION,
    CustomerContractSpec,
    DemandOrderSpec,
    FactorioTaskSpec,
    ProductDemandSpec,
)

pytestmark = pytest.mark.no_factorio


def _one_shot(
    order_id="o1",
    product="iron-plate",
    quantity=100,
    issue=0,
    due=3600,
    grace=0,
):
    return DemandOrderSpec(
        order_id=order_id,
        kind="one_shot",
        products=[ProductDemandSpec(product=product, quantity=float(quantity))],
        issue_tick=issue,
        due_tick=due,
        grace_ticks=grace,
    )


def _spec(orders, **kwargs):
    return CustomerContractSpec(
        generator_version=CUSTOMER_GENERATOR_VERSION, orders=orders, **kwargs
    )


# ---------------------------------------------------------------------------
# Schedule generation
# ---------------------------------------------------------------------------


def test_schedule_generation_is_deterministic():
    config = ScheduleConfig(horizon_ticks=720000, difficulty=0.5)
    first = generate_contract_schedule(config, seed=1234)
    second = generate_contract_schedule(config, seed=1234)
    assert first.model_dump() == second.model_dump()
    assert first.commitment == second.commitment


def test_schedule_seed_changes_the_stream():
    config = ScheduleConfig(horizon_ticks=720000, difficulty=0.5)
    first = generate_contract_schedule(config, seed=1)
    second = generate_contract_schedule(config, seed=2)
    assert first.model_dump() != second.model_dump()


def test_generated_orders_are_chronological_and_valid():
    config = ScheduleConfig(
        horizon_ticks=1440000, difficulty=0.7, order_count=8
    )
    spec = generate_contract_schedule(config, seed=99)
    issues = [order.issue_tick for order in spec.orders]
    assert issues == sorted(issues)
    for order in spec.orders:
        assert order.due_tick > order.issue_tick
        assert order.products
        assert all(p.quantity > 0 for p in order.products)


def test_commitment_binds_order_content():
    base = _spec([_one_shot()])
    mutated_orders = [_one_shot(quantity=101)]
    other = _spec(mutated_orders)
    assert base.commitment != other.commitment


def test_task_fingerprint_includes_customer_spec():
    plain = FactorioTaskSpec(task_id="t", goal="g")
    contracted = plain.model_copy(update={})
    contracted_with_customer = FactorioTaskSpec(
        task_id="t", goal="g", customer=_spec([_one_shot()])
    )
    assert contracted.fingerprint != contracted_with_customer.fingerprint
    with pytest.raises(ValueError):
        plain.model_validate(
            plain.model_dump() | {"customer": {"orders": []}}
        )


# ---------------------------------------------------------------------------
# Reveal semantics (no future leakage)
# ---------------------------------------------------------------------------


def test_pending_orders_are_hidden_from_students():
    future = _one_shot("future", issue=10000, due=20000)
    engine = ContractEngine(_spec([future]))
    assert engine.student_view() == []
    events = engine.sync(9999, [])
    assert engine.student_view() == []
    assert events == []


def test_orders_reveal_at_issue_tick():
    order = _one_shot("now", issue=500, due=5000)
    engine = ContractEngine(_spec([order]))
    engine.sync(499, [])
    assert engine.student_view() == []
    engine.sync(500, [])
    views = engine.student_view()
    assert len(views) == 1
    assert views[0].status == "open"
    assert views[0].due_tick == 5000


def test_view_exposes_no_penalty_or_verifier_internals():
    spec = _spec([_one_shot()], lateness_penalty_weight=3.5)
    order = spec.orders[0]
    engine = ContractEngine(spec)
    engine.sync(order.issue_tick, [])
    payload = engine.student_view()[0].model_dump()
    assert "lateness_penalty_weight" not in payload
    assert "weight" not in payload
    assert "commitment" not in payload


# ---------------------------------------------------------------------------
# Attribution and one-shot fulfillment
# ---------------------------------------------------------------------------


def test_one_shot_full_and_partial_fulfillment():
    spec = _spec([_one_shot("a", quantity=100)])
    engine = ContractEngine(spec)
    engine.sync(10, [DeliveryBucket(start_tick=0, items={"iron-plate": 60})])
    result = engine.evaluate(100)
    assert result.order_results[0].ratio == pytest.approx(0.6)

    engine_two = ContractEngine(_spec([_one_shot("b", quantity=100)]))
    engine_two.sync(10, [DeliveryBucket(start_tick=0, items={"iron-plate": 100})])
    full = engine_two.evaluate(100)
    assert full.order_results[0].ratio == pytest.approx(1.0)
    assert full.aggregate_ratio == pytest.approx(1.0)


def test_deliveries_before_issue_are_unattributed():
    order = _one_shot("late", issue=600, due=6000)
    engine = ContractEngine(_spec([order]))
    engine.sync(700, [DeliveryBucket(start_tick=0, items={"iron-plate": 50})])
    engine.sync(800, [DeliveryBucket(start_tick=600, items={"iron-plate": 40})])
    result = engine.evaluate(900)
    assert result.order_results[0].accepted["iron-plate"] == pytest.approx(40)
    assert result.unattributed["iron-plate"] == pytest.approx(50)


def test_fifo_attribution_across_overlapping_orders():
    first = _one_shot("first", quantity=50, issue=0, due=100000)
    second = _one_shot("second", quantity=50, issue=0, due=100000)
    engine = ContractEngine(_spec([first, second]))
    engine.sync(10, [DeliveryBucket(start_tick=0, items={"iron-plate": 80})])
    results = {r.order_id: r for r in engine.evaluate(20).order_results}
    assert results["first"].accepted["iron-plate"] == pytest.approx(50)
    assert results["second"].accepted["iron-plate"] == pytest.approx(30)
    assert results["second"].ratio == pytest.approx(0.6)


def test_overflow_spills_to_later_order_after_cap():
    first = _one_shot("first", quantity=50, issue=0, due=100000)
    second = _one_shot("second", quantity=10, issue=0, due=100000)
    engine = ContractEngine(_spec([first, second]))
    engine.sync(10, [DeliveryBucket(start_tick=0, items={"iron-plate": 55})])
    results = {r.order_id: r for r in engine.evaluate(20).order_results}
    assert results["first"].accepted["iron-plate"] == pytest.approx(50)
    assert results["second"].accepted["iron-plate"] == pytest.approx(5)


def test_expired_order_stops_absorbing_and_late_items_void():
    order = _one_shot("tight", quantity=100, issue=0, due=1000, grace=100)
    spec = _spec([order])
    engine = ContractEngine(spec)
    engine.sync(500, [DeliveryBucket(start_tick=0, items={"iron-plate": 40})])
    engine.sync(1200, [DeliveryBucket(start_tick=1100, items={"iron-plate": 90})])
    result = engine.evaluate(1300)
    tight = result.order_results[0]
    assert tight.status == "expired"
    assert tight.accepted["iron-plate"] == pytest.approx(40)
    assert result.unattributed["iron-plate"] == pytest.approx(90)


# ---------------------------------------------------------------------------
# Sustained-rate scoring
# ---------------------------------------------------------------------------

SUSTAINED_WINDOW = SLICE_TICKS * 4


def _sustained(quantity_total):
    return DemandOrderSpec(
        order_id="sus",
        kind="sustained",
        products=[
            ProductDemandSpec(product="copper-cable", quantity=float(quantity_total))
        ],
        issue_tick=0,
        due_tick=SUSTAINED_WINDOW,
    )


def test_steady_supply_beats_burst_for_sustained_orders():
    total = 400
    steady_engine = ContractEngine(_spec([_sustained(total)]))
    for index in range(4):
        steady_engine.sync(
            index * SLICE_TICKS + 10,
            [
                DeliveryBucket(
                    start_tick=index * SLICE_TICKS,
                    items={"copper-cable": 100},
                )
            ],
        )
    steady = steady_engine.evaluate(SUSTAINED_WINDOW + 1)

    burst_engine = ContractEngine(_spec([_sustained(total)]))
    burst_engine.sync(
        10, [DeliveryBucket(start_tick=0, items={"copper-cable": 400})]
    )
    burst = burst_engine.evaluate(SUSTAINED_WINDOW + 1)

    assert steady.order_results[0].ratio == pytest.approx(1.0)
    assert burst.order_results[0].ratio < steady.order_results[0].ratio
    assert burst.order_results[0].ratio == pytest.approx(0.25)


def test_partial_sustained_delivery_scores_fractionally():
    engine = ContractEngine(_spec([_sustained(400)]))
    engine.sync(10, [DeliveryBucket(start_tick=0, items={"copper-cable": 150})])
    result = engine.evaluate(SUSTAINED_WINDOW + 1)
    # First slice fully met (1.0), remaining three slices empty.
    assert result.order_results[0].ratio == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# Reward integral and penalties
# ---------------------------------------------------------------------------


def test_reward_integral_weights_and_lateness_penalty():
    good = _one_shot("good", quantity=100, issue=0, due=1000)
    bad = _one_shot(
        "bad",
        product="steel-plate",
        quantity=100,
        issue=0,
        due=1000,
    )
    bad = bad.model_copy(
        update={"weight": 3.0}
    )
    spec = _spec([good, bad], lateness_penalty_weight=0.5)
    engine = ContractEngine(spec)
    engine.sync(
        100,
        [
            DeliveryBucket(
                start_tick=0, items={"iron-plate": 100, "steel-plate": 25}
            )
        ],
    )
    result = engine.evaluate(2000)
    assert result.order_results[0].ratio == pytest.approx(1.0)
    assert result.order_results[1].ratio == pytest.approx(0.25)
    # R = sum(w*r)/sum(w) - lambda * sum(w*(1-r))/sum(w)
    expected_net = ((1.0 * 1.0) + (3.0 * 0.25)) / 4.0 - 0.5 * (
        (0.0 * 1.0) + (3.0 * 0.75)
    ) / 4.0
    assert result.net_reward == pytest.approx(expected_net)
    assert result.penalty == pytest.approx(0.5 * (3.0 * 0.75) / 4.0)


def test_unrevealed_orders_do_not_dilute_the_integral():
    issued = _one_shot("issued", quantity=100, issue=0, due=100000)
    future = _one_shot(
        "future", product="steel-plate", quantity=100, issue=500000, due=600000
    )
    spec = _spec([issued, future])
    engine = ContractEngine(spec)
    engine.sync(10, [DeliveryBucket(start_tick=0, items={"iron-plate": 100})])
    result = engine.evaluate(2000)
    assert result.aggregate_ratio == pytest.approx(1.0)
    assert [r.order_id for r in result.order_results] == ["issued"]
    assert success_from_evaluation(result, spec) is True


def test_success_requires_all_required_orders_met():
    met = _one_shot("met", quantity=100)
    unmet = _one_shot("unmet", product="steel-plate", quantity=100)
    spec = _spec([met, unmet], success_ratio=1.0)
    engine = ContractEngine(spec)
    engine.sync(
        10, [DeliveryBucket(start_tick=0, items={"iron-plate": 100})]
    )
    result = engine.evaluate(2000)
    assert success_from_evaluation(result, spec) is False

    engine.sync(
        30, [DeliveryBucket(start_tick=0, items={"steel-plate": 100})]
    )
    result = engine.evaluate(2000)
    assert success_from_evaluation(result, spec) is True


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------


def test_receipt_signs_and_verifies():
    import hashlib

    key = b"unit-test-key"
    spec = _spec([_one_shot("r1", quantity=10)], receipt_key_env="UNUSED")
    engine = ContractEngine(spec)
    engine.sync(10, [DeliveryBucket(start_tick=0, items={"iron-plate": 10})])
    result = engine.evaluate(100, signing_key=key)
    assert verify_receipt(result.receipt, result.receipt_mac, key)
    tampered = dict(result.receipt)
    tampered["aggregate_ratio"] = 0.42
    assert not verify_receipt(tampered, result.receipt_mac, key)
    digest = hashlib.sha256(b"x").hexdigest()[:8]
    assert len(result.receipt_mac) == 64 and digest != result.receipt_mac


# ---------------------------------------------------------------------------
# Engine clock edge cases
# ---------------------------------------------------------------------------


def test_sync_is_idempotent_on_repeated_ticks():
    spec = _spec([_one_shot("idem", quantity=10)])
    engine = ContractEngine(spec)
    buckets = [DeliveryBucket(start_tick=0, items={"iron-plate": 10})]
    first_events = engine.sync(50, list(buckets))
    second_events = engine.sync(50, [])
    result = engine.evaluate(100)
    assert result.order_results[0].ratio == pytest.approx(1.0)
    assert any(e["event"] == "contract_issued" for e in first_events)
    assert second_events == []


def test_mixed_products_score_per_product():
    order = DemandOrderSpec(
        order_id="mix",
        kind="one_shot",
        products=[
            ProductDemandSpec(product="iron-plate", quantity=100),
            ProductDemandSpec(product="gear", quantity=50),
        ],
        issue_tick=0,
        due_tick=10000,
    )
    engine = ContractEngine(_spec([order]))
    engine.sync(
        10,
        [
            DeliveryBucket(
                start_tick=0, items={"iron-plate": 100, "gear": 25}
            )
        ],
    )
    result = engine.evaluate(20000)
    mix = result.order_results[0]
    assert mix.accepted["gear"] == pytest.approx(25)
    assert mix.ratio == pytest.approx((1.0 + 0.5) / 2)
