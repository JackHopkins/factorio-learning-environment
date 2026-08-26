"""Outcome mapping, contextual difficulty, and online ability updates.

Rating policy is deliberately isolated here: ``customer.py`` stays a pure
order state machine, generation never scores itself beyond feasibility, and
the underlying inference implementation is replaceable behind
:class:`ContractRater`.  Only plain floats cross that boundary -- package
types never appear in saved results.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from typing import Literal, Protocol

from fle.envd.models import (
    CapabilityRating,
    CalibrationManifest,
    ContractDifficultyFeatures,
    ContractEpochOutcome,
)

# Section 11 initial thresholds; calibrated and versioned through manifests.
DEFAULT_PARTIAL_FLOOR = 0.25
DEFAULT_PARTIAL_CEILING = 0.90

# Rating-scale constants (section 16.2 fixes performance scale beta = 1).
_RATING_BETA = 1.0
_RATING_TAU = 0.03  # per-epoch skill dynamics
_RATING_DRAW_PROBABILITY = 0.10
_INITIAL_SIGMA = 2.0  # two performance betas
_MIN_CONTRACT_SIGMA = 1e-3


class OutcomeThresholds:
    """Versioned cutpoints separating win/draw/loss completion bands."""

    __slots__ = ("partial_floor", "partial_ceiling")

    def __init__(
        self,
        partial_floor: float = DEFAULT_PARTIAL_FLOOR,
        partial_ceiling: float = DEFAULT_PARTIAL_CEILING,
    ):
        if not 0.0 <= partial_floor < partial_ceiling <= 1.0:
            raise ValueError("Thresholds must satisfy 0 <= floor < ceiling <= 1")
        self.partial_floor = partial_floor
        self.partial_ceiling = partial_ceiling

    @classmethod
    def from_manifest(cls, manifest: CalibrationManifest | None) -> "OutcomeThresholds":
        if manifest is None:
            return cls()
        return cls(manifest.partial_floor, manifest.partial_ceiling)


def map_outcome(
    outcome: ContractEpochOutcome,
    thresholds: OutcomeThresholds | None = None,
) -> Literal["win", "draw", "loss"] | None:
    """Global outcome mapping (section 11). Returns None when unratable."""

    cuts = thresholds or OutcomeThresholds()
    if outcome.status in ("infrastructure_error", "invalid"):
        return None
    if outcome.status == "abandoned":
        return "loss"
    if outcome.status == "fulfilled":
        return "win"
    ratio = outcome.completion_ratio
    if ratio <= cuts.partial_floor:
        return "loss"
    return "draw"


# ---------------------------------------------------------------------------
# Contextual difficulty models (section 10)
# ---------------------------------------------------------------------------

RAW_FEATURE_KEYS: tuple[str, ...] = (
    "recipe_depth",
    "missing_technology_count",
    "missing_machine_type_count",
    "required_new_intermediate_count",
    "log_quantity",
    "required_rate_per_minute",
    "supply_pressure_ratio",
    "estimated_power_fraction",
    "transport_complexity",
)

# Advantage-side features measure what the factory ALREADY contributes;
# they reduce effective difficulty and never increase it.
STATE_FEATURE_KEYS: tuple[str, ...] = ("inventory_coverage_ratio",)


def supply_pressure_ratio(features: ContractDifficultyFeatures) -> float:
    """required rate / max(existing rate, epsilon): explicit physical ratio."""
    existing = max(features.existing_rate_per_minute, 1e-6)
    return min(features.required_rate_per_minute / existing, 100.0)


def _feature_vector(
    features: ContractDifficultyFeatures,
    keys: tuple[str, ...],
) -> dict[str, float]:
    values = features.model_dump()
    vector = {key: float(values[key]) for key in keys if key in values}
    if "supply_pressure_ratio" in keys:
        vector["supply_pressure_ratio"] = supply_pressure_ratio(features)
    return vector


class DifficultyModel(Protocol):
    def evaluate(
        self,
        features: ContractDifficultyFeatures,
        *,
        template_id: str | None = None,
    ) -> tuple[float, float, float]:
        """Return (raw_difficulty, state_advantage, effective_difficulty)."""


@dataclass(frozen=True)
class UncalibratedDifficultyModel:
    """Broad hand-set prior used before a calibration manifest exists.

    Weights are documented heuristics, NOT fitted values: official scoring
    stays disabled until section 16 gates pass.  Each term is normalized to
    roughly unit range so no single feature dominates.
    """

    default_intercept: float = 1.0
    template_intercepts: dict[str, float] = field(default_factory=dict)
    raw_weights: dict[str, float] = field(
        default_factory=lambda: {
            "recipe_depth": 0.35,
            "missing_technology_count": 0.60,
            "missing_machine_type_count": 0.45,
            "required_new_intermediate_count": 0.30,
            "log_quantity": 0.15,
            "required_rate_per_minute": 0.002,
            "supply_pressure_ratio": 0.03,
            "estimated_power_fraction": 0.20,
            "transport_complexity": 0.50,
        }
    )
    state_weights: dict[str, float] = field(
        default_factory=lambda: {
            "inventory_coverage_ratio": 0.60,
        }
    )

    def evaluate(
        self,
        features: ContractDifficultyFeatures,
        *,
        template_id: str | None = None,
    ) -> tuple[float, float, float]:
        raw_values = _feature_vector(features, RAW_FEATURE_KEYS)
        state_values = _feature_vector(features, STATE_FEATURE_KEYS)
        intercept = self.template_intercepts.get(
            template_id or "",
            self.template_intercepts.get(features.product_id, self.default_intercept),
        )
        raw = intercept + sum(
            weight * raw_values.get(key, 0.0)
            for key, weight in self.raw_weights.items()
        )
        advantage = sum(
            weight * state_values.get(key, 0.0)
            for key, weight in self.state_weights.items()
        )
        advantage = max(advantage, 0.0)  # advantage cannot add difficulty
        effective = raw - advantage
        return (round(raw, 6), round(advantage, 6), round(effective, 6))


class CalibratedDifficultyModel:
    """Frozen linear contextual model driven by a calibration manifest."""

    def __init__(self, manifest: CalibrationManifest):
        self.manifest = manifest

    def evaluate(
        self,
        features: ContractDifficultyFeatures,
        *,
        template_id: str | None = None,
    ) -> tuple[float, float, float]:
        manifest = self.manifest
        raw_values = _feature_vector(
            features,
            tuple(sorted(set(RAW_FEATURE_KEYS) | set(manifest.beta_raw))),
        )
        state_values = _feature_vector(
            features,
            tuple(sorted(set(STATE_FEATURE_KEYS) | set(manifest.beta_state))),
        )

        def normalized(
            key: str, value: float, bank: dict[str, tuple[float, float]]
        ) -> float:
            mean, std = bank.get(key, (0.0, 1.0))
            clipped = value
            clip = manifest.clipping.get(key)
            if clip is not None:
                clipped = min(max(value, clip[0]), clip[1])
            return (clipped - mean) / max(std, 1e-9)

        # Calibration records are keyed by the committed template, while a
        # feature vector only carries the product.  Keep the product-key
        # fallback for older manifests and direct model probes, but use the
        # template supplied by generation whenever it is available.
        intercept_keys = []
        if template_id:
            intercept_keys.append(f"template:{template_id}")
            intercept_keys.append(template_id)
        intercept_keys.extend(
            [f"template:{features.product_id}", features.product_id]
        )
        raw = next(
            (manifest.template_intercepts[key] for key in intercept_keys if key in manifest.template_intercepts),
            0.0,
        )
        for key, weight in manifest.beta_raw.items():
            raw += weight * normalized(
                key, raw_values.get(key, 0.0), manifest.normalization
            )
        advantage = 0.0
        for key, weight in manifest.beta_state.items():
            advantage += weight * normalized(
                key, state_values.get(key, 0.0), manifest.normalization
            )
        advantage = max(advantage, 0.0)
        effective = raw - advantage
        return (round(raw, 6), round(advantage, 6), round(effective, 6))

    def extrapolation_distance(self, features: ContractDifficultyFeatures) -> float:
        """How far order features sit outside the supported envelope (0 in)."""
        values = _feature_vector(features, tuple(self.manifest.supported_ranges))
        worst = 0.0
        for key, (low, high) in self.manifest.supported_ranges.items():
            value = values.get(key)
            if not isinstance(value, (int, float)):
                continue
            span = max(high - low, 1e-9)
            if value < low:
                worst = max(worst, (low - value) / span)
            elif value > high:
                worst = max(worst, (value - high) / span)
        return worst

    def out_of_envelope(self, features: ContractDifficultyFeatures) -> bool:
        return self.extrapolation_distance(features) > 0.0


def contract_uncertainty(
    *,
    manifest: CalibrationManifest | None,
    features: ContractDifficultyFeatures | None = None,
    extrapolation_limit: float = 0.5,
) -> float:
    """Virtual contract player's difficulty sigma (section 12).

    Combines calibration parameter uncertainty with extrapolation growth;
    uncalibrated runs carry a wide honest prior instead of false precision.
    """
    if manifest is None or features is None:
        return 1.5
    base = 0.5
    distance = CalibratedDifficultyModel(manifest).extrapolation_distance(features)
    growth = (
        math.exp(max(distance - extrapolation_limit, 0.0))
        if (distance > extrapolation_limit)
        else distance / max(extrapolation_limit, 1e-9) * 0.25
    )
    return max(base + growth, _MIN_CONTRACT_SIGMA)


# ---------------------------------------------------------------------------
# ContractRater protocol and the pinned TrueSkill implementation
# ---------------------------------------------------------------------------


class ContractRater(Protocol):
    def initial_rating(self) -> CapabilityRating: ...

    def update(
        self,
        rating: CapabilityRating,
        difficulty_mean: float,
        difficulty_sigma: float,
        result: Literal["win", "draw", "loss"],
    ) -> CapabilityRating: ...


class TrueskillContractRater:
    """Pinned ``trueskill==0.4.5`` behind the ContractRater interface.

    Each epoch is one match between the persistent agent player and a virtual
    contract player whose mean is the effective difficulty and whose sigma
    carries calibration + extrapolation uncertainty.  Only the agent posterior
    survives the update; the virtual contract posterior is discarded.
    """

    def __init__(
        self,
        *,
        model_version: str = "trueskill-contract-v1",
        beta: float = _RATING_BETA,
        tau: float = _RATING_TAU,
        draw_probability: float = _RATING_DRAW_PROBABILITY,
        initial_sigma: float = _INITIAL_SIGMA,
    ):
        self.model_version = model_version
        self.initial_sigma = initial_sigma
        with warnings.catch_warnings():
            # trueskill 0.4.5 emits a cosmetic SyntaxWarning from an ASCII
            # banner docstring at import time; silence it at this boundary.
            warnings.simplefilter("ignore", SyntaxWarning)
            import trueskill

            self._trueskill = trueskill
        self._env = trueskill.TrueSkill(
            mu=0.0,
            sigma=initial_sigma,
            beta=beta,
            tau=tau,
            draw_probability=draw_probability,
        )

    def initial_rating(self) -> CapabilityRating:
        return CapabilityRating(
            model_version=self.model_version,
            mu=0.0,
            sigma=self.initial_sigma,
            conservative_score=-3.0 * self.initial_sigma,
            rated_epoch_count=0,
        )

    def update(
        self,
        rating: CapabilityRating,
        difficulty_mean: float,
        difficulty_sigma: float,
        result: Literal["win", "draw", "loss"],
    ) -> CapabilityRating:
        env = self._env
        agent = env.create_rating(mu=float(rating.mu), sigma=float(rating.sigma))
        contract = env.create_rating(
            mu=float(difficulty_mean),
            sigma=max(float(difficulty_sigma), _MIN_CONTRACT_SIGMA),
        )
        # Use the package-level helper.  TrueSkill 0.4.5 emits a deprecation
        # warning for the equivalent environment instance method.
        rate_1vs1 = self._trueskill.rate_1vs1
        if result == "win":
            agent, _ = rate_1vs1(agent, contract, env=env)
        elif result == "loss":
            _, agent = rate_1vs1(contract, agent, env=env)
        else:
            agent, _ = rate_1vs1(agent, contract, drawn=True, env=env)
        new_sigma = max(float(agent.sigma), 0.0)
        if not math.isfinite(agent.mu) or not math.isfinite(new_sigma):
            raise ValueError("Non-finite rating after update")
        return CapabilityRating(
            model_version=rating.model_version or self.model_version,
            mu=round(float(agent.mu), 6),
            sigma=round(new_sigma, 6),
            conservative_score=round(float(agent.mu) - 3.0 * new_sigma, 6),
            rated_epoch_count=rating.rated_epoch_count + 1,
        )


__all__ = [
    "DEFAULT_PARTIAL_CEILING",
    "DEFAULT_PARTIAL_FLOOR",
    "CalibratedDifficultyModel",
    "ContractRater",
    "DifficultyModel",
    "OutcomeThresholds",
    "RAW_FEATURE_KEYS",
    "STATE_FEATURE_KEYS",
    "TrueskillContractRater",
    "UncalibratedDifficultyModel",
    "contract_uncertainty",
    "map_outcome",
    "supply_pressure_ratio",
]
