"""Candidate scoring, coverage accounting, and seeded selection.

The selector is policy, not inference: it scores a bounded generated pool
against the current ability posterior and coverage obligations, then commits
one candidate using seeded randomness that is recorded in the epoch
specification and therefore fully replayable.

Scoring formula (section 13)::

    score = w_info   * expected_information_gain
          + w_coverage * coverage_deficit
          + w_novelty * family_novelty
          - w_repeat  * recent_family_repetition
          - w_extrapolation * calibration_extrapolation

Information gain favors contracts near the current rating but never
exclusively -- coverage and novelty terms keep the session from collapsing
into a single stage or product family.
"""

from __future__ import annotations

import math
import random
from collections import Counter, deque
from dataclasses import dataclass, field

from fle.envd.contract_generator import ContractCandidate, MIXTURE_WEIGHTS
from fle.envd.contract_rating import CalibratedDifficultyModel, contract_uncertainty
from fle.envd.models import (
    CalibrationManifest,
    CapabilityRating,
    ContractDifficultyFeatures,
    SelectorWeights,
)


class SelectionError(RuntimeError):
    """No viable candidate remained after filtering."""


def outcome_probabilities(
    rating: CapabilityRating,
    difficulty_mean: float,
    difficulty_sigma: float,
) -> float:
    """Probability the agent clears the contract (win side, pre-draw)."""
    spread = math.sqrt(
        rating.sigma**2 + difficulty_sigma**2 + 1.0  # +beta^2, beta=1
    )
    z = (rating.mu - difficulty_mean) / max(spread, 1e-9)
    return _normal_cdf(z)


def _normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _binary_entropy(p: float) -> float:
    p = min(max(p, 0.0), 1.0)
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log(p) + (1.0 - p) * math.log(1.0 - p)) / math.log(2.0)


def expected_information_gain(
    rating: CapabilityRating,
    difficulty_mean: float,
    difficulty_sigma: float,
) -> float:
    """Entropy of the predicted outcome distribution in [0, 1].

    Maximized when the contract sits at the agent's posterior mean (a
    maximally informative match) and vanishes for foregone conclusions.
    """
    p_clear = outcome_probabilities(rating, difficulty_mean, difficulty_sigma)
    return _binary_entropy(p_clear)


@dataclass
class SelectionHistory:
    """Coverage ledger across one adaptive session."""

    window: int = 8
    family_counts: Counter = field(default_factory=Counter)
    band_counts: Counter = field(default_factory=Counter)
    mixture_counts: Counter = field(default_factory=Counter)
    recent_families: deque = field(default_factory=deque)

    def record(
        self,
        features: ContractDifficultyFeatures,
        mixture_class: str | None = None,
    ) -> None:
        self.family_counts[features.product_id] += 1
        self.band_counts[features.stage_band] += 1
        if mixture_class is not None:
            self.mixture_counts[mixture_class] += 1
        self.recent_families.append(features.stage_band)
        self.recent_families.append(_family_of(features))
        while len(self.recent_families) > 2 * self.window:
            self.recent_families.popleft()

    def recent_family_repetition(self, features: ContractDifficultyFeatures) -> float:
        family = _family_of(features)
        count = sum(
            1
            for index, value in enumerate(self.recent_families)
            if index % 2 == 1 and value == family
        )
        return min(count / max(self.window, 1), 1.0)

    def coverage_deficit(
        self,
        features: ContractDifficultyFeatures,
        supported_bands: tuple[int, ...] = (0, 1, 2, 3, 4, 5),
    ) -> float:
        """How underrepresented this candidate's band is among obligations."""
        total = sum(self.band_counts.values())
        if total == 0:
            return 1.0  # everything is scarce before the first commitment
        share = self.band_counts.get(features.stage_band, 0) / total
        fair = 1.0 / max(len(supported_bands), 1)
        deficit = (fair - share) / max(fair, 1e-9)
        return min(max(deficit, 0.0), 1.0)

    def family_novelty(self, features: ContractDifficultyFeatures) -> float:
        seen = self.family_counts.get(features.product_id, 0)
        return 1.0 / (1.0 + seen)

    def mandatory_coverage_complete(
        self,
        *,
        required_bands: set[int],
        required_mixtures: set[str],
    ) -> bool:
        """Return whether every reachable coverage obligation was observed."""
        return required_bands.issubset(self.band_counts) and required_mixtures.issubset(
            self.mixture_counts
        )


def _family_of(features: ContractDifficultyFeatures) -> str:
    # Family granularity for repetition control: coarse product grouping by
    # progression tier keeps caps meaningful without a hand-maintained list.
    return f"tier{min(features.recipe_depth // 2, 3)}"


@dataclass(frozen=True)
class ScoredCandidate:
    candidate: ContractCandidate
    score: float
    components: dict[str, float]


class ContractSelector:
    """Deterministic, seeded candidate selection over one bounded pool."""

    def __init__(
        self,
        weights: SelectorWeights | None = None,
        manifest: CalibrationManifest | None = None,
    ):
        self.weights = weights or SelectorWeights()
        self.manifest = manifest
        self._difficulty = CalibratedDifficultyModel(manifest) if manifest else None

    def score_candidates(
        self,
        candidates: list[ContractCandidate],
        rating: CapabilityRating,
        history: SelectionHistory,
    ) -> list[ScoredCandidate]:
        scored: list[ScoredCandidate] = []
        for candidate in candidates:
            if not candidate.accepted or candidate.features is None:
                continue
            features = candidate.features
            effective = (
                candidate.effective_difficulty
                if candidate.effective_difficulty is not None
                else 0.0
            )
            uncertainty = contract_uncertainty(
                manifest=self.manifest, features=features
            )
            info = expected_information_gain(rating, effective, uncertainty)
            components = {
                "info": info,
                "coverage": history.coverage_deficit(features),
                "novelty": history.family_novelty(features),
                "unseen_product": float(
                    history.family_counts.get(features.product_id, 0) == 0
                ),
                "repeat": history.recent_family_repetition(features),
                "extrapolation": (
                    self._difficulty.extrapolation_distance(features)
                    if self._difficulty is not None
                    else 0.0
                ),
            }
            w = self.weights
            score = (
                w.w_info * components["info"]
                + w.w_coverage * components["coverage"]
                + w.w_novelty * components["novelty"]
                - w.w_repeat * components["repeat"]
                - w.w_extrapolation * components["extrapolation"]
            )
            scored.append(ScoredCandidate(candidate, score, components))
        return scored

    def select(
        self,
        candidates: list[ContractCandidate],
        rating: CapabilityRating,
        history: SelectionHistory,
        *,
        selection_seed: int,
    ) -> tuple[ContractCandidate, list[ScoredCandidate]]:
        """Commit one candidate via seeded Gumbel perturbation.

        The perturbation stays small relative to score scale so selection
        remains near-optimal while keeping committed randomness real and
        replayable from (selection_seed, pool identity).
        """
        scored = self.score_candidates(candidates, rating, history)
        if not scored:
            raise SelectionError("No accepted candidates in the pool")
        rng = random.Random(selection_seed)
        # Apply the benchmark's consolidation/frontier/stress mixture policy
        # before scoring the seeded choice.  If a class has no feasible member
        # in the current live catalog, fall back to the available classes so a
        # sparse training recipe dump does not create a false dead-end.
        available_classes = {
            scored_candidate.candidate.mixture_class for scored_candidate in scored
        }
        uncovered_classes = available_classes - set(history.mixture_counts)
        if not history.mixture_counts and "consolidation" in available_classes:
            # Establish a baseline factory before requiring a one-band frontier
            # transition. Subsequent uncovered classes remain hard obligations.
            uncovered_classes = {"consolidation"}
        weighted_classes = [
            mixture_class
            for mixture_class, weight in MIXTURE_WEIGHTS.items()
            if mixture_class in (uncovered_classes or available_classes) and weight > 0
        ]
        if weighted_classes:
            total_weight = sum(MIXTURE_WEIGHTS[mixture] for mixture in weighted_classes)
            draw = rng.random() * total_weight
            cumulative = 0.0
            selected_class = weighted_classes[-1]
            for mixture_class in weighted_classes:
                cumulative += MIXTURE_WEIGHTS[mixture_class]
                if draw <= cumulative:
                    selected_class = mixture_class
                    break
            scored = [
                item
                for item in scored
                if item.candidate.mixture_class == selected_class
            ]
        unseen_products = [
            item
            for item in scored
            if history.family_counts.get(item.candidate.item_name, 0) == 0
        ]
        if unseen_products:
            # Coverage is a benchmark obligation, not merely a small scoring
            # bonus. Once every feasible product in this sampled class has
            # appeared, normal information/novelty scoring resumes.
            scored = unseen_products
        span = max(s.score for s in scored) - min(s.score for s in scored)
        scale = max(self.weights.selection_temperature * max(span, 1e-6), 1e-12)

        def gumbel() -> float:
            u = rng.random()
            return -math.log(-math.log(max(u, 1e-12)))

        best = max(
            scored,
            key=lambda s: s.score + scale * gumbel(),
        )
        return best.candidate, scored


__all__ = [
    "ContractSelector",
    "ScoredCandidate",
    "SelectionError",
    "SelectionHistory",
    "expected_information_gain",
    "outcome_probabilities",
]
