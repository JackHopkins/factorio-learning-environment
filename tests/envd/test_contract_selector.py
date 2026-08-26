"""Selector scoring and seeded-selection tests (section 13)."""

import pytest

from fle.envd.contract_generator import ContractCandidate
from fle.envd.contract_rating import TrueskillContractRater
from fle.envd.contract_selector import (
    ContractSelector,
    SelectionError,
    SelectionHistory,
    expected_information_gain,
)
from fle.envd.models import (
    CapabilityRating,
    ContractDifficultyFeatures,
    SelectorWeights,
)

pytestmark = pytest.mark.no_factorio


@pytest.fixture(scope="module")
def rating() -> CapabilityRating:
    return TrueskillContractRater().initial_rating()


def _features(**overrides) -> ContractDifficultyFeatures:
    fields = dict(
        product_id="iron-plate",
        product_tier=0,
        recipe_depth=1,
        missing_technology_count=0,
        missing_machine_type_count=0,
        required_new_intermediate_count=0,
        log_quantity=6.0,
        deadline_ticks=36000,
        required_rate_per_minute=60.0,
        existing_rate_per_minute=10.0,
        inventory_coverage_ratio=0.1,
        estimated_power_fraction=0.1,
        transport_complexity=0.0,
        stage_band=1,
    )
    fields.update(overrides)
    return ContractDifficultyFeatures(**fields)


def _candidate(
    item="iron-plate", effective=1.0, stage_band=1, **feature_overrides
) -> ContractCandidate:
    return ContractCandidate(
        template_id="t",
        mixture_class="consolidation",
        generation_seed=1,
        item_name=item,
        quantity=100,
        deadline_ticks=36000,
        analytic_minimum_ticks=600,
        features=_features(stage_band=stage_band, **feature_overrides),
        raw_difficulty=effective + 1.0,
        state_advantage=1.0,
        effective_difficulty=effective,
        family="smelting",
    )


# ---------------------------------------------------------------------------
# Information gain shape
# ---------------------------------------------------------------------------


def test_information_gain_peaks_at_the_posterior_mean(rating):
    at_mean = expected_information_gain(rating, 0.0, 0.5)
    near = expected_information_gain(rating, 1.5, 0.5)
    far = expected_information_gain(rating, 12.0, 0.5)
    assert at_mean > near > far
    assert far == pytest.approx(0.0, abs=1e-5)  # foregone conclusion


# ---------------------------------------------------------------------------
# Scoring components
# ---------------------------------------------------------------------------


def test_underrepresented_band_gets_coverage_bonus(rating):
    history = SelectionHistory()
    for _ in range(6):
        history.record(_features(stage_band=1, product_id="iron-plate"))
    fresh_band = _features(stage_band=4)
    crowded = _features(stage_band=1)
    assert history.coverage_deficit(fresh_band) == 1.0
    assert history.coverage_deficit(crowded) < 0.2

    selector = ContractSelector()
    scored_fresh = selector.score_candidates(
        [_candidate(stage_band=4)], rating, history
    )[0]
    scored_crowded = selector.score_candidates(
        [_candidate(stage_band=1)], rating, history
    )[0]
    assert scored_fresh.components["coverage"] > scored_crowded.components["coverage"]


def test_recent_family_repetition_penalized(rating):
    weights = SelectorWeights(w_info=0.0, w_repeat=1.0)
    selector = ContractSelector(weights=weights)
    cold_history = SelectionHistory()
    hot_history = SelectionHistory()
    for _ in range(8):
        hot_history.record(_features(product_id="iron-plate"))

    cold = selector.score_candidates([_candidate()], rating, cold_history)[0]
    hot = selector.score_candidates([_candidate()], rating, hot_history)[0]
    assert cold.components["repeat"] == pytest.approx(0.0)
    assert hot.components["repeat"] > 0.5
    assert hot.score < cold.score


def test_novelty_decays_with_repetition(rating):
    history = SelectionHistory()
    novel = history.family_novelty(_features(product_id="new-item"))
    history.record(_features(product_id="new-item"))
    seen_once = history.family_novelty(_features(product_id="new-item"))
    assert novel > seen_once > 0.0


def test_extrapolation_penalty_requires_manifest(rating):
    from fle.envd.models import CalibrationManifest

    manifest = CalibrationManifest(
        calibration_version="cal",
        benchmark_version="bv",
        training_data_sha256="0" * 64,
        game_versions=("2.0.73",),
        template_bank_version="tb",
        template_intercepts={},
        beta_raw={},
        beta_state={},
        normalization={},
        clipping={},
        supported_ranges={"recipe_depth": (0.0, 2.0)},
    )
    plain = ContractSelector()
    calibrated = ContractSelector(manifest=manifest)

    assert (
        plain.score_candidates([_candidate()], rating, SelectionHistory())[
            0
        ].components["extrapolation"]
        == 0.0
    )
    penalized = calibrated.score_candidates(
        [_candidate(recipe_depth=9)], rating, SelectionHistory()
    )[0]
    clean = calibrated.score_candidates(
        [_candidate(recipe_depth=1)], rating, SelectionHistory()
    )[0]
    assert penalized.components["extrapolation"] > 0.0
    assert clean.components["extrapolation"] == 0.0


# ---------------------------------------------------------------------------
# Seeded selection
# ---------------------------------------------------------------------------


def _pool(n: int = 8) -> list[ContractCandidate]:
    return [_candidate(item=f"item-{i}", effective=float(i)) for i in range(n)]


def test_selection_is_replayable_from_seed(rating):
    selector = ContractSelector()
    pool = _pool()
    first, scored_a = selector.select(
        [c.model_copy(deep=True) for c in pool],
        rating,
        SelectionHistory(),
        selection_seed=12345,
    )
    second, scored_b = selector.select(
        [c.model_copy(deep=True) for c in pool],
        rating,
        SelectionHistory(),
        selection_seed=12345,
    )
    assert first.item_name == second.item_name
    assert [s.candidate.item_name for s in scored_a] == [
        s.candidate.item_name for s in scored_b
    ]


def test_different_seeds_can_diverge_on_ties(rating):
    """The committed randomness is real: seeds explore the pool."""
    selector = ContractSelector(weights=SelectorWeights(selection_temperature=0.5))
    picks = set()
    for seed in range(40):
        candidate, _ = selector.select(
            _pool(), rating, SelectionHistory(), selection_seed=seed
        )
        picks.add(candidate.item_name)
    assert len(picks) >= 3  # not collapsed onto one deterministic pick


def test_high_information_candidates_preferred_in_expectation(rating):
    selector = ContractSelector(
        weights=SelectorWeights(
            w_info=1.0,
            w_coverage=0.0,
            w_novelty=0.0,
            w_repeat=0.0,
            w_extrapolation=0.0,
            selection_temperature=0.01,
        )
    )
    # Pool items sit far from the rating (low information); the extra
    # candidate at the posterior mean strictly dominates on score.
    pool = [_candidate(item=f"far-{i}", effective=float(3 + i)) for i in range(6)] + [
        _candidate(item="at-rating", effective=0.05)
    ]
    wins = 0
    for seed in range(20):
        candidate, _ = selector.select(
            pool, rating, SelectionHistory(), selection_seed=seed
        )
        wins += int(candidate.item_name == "at-rating")
    assert wins >= 17  # dominant score with tiny jitter


def test_unseen_mixture_is_selected_before_repeating_covered_mixture(rating):
    history = SelectionHistory()
    history.record(_features(product_id="iron-plate"), "consolidation")
    consolidation = _candidate(item="copper-plate", effective=0.0)
    frontier = _candidate(item="steel-plate", effective=12.0).model_copy(
        update={"mixture_class": "frontier"}
    )
    for seed in range(10):
        selected, _ = ContractSelector().select(
            [consolidation, frontier], rating, history, selection_seed=seed
        )
        assert selected.mixture_class == "frontier"


def test_first_epoch_bootstraps_before_frontier(rating):
    consolidation = _candidate(item="iron-plate", effective=12.0)
    frontier = _candidate(item="steel-plate", effective=0.0).model_copy(
        update={"mixture_class": "frontier"}
    )
    for seed in range(10):
        selected, _ = ContractSelector().select(
            [consolidation, frontier], rating, SelectionHistory(), selection_seed=seed
        )
        assert selected.mixture_class == "consolidation"


def test_unseen_product_is_selected_before_same_class_repeat(rating):
    history = SelectionHistory()
    history.record(_features(product_id="iron-plate"), "consolidation")
    repeated = _candidate(item="iron-plate", effective=0.0)
    unseen = _candidate(item="copper-plate", effective=12.0)
    for seed in range(10):
        selected, _ = ContractSelector().select(
            [repeated, unseen], rating, history, selection_seed=seed
        )
        assert selected.item_name == "copper-plate"


def test_empty_pool_raises_selection_error(rating):
    selector = ContractSelector()
    rejected = ContractCandidate(
        template_id="t",
        mixture_class="stress",
        generation_seed=1,
        item_name="x",
        rejection_reason="infeasible_analytic",
    )
    with pytest.raises(SelectionError):
        selector.select([rejected], rating, SelectionHistory(), selection_seed=1)


# ---------------------------------------------------------------------------
# History bookkeeping
# ---------------------------------------------------------------------------


def test_history_window_bounds_repetition():
    history = SelectionHistory(window=4)
    for _ in range(20):
        history.record(_features(product_id="iron-plate"))
    repetition = history.recent_family_repetition(_features())
    assert repetition == pytest.approx(1.0)  # saturated, not unbounded
