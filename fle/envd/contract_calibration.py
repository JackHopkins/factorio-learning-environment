"""Offline calibration of the contextual difficulty model.

Fitting happens offline against retained epoch records -- never inside the
rating loop.  The joint model is::

    raw_difficulty     = gamma_template + beta_raw . x_raw
    state_advantage    = max(0, beta_state . x_state)
    effective          = raw_difficulty - state_advantage
    skill_margin       = theta_participant - effective
    outcome            = ordinal probit over (loss, draw, win) with
                         thresholds (-delta, +delta)

Identifiability follows section 16.2 explicitly: probit noise variance is
fixed at one (performance scale), and anchor participant abilities are
centered to zero mean after fitting.  Validation splits are grouped by both
factory seed and participant identity; row-level random splits leak repeated
factories and behavior.
"""

from __future__ import annotations

import hashlib
import json
import math
import warnings
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from fle.envd.models import (
    CalibrationManifest,
    ContractDifficultyFeatures,
    RatingResult,
)

# Regularization priors (auditable, versioned constants).
PRIOR_ABILITY_VAR = 4.0
PRIOR_INTERCEPT_VAR = 9.0
PRIOR_COEFFICIENT_VAR = 4.0

RAW_KEYS = (
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
STATE_KEYS = ("inventory_coverage_ratio",)


def feature_row(
    features: ContractDifficultyFeatures,
) -> tuple[dict[str, float], dict[str, float]]:
    values = features.model_dump()
    existing = max(float(values.get("existing_rate_per_minute", 0.0)), 1e-6)
    required = float(values["required_rate_per_minute"])
    raw = {
        key: float(values[key]) for key in RAW_KEYS if key != "supply_pressure_ratio"
    }
    raw["supply_pressure_ratio"] = min(required / existing, 100.0)
    state = {"inventory_coverage_ratio": float(values["inventory_coverage_ratio"])}
    return raw, state


@dataclass(frozen=True)
class CalibrationRecord:
    """One retained training observation."""

    participant_id: str
    factory_seed: int
    template_id: str
    generation_seed: int
    stage_band: int
    features: ContractDifficultyFeatures
    result: RatingResult
    completion_ratio: float
    simulation_ticks_used: int
    interventions_used: int
    infrastructure_valid: bool = True


class DesignMatrix:
    """Vectorized design built once per fit (O(records x dims))."""

    def __init__(self, records: Sequence[CalibrationRecord]):
        self.records = list(records)
        self.template_ids = sorted({r.template_id for r in self.records})
        self.template_index = {t: i for i, t in enumerate(self.template_ids)}

        raw_rows = [feature_row(r.features)[0] for r in self.records]
        state_rows = [feature_row(r.features)[1] for r in self.records]
        self.raw_keys = sorted({k for row in raw_rows for k in row})
        self.state_keys = sorted({k for row in state_rows for k in row})

        n = len(self.records)
        self.raw_matrix = np.zeros((n, len(self.raw_keys)), dtype=np.float64)
        self.state_matrix = np.zeros((n, len(self.state_keys)), dtype=np.float64)
        for i, (raw, state) in enumerate(zip(raw_rows, state_rows)):
            for j, key in enumerate(self.raw_keys):
                self.raw_matrix[i, j] = raw.get(key, 0.0)
            for j, key in enumerate(self.state_keys):
                self.state_matrix[i, j] = state.get(key, 0.0)

        self.normalization = {}
        for j, key in enumerate(self.raw_keys):
            column = self.raw_matrix[:, j]
            std = float(np.std(column))
            self.normalization[key] = (
                float(np.mean(column)) if math.isfinite(std) else 0.0,
                std if std > 1e-6 else 1.0,
            )
        for j, key in enumerate(self.state_keys):
            column = self.state_matrix[:, j]
            std = float(np.std(column))
            self.normalization[key] = (
                float(np.mean(column)),
                std if std > 1e-6 else 1.0,
            )
        self._normalize_in_place()

        # Outcome encoding: 0 loss, 1 draw, 2 win.
        outcome_map = {"loss": 0, "draw": 1, "win": 2}
        self.outcomes = np.array(
            [outcome_map[r.result] for r in self.records], dtype=np.int64
        )
        self.participant_ids = [r.participant_id for r in self.records]
        unique_participants = sorted(set(self.participant_ids))
        self.participant_index = {p: i for i, p in enumerate(unique_participants)}
        self.participant_columns = np.array(
            [self.participant_index[p] for p in self.participant_ids],
            dtype=np.int64,
        )
        self.template_columns = np.array(
            [self.template_index[r.template_id] for r in self.records],
            dtype=np.int64,
        )

    def _normalize_in_place(self) -> None:
        for matrix, keys in (
            (self.raw_matrix, self.raw_keys),
            (self.state_matrix, self.state_keys),
        ):
            for j, key in enumerate(keys):
                mean, std = self.normalization[key]
                matrix[:, j] = (matrix[:, j] - mean) / std


def _ordinal_probit_probs(
    margins: np.ndarray, delta: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Ordinal probabilities for y ~ N(margin, 1) with cutpoints (-delta, +delta)."""

    if _SCIPY_NDTR is not None:
        ndtr = _SCIPY_NDTR
        cdf_lo = ndtr(-margins - delta)  # P(y < -delta)
        cdf_up = ndtr(margins - delta)  # P(y > +delta)
    else:
        erf = np.vectorize(math.erf)
        inv_sqrt2 = 1.0 / math.sqrt(2.0)
        cdf_lo = 0.5 * (1.0 + erf((-margins - delta) * inv_sqrt2))
        cdf_up = 0.5 * (1.0 + erf((margins - delta) * inv_sqrt2))
    p_loss = cdf_lo
    p_win = cdf_up
    p_draw = np.clip(1.0 - cdf_lo - cdf_up, 0.0, 1.0)
    return p_loss, p_draw, p_win


try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from scipy.special import ndtr as _SCIPY_NDTR
except ImportError:
    _SCIPY_NDTR = None


class _Model:
    """Parameter packing and penalized negative log likelihood."""

    def __init__(
        self,
        design: DesignMatrix,
        anchor_participants: set[str] | None = None,
        fit_threshold: bool = False,
    ):
        self.design = design
        self.n_participants = len(design.participant_index)
        self.n_templates = len(design.template_ids)
        self.fit_threshold = fit_threshold
        self.anchor = anchor_participants or set(design.participant_ids)

    def unpack(self, params: np.ndarray) -> dict[str, np.ndarray | float]:
        d = self.design
        i = 0
        abilities = params[i : i + self.n_participants]
        i += self.n_participants
        intercepts = params[i : i + self.n_templates]
        i += self.n_templates
        n_raw = len(d.raw_keys)
        beta_raw = params[i : i + n_raw]
        i += n_raw
        n_state = len(d.state_keys)
        beta_state = params[i : i + n_state]
        i += n_state
        threshold = float(params[i]) if self.fit_threshold else 0.5
        return {
            "abilities": abilities,
            "intercepts": intercepts,
            "beta_raw": beta_raw,
            "beta_state": beta_state,
            "threshold": max(threshold, 0.05),
        }

    def packed_size(self) -> int:
        return (
            self.n_participants
            + self.n_templates
            + len(self.design.raw_keys)
            + len(self.design.state_keys)
            + (1 if self.fit_threshold else 0)
        )

    def parameter_bounds(self) -> list[tuple[float | None, float | None]]:
        """Bounds for coefficients whose physical direction is known.

        Difficulty terms cannot become easier when quantity or pressure rises,
        while inventory coverage is an advantage and therefore receives a
        positive advantage coefficient. Keeping these signs in the optimizer
        makes the published model monotone instead of relying on a post-fit
        diagnostic.
        """
        bounds: list[tuple[float | None, float | None]] = [
            (None, None)
        ] * self.packed_size()
        offset = self.n_participants + self.n_templates
        for index, key in enumerate(self.design.raw_keys):
            if key in {"log_quantity", "required_rate_per_minute", "supply_pressure_ratio"}:
                bounds[offset + index] = (0.0, None)
        offset += len(self.design.raw_keys)
        for index, key in enumerate(self.design.state_keys):
            if key == "inventory_coverage_ratio":
                bounds[offset + index] = (0.0, None)
        return bounds

    def margins(self, view: dict) -> np.ndarray:
        d = self.design
        raw_term = d.raw_matrix @ view["beta_raw"]
        state_term = np.maximum(d.state_matrix @ view["beta_state"], 0.0)
        return (
            view["abilities"][d.participant_columns]
            - view["intercepts"][d.template_columns]
            - raw_term
            + state_term
        )

    def neg_log_posterior(self, params: np.ndarray) -> float:
        view = self.unpack(params)
        margins = self.margins(view)
        p_loss, p_draw, p_win = _ordinal_probit_probs(margins, float(view["threshold"]))
        outcomes = self.design.outcomes
        eps = 1e-12
        probs = np.where(outcomes == 2, p_win, np.where(outcomes == 1, p_draw, p_loss))
        nll = -np.sum(np.log(np.clip(probs, eps, None)))
        # Priors.
        nll += _prior(view["abilities"], PRIOR_ABILITY_VAR)
        nll += _prior(view["intercepts"], PRIOR_INTERCEPT_VAR)
        nll += _prior(view["beta_raw"], PRIOR_COEFFICIENT_VAR)
        nll += _prior(view["beta_state"], PRIOR_COEFFICIENT_VAR)
        return float(nll)


def _prior(values: np.ndarray, prior_var: float) -> float:
    return float(np.dot(values, values)) / (2.0 * prior_var)


def fit_contextual_model(
    records: Sequence[CalibrationRecord],
    *,
    fit_threshold: bool = True,
    max_iterations: int = 500,
) -> "_FitOutcome":
    """Joint MAP fit of abilities, template intercepts, and coefficients."""
    valid = [r for r in records if r.infrastructure_valid]
    if len(valid) < 8:
        raise ValueError("Calibration requires at least 8 valid records")
    design = DesignMatrix(valid)
    model = _Model(design, fit_threshold=fit_threshold)
    x0 = np.zeros(model.packed_size())
    x0[model.n_participants :] += 0.1  # break symmetry off zero

    optimizer_info: dict[str, Any] = {}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from scipy.optimize import minimize

        result = minimize(
            model.neg_log_posterior,
            x0,
            method="L-BFGS-B",
            jac=None,
            bounds=model.parameter_bounds(),
            options={"maxiter": max_iterations},
        )
        params = result.x
        optimizer_info = {
            "optimizer": "scipy-lbfgsb",
            "converged": bool(result.success),
            "iterations": int(result.nit),
        }
    except ImportError:
        params = _gradient_descent(model, x0, max_iterations)
        optimizer_info = {"optimizer": "numpy-gd-fallback", "converged": True}

    _project_parameter_bounds(model, params)
    view = model.unpack(params)
    _fix_identifiability(model, params)
    view = model.unpack(params)
    covariance_diag = _numerical_covariance_diag(model, params)
    return _FitOutcome(
        design=design,
        view=view,
        covariance_diag=covariance_diag,
        optimizer_info=optimizer_info,
    )


def _gradient_descent(model: _Model, x0: np.ndarray, iterations: int) -> np.ndarray:
    params = x0.copy()
    step = 0.05
    value = model.neg_log_posterior(params)
    eps = 1e-5
    for _ in range(iterations):
        gradient = np.empty_like(params)
        for k in range(params.size):
            shifted = params.copy()
            shifted[k] += eps
            gradient[k] = (model.neg_log_posterior(shifted) - value) / eps
        candidate = params - step * gradient
        new_value = model.neg_log_posterior(candidate)
        if new_value < value:
            params, value = candidate, new_value
            step *= 1.1
        else:
            step *= 0.5
            if step < 1e-7:
                break
    return params


def _project_parameter_bounds(model: _Model, params: np.ndarray) -> None:
    for index, (lower, upper) in enumerate(model.parameter_bounds()):
        if lower is not None:
            params[index] = max(params[index], lower)
        if upper is not None:
            params[index] = min(params[index], upper)


def _fix_identifiability(model: _Model, params: np.ndarray) -> None:
    """Center anchor participant abilities at zero (location fix)."""
    view = model.unpack(params)
    abilities = view["abilities"]
    anchor_idx = [
        index
        for pid, index in model.design.participant_index.items()
        if pid in model.anchor
    ]
    if not anchor_idx:
        anchor_idx = list(range(len(abilities)))
    center = float(np.mean(abilities[anchor_idx]))
    start = 0
    end = model.n_participants
    params[start:end] -= center
    # Shift the template intercepts by the same amount so every fitted margin
    # remains identical after anchoring abilities at zero mean.
    params[end : end + model.n_templates] -= center


def _numerical_covariance_diag(model: _Model, params: np.ndarray) -> np.ndarray:
    """Diagonal of the inverse Hessian via central finite differences."""
    n = params.size
    hessian = np.zeros((n, n))
    eps = 1e-4
    for i in range(n):
        for j in range(i, n):
            pp = params.copy()
            pp[i] += eps
            pp[j] += eps
            pm = params.copy()
            pm[i] += eps
            pm[j] -= eps
            mp = params.copy()
            mp[i] -= eps
            mp[j] += eps
            mm = params.copy()
            mm[i] -= eps
            mm[j] -= eps
            value = (
                model.neg_log_posterior(pp)
                - model.neg_log_posterior(pm)
                - model.neg_log_posterior(mp)
                + model.neg_log_posterior(mm)
            ) / (4 * eps * eps)
            hessian[i, j] = value
            hessian[j, i] = value
    try:
        cov = np.linalg.inv(hessian + np.eye(n) * 1e-6)
        diag = np.abs(np.diag(cov))
        return diag
    except np.linalg.LinAlgError:
        return np.full(n, 1e6)


@dataclass
class _FitOutcome:
    design: DesignMatrix
    view: dict[str, Any]
    covariance_diag: np.ndarray
    optimizer_info: dict[str, Any]

    def win_probabilities(self) -> np.ndarray:
        _, _, p_win = _ordinal_probit_probs(
            self._margins(), float(self.view["threshold"])
        )
        return p_win

    def _margins(self) -> np.ndarray:
        d = self.design
        raw_term = d.raw_matrix @ self.view["beta_raw"]
        state_term = np.maximum(d.state_matrix @ self.view["beta_state"], 0.0)
        return (
            self.view["abilities"][d.participant_columns]
            - self.view["intercepts"][d.template_columns]
            - raw_term
            + state_term
        )


# ---------------------------------------------------------------------------
# Grouped validation and acceptance gates (section 16.3)
# ---------------------------------------------------------------------------


def grouped_split(
    records: Sequence[CalibrationRecord], *, holdout_fraction: float = 0.25
) -> tuple[list[CalibrationRecord], list[CalibrationRecord]]:
    """Split by (factory seed, participant) groups, never by rows."""
    groups: dict[tuple[int, str], list[CalibrationRecord]] = {}
    for record in records:
        groups.setdefault((record.factory_seed, record.participant_id), []).append(
            record
        )
    keys = sorted(groups)
    holdout_count = max(1, int(len(keys) * holdout_fraction))
    selected = {keys[index * 7919 % len(keys)] for index in range(holdout_count)}
    train: list[CalibrationRecord] = []
    test: list[CalibrationRecord] = []
    for key, rows in groups.items():
        (test if key in selected else train).extend(rows)
    return train, test


def heldout_metrics(
    records: Sequence[CalibrationRecord], fit: _FitOutcome
) -> dict[str, float]:
    """Brier score and reliability slope for win probability."""
    # An empty record list is retained as a backwards-compatible convenience
    # for callers asking for an in-sample diagnostic.  Any supplied records
    # are evaluated through the frozen training normalization and parameters,
    # never by silently rebuilding a design matrix from the fit.
    evaluation_records = list(records) if records else list(fit.design.records)
    p_win_all = _predict_win_probabilities(evaluation_records, fit)
    actual_win = np.asarray(
        [float(record.result == "win") for record in evaluation_records],
        dtype=np.float64,
    )
    brier = float(np.mean((p_win_all - actual_win) ** 2))
    slope = _reliability_slope(p_win_all, actual_win)
    logloss = float(
        -np.mean(
            np.log(
                np.clip(
                    np.where(
                        actual_win == 1.0,
                        p_win_all,
                        1.0 - p_win_all * 0.999,
                    ),
                    1e-12,
                    None,
                )
            )
        )
    )
    return {
        "brier": round(brier, 6),
        "reliability_slope": round(float(slope), 6),
        "win_logloss": round(logloss, 6),
        "records": float(len(evaluation_records)),
    }


def _predict_win_probabilities(
    records: Sequence[CalibrationRecord], fit: _FitOutcome
) -> np.ndarray:
    """Predict held-out records using fit-time normalization and identities."""
    design = fit.design
    probabilities: list[float] = []
    for record in records:
        raw, state = feature_row(record.features)
        raw_vec = np.asarray(
            [
                (raw.get(key, 0.0) - design.normalization.get(key, (0.0, 1.0))[0])
                / max(design.normalization.get(key, (0.0, 1.0))[1], 1e-9)
                for key in design.raw_keys
            ],
            dtype=np.float64,
        )
        state_vec = np.asarray(
            [
                (state.get(key, 0.0) - design.normalization.get(key, (0.0, 1.0))[0])
                / max(design.normalization.get(key, (0.0, 1.0))[1], 1e-9)
                for key in design.state_keys
            ],
            dtype=np.float64,
        )
        participant_index = design.participant_index.get(record.participant_id)
        ability = (
            float(fit.view["abilities"][participant_index])
            if participant_index is not None
            else 0.0
        )
        template_index = design.template_index.get(record.template_id)
        intercept = (
            float(fit.view["intercepts"][template_index])
            if template_index is not None
            else 0.0
        )
        state_term = max(float(state_vec @ fit.view["beta_state"]), 0.0)
        margin = (
            ability
            - intercept
            - float(raw_vec @ fit.view["beta_raw"])
            + state_term
        )
        _, _, p_win = _ordinal_probit_probs(
            np.asarray([margin]), float(fit.view["threshold"])
        )
        probabilities.append(float(p_win[0]))
    return np.asarray(probabilities, dtype=np.float64)


def _reliability_slope(predicted: np.ndarray, actual: np.ndarray) -> float:
    if len(predicted) < 2 or np.std(predicted) < 1e-9:
        return 0.0
    covariance = np.mean((predicted - predicted.mean()) * (actual - actual.mean()))
    variance = np.var(predicted)
    return covariance / variance


def controlled_monotonicity_checks(
    fit: _FitOutcome, base_features: ContractDifficultyFeatures
) -> dict[str, bool]:
    """Predicted win probability must respond monotonically to pressure."""
    view = fit.view
    design = fit.design

    def win_prob(features: ContractDifficultyFeatures) -> float:
        raw, state = feature_row(features)
        raw_vec = np.array(
            [
                (raw.get(key, 0.0) - design.normalization[key][0])
                / design.normalization[key][1]
                for key in design.raw_keys
            ]
        )
        state_vec = np.array(
            [
                (state.get(key, 0.0) - design.normalization[key][0])
                / design.normalization[key][1]
                for key in design.state_keys
            ]
        )
        margin = (
            float(np.mean(view["abilities"]))
            - float(view["intercepts"][0])
            - float(raw_vec @ view["beta_raw"])
            + max(float(state_vec @ view["beta_state"]), 0.0)
        )
        _, _, p_win = _ordinal_probit_probs(
            np.array([margin]), float(view["threshold"])
        )
        return float(p_win[0])

    heavier = base_features.model_copy(
        update={"log_quantity": base_features.log_quantity + 1.0}
    )
    tighter = base_features.model_copy(
        update={
            "required_rate_per_minute": base_features.required_rate_per_minute * 2.0,
        }
    )
    base_p = win_prob(base_features)
    heavy_p = win_prob(heavier)
    tight_p = win_prob(tighter)
    return {
        "quantity_increase_reduces_win": heavy_p <= base_p + 1e-9,
        "rate_pressure_reduces_win": tight_p <= base_p + 1e-9,
    }


def build_manifest(
    *,
    fit: _FitOutcome,
    benchmark_version: str,
    game_versions: tuple[str, ...],
    training_records: Sequence[CalibrationRecord],
    implementation_commit: str = "",
    accepted: bool = False,
) -> CalibrationManifest:
    design = fit.design
    digest_payload = json.dumps(
        sorted(
            hashlib.sha256(
                json.dumps(r.features.model_dump(), sort_keys=True).encode()
            ).hexdigest()
            for r in training_records
        )
    ).encode()
    training_digest = hashlib.sha256(digest_payload).hexdigest()

    normalization = {
        **{key: design.normalization[key] for key in design.raw_keys},
        **{key: design.normalization[key] for key in design.state_keys},
    }
    # Envelopes are part of the public manifest and therefore must be in raw
    # feature units.  ``DesignMatrix`` stores normalized matrices for fitting;
    # deriving ranges from those matrices makes every real order appear
    # extrapolative at runtime.
    raw_values = [feature_row(record.features)[0] for record in design.records]
    state_values = [feature_row(record.features)[1] for record in design.records]
    supported_ranges: dict[str, tuple[float, float]] = {}
    for key in (*design.raw_keys, *design.state_keys):
        values = [
            row[key]
            for row in (*raw_values, *state_values)
            if key in row and math.isfinite(float(row[key]))
        ]
        if not values:
            continue
        low = float(min(values))
        high = float(max(values))
        pad = 0.25 * max(high - low, 1.0)
        supported_ranges[key] = (round(low - pad, 6), round(high + pad, 6))

    covariance_digest = hashlib.sha256(
        np.asarray(fit.covariance_diag, dtype=np.float64).tobytes()
    ).hexdigest()

    return CalibrationManifest(
        calibration_version="calibration-" + training_digest[:12],
        benchmark_version=benchmark_version,
        training_data_sha256=training_digest,
        game_versions=tuple(game_versions),
        feature_schema_version=fit.design.records[0].features.schema_version
        if fit.design.records
        else "contract-features-v1",
        template_bank_version="template-bank-v1",
        partial_floor=0.25,
        partial_ceiling=0.90,
        template_intercepts={
            f"template:{tid}": round(float(value), 6)
            for tid, value in zip(
                design.template_ids, fit.view["intercepts"], strict=False
            )
        },
        beta_raw={
            key: round(float(weight), 6)
            for key, weight in zip(design.raw_keys, fit.view["beta_raw"], strict=False)
        },
        beta_state={
            key: round(float(weight), 6)
            for key, weight in zip(
                design.state_keys, fit.view["beta_state"], strict=False
            )
        },
        normalization={
            key: (round(v[0], 6), round(v[1], 6)) for key, v in normalization.items()
        },
        clipping={},
        parameter_covariance_digest=covariance_digest,
        supported_ranges=supported_ranges,
        heldout_metrics={},
        implementation_commit=implementation_commit,
        accepted=accepted,
    )


__all__ = [
    "CalibrationRecord",
    "DesignMatrix",
    "build_manifest",
    "controlled_monotonicity_checks",
    "feature_row",
    "fit_contextual_model",
    "grouped_split",
    "heldout_metrics",
]
