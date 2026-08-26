"""Golden-value and property tests for the rating layer (section 12)."""

import math

import pytest

from fle.envd.contract_rating import (
    CalibratedDifficultyModel,
    OutcomeThresholds,
    TrueskillContractRater,
    UncalibratedDifficultyModel,
    contract_uncertainty,
    map_outcome,
)
from fle.envd.models import (
    CalibrationManifest,
    ContractDifficultyFeatures,
    ContractEpochOutcome,
)

pytestmark = pytest.mark.no_factorio


@pytest.fixture(scope="module")
def rater() -> TrueskillContractRater:
    return TrueskillContractRater()


def _outcome(**overrides) -> ContractEpochOutcome:
    fields = dict(
        session_id="s",
        epoch_index=1,
        commitment_hash="h" * 64,
        status="partial",
        delivered_quantity=50,
        requested_quantity=100,
        completion_ratio=0.5,
        simulation_ticks_used=1000,
        interventions_used=3,
        model_seconds=1.0,
        tool_seconds=1.0,
        runner_wall_seconds=2.0,
        terminal_state_digest="d",
    )
    fields.update(overrides)
    return ContractEpochOutcome(**fields)


# ---------------------------------------------------------------------------
# Golden values against pinned trueskill==0.4.5
# ---------------------------------------------------------------------------


def test_golden_values_against_pinned_reference(rater):
    """Constants derived from trueskill==0.4.5 defaults; upstream drift or a
    wrapper wiring mistake breaks these."""
    initial = rater.initial_rating()
    assert initial.mu == pytest.approx(0.0)
    assert initial.sigma == pytest.approx(2.0)

    win = rater.update(initial, 0.0, 0.5, "win")
    loss = rater.update(initial, 0.0, 0.5, "loss")
    draw = rater.update(initial, 0.0, 0.5, "draw")
    assert win.mu == pytest.approx(1.349991, abs=1e-4)
    assert win.sigma == pytest.approx(1.527075, abs=1e-4)
    assert loss.mu == pytest.approx(-1.349991, abs=1e-4)
    assert draw.mu == pytest.approx(0.0, abs=1e-4)
    assert draw.sigma == pytest.approx(1.201997, abs=1e-4)


# ---------------------------------------------------------------------------
# Directional properties
# ---------------------------------------------------------------------------


def test_win_raises_and_loss_lowers_mu(rater):
    initial = rater.initial_rating()
    win = rater.update(initial, 1.0, 0.5, "win")
    loss = rater.update(initial, -1.0, 0.5, "loss")
    assert win.mu > initial.mu > loss.mu
    assert win.conservative_score == pytest.approx(win.mu - 3 * win.sigma, rel=1e-6)


def test_draw_keeps_symmetric_means(rater):
    initial_a = rater.initial_rating()
    draw = rater.update(initial_a, 0.0, 0.5, "draw")
    assert draw.mu == pytest.approx(initial_a.mu, abs=0.35)
    assert draw.sigma < initial_a.sigma  # still learned something


def test_near_rated_contracts_reduce_uncertainty_more(rater):
    """Expected-outcome matches: near contracts inform; lopsided ones don't."""
    initial = rater.initial_rating()
    near = rater.update(initial, 0.5, 0.5, "win")  # close match
    far = rater.update(initial, -8.0, 0.5, "win")  # foregone conclusion
    assert near.sigma < far.sigma


def test_uncertain_contracts_produce_smaller_updates(rater):
    initial = rater.initial_rating()
    certain = rater.update(initial, 0.0, 0.3, "win")
    uncertain = rater.update(initial, 0.0, 4.0, "win")
    assert abs(uncertain.mu - initial.mu) < abs(certain.mu - initial.mu)


def test_finite_nonnegative_sigma_after_1000_updates(rater):
    current = rater.initial_rating()
    for _ in range(1000):
        current = rater.update(current, 0.0, 0.7, "draw")
    assert math.isfinite(current.mu)
    assert math.isfinite(current.sigma)
    assert current.sigma >= 0.0
    assert current.rated_epoch_count == 1000


def test_rating_never_leaks_package_types(rater):
    update = rater.update(rater.initial_rating(), 0.0, 0.5, "win")
    payload = update.model_dump(mode="json")
    assert set(payload) == {
        "model_version",
        "mu",
        "sigma",
        "conservative_score",
        "rated_epoch_count",
    }
    assert all(isinstance(v, (str, int, float)) for v in payload.values())


# ---------------------------------------------------------------------------
# Outcome mapping (section 11)
# ---------------------------------------------------------------------------


def test_map_outcome_threshold_bands():
    thresholds = OutcomeThresholds(partial_floor=0.25, partial_ceiling=0.90)

    def at(ratio, status="partial"):
        return _outcome(completion_ratio=ratio, status=status)

    assert map_outcome(at(1.0, status="fulfilled")) == "win"
    assert map_outcome(at(0.95), thresholds) == "draw"
    assert map_outcome(at(0.90), thresholds) == "draw"
    assert map_outcome(at(0.50), thresholds) == "draw"
    assert map_outcome(at(0.26), thresholds) == "draw"
    assert map_outcome(at(0.25), thresholds) == "loss"
    assert map_outcome(at(0.10), thresholds) == "loss"
    assert map_outcome(at(0.0, status="expired")) == "loss"
    assert map_outcome(_outcome(status="abandoned")) == "loss"
    assert map_outcome(_outcome(status="infrastructure_error")) is None
    assert map_outcome(_outcome(status="invalid")) is None


def test_invalid_threshold_configuration_rejected():
    with pytest.raises(ValueError):
        OutcomeThresholds(partial_floor=0.9, partial_ceiling=0.25)


# ---------------------------------------------------------------------------
# Difficulty models (section 10)
# ---------------------------------------------------------------------------


def _features(**overrides) -> ContractDifficultyFeatures:
    fields = dict(
        product_id="electronic-circuit",
        product_tier=1,
        recipe_depth=3,
        missing_technology_count=0,
        missing_machine_type_count=0,
        required_new_intermediate_count=1,
        log_quantity=6.0,
        deadline_ticks=36000,
        required_rate_per_minute=60.0,
        existing_rate_per_minute=30.0,
        inventory_coverage_ratio=0.1,
        estimated_power_fraction=0.2,
        transport_complexity=0.25,
        stage_band=1,
    )
    fields.update(overrides)
    return ContractDifficultyFeatures(**fields)


def test_uncalibrated_model_monotone_in_missing_prerequisites():
    model = UncalibratedDifficultyModel()
    easy = model.evaluate(_features())
    harder = model.evaluate(
        _features(missing_technology_count=2, missing_machine_type_count=1)
    )
    assert harder[0] > easy[0]  # raw difficulty rises
    assert harder[2] > easy[2]  # effective difficulty rises


def test_state_advantage_reduces_effective_difficulty():
    model = UncalibratedDifficultyModel()
    no_supply = model.evaluate(_features(existing_rate_per_minute=0.0))
    supplied = model.evaluate(_features(existing_rate_per_minute=120.0))
    assert supplied[2] < no_supply[2]

    bare = model.evaluate(_features(inventory_coverage_ratio=0.0))
    stocked = model.evaluate(_features(inventory_coverage_ratio=0.9))
    assert stocked[2] < bare[2]


def test_uncalibrated_model_monotone_in_quantity():
    model = UncalibratedDifficultyModel()
    easy = model.evaluate(_features(log_quantity=4.0))
    harder = model.evaluate(_features(log_quantity=8.0))
    assert harder[0] > easy[0]
    assert harder[2] > easy[2]


def test_advantage_never_adds_difficulty():
    model = UncalibratedDifficultyModel()
    for coverage in (-5.0, 0.0, 0.5, 2.0):
        _, advantage, effective = model.evaluate(
            _features(inventory_coverage_ratio=coverage)
        )
        assert advantage >= 0.0


def _manifest() -> CalibrationManifest:
    return CalibrationManifest(
        calibration_version="cal-test",
        benchmark_version="bv-test",
        training_data_sha256="0" * 64,
        game_versions=("2.0.73",),
        template_bank_version="tb-v1",
        partial_floor=0.25,
        partial_ceiling=0.90,
        template_intercepts={"template:electronic-circuit": 1.5},
        beta_raw={"recipe_depth": 0.5, "log_quantity": 0.1},
        beta_state={"inventory_coverage_ratio": -0.8},
        normalization={
            "recipe_depth": (3.0, 1.5),
            "log_quantity": (6.0, 1.0),
            "inventory_coverage_ratio": (0.2, 0.3),
        },
        clipping={},
        supported_ranges={"recipe_depth": (0.0, 6.0)},
        accepted=True,
    )


def test_calibrated_model_applies_manifest_terms():
    model = CalibratedDifficultyModel(_manifest())
    features = _features(recipe_depth=6)  # normalized (6-3)/1.5 = +2 sd
    raw, advantage, effective = model.evaluate(features)
    assert raw == pytest.approx(
        1.5 + 0.5 * 2.0 + 0.1 * 0.0,  # intercept + depth term only
        abs=1e-3,
    )


def test_calibrated_model_accepts_committed_template_identity():
    manifest = _manifest().model_copy(
        update={"template_intercepts": {"template:t-circuits": 4.0}}
    )
    model = CalibratedDifficultyModel(manifest)
    raw, _, _ = model.evaluate(_features(), template_id="t-circuits")
    assert raw == pytest.approx(4.0 + 0.5 * 0.0 + 0.1 * 0.0, abs=1e-3)


def test_extrapolation_distance_and_flagging():
    model = CalibratedDifficultyModel(_manifest())
    inside = _features(recipe_depth=4)
    outside = _features(recipe_depth=12)
    assert model.extrapolation_distance(inside) == 0.0
    assert model.extrapolation_distance(outside) > 0.0
    assert model.out_of_envelope(outside)
    assert not model.out_of_envelope(inside)


def test_contract_uncertainty_grows_with_extrapolation():
    manifest = _manifest()
    inside = _features(recipe_depth=4)
    outside = _features(recipe_depth=12)
    sigma_inside = contract_uncertainty(manifest=manifest, features=inside)
    sigma_outside = contract_uncertainty(manifest=manifest, features=outside)
    uncalibrated = contract_uncertainty(manifest=None, features=None)
    assert sigma_inside < sigma_outside
    assert uncalibrated > sigma_inside  # honest wide prior pre-calibration
