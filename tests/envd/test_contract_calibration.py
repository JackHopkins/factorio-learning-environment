"""Statistical tests: grouped splits, parameter recovery, manifests (§16)."""

import math
import random
import statistics

import pytest

from fle.envd.contract_calibration import (
    CalibrationRecord,
    build_manifest,
    controlled_monotonicity_checks,
    fit_contextual_model,
    feature_row,
    grouped_split,
    heldout_metrics,
)
from fle.envd.models import CalibrationManifest, ContractDifficultyFeatures

pytestmark = pytest.mark.no_factorio


def _features(**overrides) -> ContractDifficultyFeatures:
    fields = dict(
        product_id="iron-plate",
        product_tier=0,
        recipe_depth=1,
        missing_technology_count=0,
        missing_machine_type_count=0,
        required_new_intermediate_count=0,
        log_quantity=5.0,
        deadline_ticks=36000,
        required_rate_per_minute=50.0,
        existing_rate_per_minute=10.0,
        inventory_coverage_ratio=0.1,
        estimated_power_fraction=0.2,
        transport_complexity=0.25,
        stage_band=1,
    )
    fields.update(overrides)
    return ContractDifficultyFeatures(**fields)


def _synthetic_records(
    n_per_participant: int = 60,
    seed: int = 11,
) -> list[CalibrationRecord]:
    """Ordinal-probit generator matching the fitted model structure."""
    rng = random.Random(seed)
    normal = statistics.NormalDist()
    true_ability = {"p_strong": 2.5, "p_mid": 0.5, "p_weak": -1.5}
    records: list[CalibrationRecord] = []
    for participant, ability in true_ability.items():
        for i in range(n_per_participant):
            depth = rng.randint(0, 4)
            quantity_log = rng.uniform(3.0, 8.0)
            rate = rng.uniform(20.0, 200.0)
            difficulty = 0.5 * depth + 0.15 * (quantity_log - 5.0) + 0.004 * rate
            margin = ability - difficulty + normal.inv_cdf(rng.random())
            if margin > 0.5:
                result = "win"
            elif margin < -0.5:
                result = "loss"
            else:
                result = "draw"
            records.append(
                CalibrationRecord(
                    participant_id=participant,
                    factory_seed=i % 3,
                    template_id="t-consolidate",
                    generation_seed=rng.randrange(10**9),
                    stage_band=1,
                    features=_features(
                        recipe_depth=depth,
                        log_quantity=quantity_log,
                        required_rate_per_minute=rate,
                    ),
                    result=result,
                    completion_ratio={"win": 1.0, "draw": 0.5, "loss": 0.1}[result],
                    simulation_ticks_used=1000,
                    interventions_used=3,
                )
            )
    return records


# ---------------------------------------------------------------------------
# Grouped splits
# ---------------------------------------------------------------------------


def test_grouped_split_never_splits_a_group():
    records = _synthetic_records(seed=3)
    train, test = grouped_split(records, holdout_fraction=0.25)
    assert train and test
    train_groups = {(r.factory_seed, r.participant_id) for r in train}
    test_groups = {(r.factory_seed, r.participant_id) for r in test}
    assert not (train_groups & test_groups), "group leaked across the split"


def test_fit_requires_minimum_records():
    with pytest.raises(ValueError):
        fit_contextual_model(_synthetic_records()[:4])


# ---------------------------------------------------------------------------
# Parameter recovery
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def fitted():
    records = _synthetic_records()
    train, _test = grouped_split(records, holdout_fraction=0.2)
    outcome = fit_contextual_model(train)
    return outcome


def test_ability_rank_ordering_recovered(fitted):
    design = fitted.design
    abilities = {
        participant: float(fitted.view["abilities"][index])
        for participant, index in design.participant_index.items()
    }
    ordering = sorted(abilities, key=abilities.get)
    assert ordering == ["p_weak", "p_mid", "p_strong"]


def test_difficulty_coefficient_signs_recovered(fitted):
    """Difficulty-increasing features carry positive raw coefficients."""
    design = fitted.design
    betas = dict(zip(design.raw_keys, fitted.view["beta_raw"]))
    assert betas["recipe_depth"] > 0.05
    assert betas["supply_pressure_ratio"] >= -0.01


def test_heldout_metrics_beat_chance(fitted):
    metrics = heldout_metrics([], fitted)
    # Chance Brier for ~balanced outcomes is ~0.25; a sane fit beats it.
    assert metrics["brier"] < 0.30
    assert metrics["reliability_slope"] > 0.0
    assert math.isfinite(metrics["win_logloss"])


def test_heldout_metrics_use_supplied_records(fitted):
    records = _synthetic_records(n_per_participant=4, seed=91)
    metrics = heldout_metrics(records, fitted)
    assert metrics["records"] == len(records)


def test_controlled_monotonicity_gates_pass(fitted):
    checks = controlled_monotonicity_checks(fitted, _features())
    assert checks["quantity_increase_reduces_win"]
    assert checks["rate_pressure_reduces_win"]


# ---------------------------------------------------------------------------
# Manifests
# ---------------------------------------------------------------------------


def test_manifest_contains_frozen_policy(fitted):
    manifest = build_manifest(
        fit=fitted,
        benchmark_version="bv-test",
        game_versions=("2.0.73",),
        training_records=_synthetic_records(),
        implementation_commit="deadbeef",
    )
    assert isinstance(manifest, CalibrationManifest)
    assert manifest.calibration_version.startswith("calibration-")
    assert len(manifest.training_data_sha256) == 64
    assert manifest.template_intercepts
    assert "recipe_depth" in manifest.beta_raw
    assert manifest.normalization
    assert manifest.supported_ranges
    # Ranges are published in raw feature units, not normalized z-scores.
    low, high = manifest.supported_ranges["recipe_depth"]
    assert low <= 0.0 and high >= 4.0
    assert manifest.implementation_commit == "deadbeef"
    assert manifest.accepted is False  # gates must be evaluated explicitly


def test_feature_row_separates_raw_and_state():
    raw, state = feature_row(_features(required_rate_per_minute=90.0))
    assert raw["supply_pressure_ratio"] == pytest.approx(9.0, rel=1e-6)
    assert state == {"inventory_coverage_ratio": pytest.approx(0.1)}
    assert "supply_pressure_ratio" not in state


def test_anchor_centering_fixes_location():
    from fle.envd.contract_calibration import DesignMatrix, _Model, _fix_identifiability
    import numpy as np

    records = _synthetic_records(n_per_participant=12, seed=5)
    design = DesignMatrix(records)
    model = _Model(design, fit_threshold=False)
    params = np.zeros(model.packed_size())
    params[: model.n_participants] = [5.0, 2.0, 8.0][: model.n_participants]
    _fix_identifiability(model, params)
    view = model.unpack(params)
    anchor_mean = float(
        np.mean(
            [
                view["abilities"][design.participant_index[p]]
                for p in ("p_strong", "p_mid", "p_weak")
            ]
        )
    )
    assert anchor_mean == pytest.approx(0.0, abs=1e-9)


def test_anchor_centering_preserves_fitted_margins():
    from fle.envd.contract_calibration import DesignMatrix, _Model, _fix_identifiability
    import numpy as np

    design = DesignMatrix(_synthetic_records(n_per_participant=12, seed=7))
    model = _Model(design, fit_threshold=False)
    params = np.zeros(model.packed_size())
    params[: model.n_participants] = [5.0, 2.0, 8.0][: model.n_participants]
    params[model.n_participants : model.n_participants + model.n_templates] = 1.25
    before = model.margins(model.unpack(params)).copy()
    _fix_identifiability(model, params)
    after = model.margins(model.unpack(params))
    assert np.allclose(before, after)


def test_manifest_threshold_validation():
    with pytest.raises(ValueError):
        CalibrationManifest(
            calibration_version="bad",
            benchmark_version="bv",
            training_data_sha256="0" * 64,
            game_versions=("2.0.73",),
            template_bank_version="tb",
            partial_floor=0.95,
            partial_ceiling=0.90,
            template_intercepts={},
            beta_raw={},
            beta_state={},
            normalization={},
            clipping={},
            supported_ranges={},
        )
