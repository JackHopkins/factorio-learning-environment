"""Template expansion, feasibility analysis, quantity and deadline sizing.

Generation is a pure deterministic function of the template version, template
id, generation seed, frozen context snapshot, and game-data version: identical
inputs yield byte-identical candidate pools on any platform.  Difficulty
scoring is injected through a model object so the generator never depends on
the rating implementation.

Recipe *facts* come exclusively from pinned game data via
:class:`~fle.envd.contract_features.ProductCatalog`; only difficulty policy
constants (reference rates, stage limits, safety factors) live here, and each
carries a version.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from typing import Any, Protocol

from pydantic import Field

from fle.envd.contract_features import (
    EPSILON_RATE,
    TICKS_PER_MINUTE,
    GameDataError,
    ProductCatalog,
    ProductFacts,
)
from fle.envd.models import (
    ADAPTIVE_BENCHMARK_SCHEMA_VERSION,
    CONTRACT_GENERATOR_VERSION,
    ContractContextSnapshot,
    ContractDifficultyFeatures,
    ContractEpochSpec,
    ContractMixtureClass,
    ContractTemplateSpec,
    WireModel,
)

GENERATION_POLICY_VERSION = "generation-policy-v2"

# Section 9.2 mixture weights.  Changing these requires a new benchmark
# version; they are policy, not calibration output.
MIXTURE_WEIGHTS: dict[ContractMixtureClass, float] = {
    "consolidation": 0.40,
    "frontier": 0.40,
    "stress": 0.20,
}

# Reference sustained rates (items/minute) a competent factory sustains at
# each progression band; used when the factory has no measured rate yet.
STAGE_REFERENCE_RATES: dict[int, float] = {
    0: 15.0,
    1: 60.0,
    2: 180.0,
    3: 400.0,
    4: 700.0,
    5: 1200.0,
}

# Upper bounds on required rates per band before the stress margin; requests
# beyond ``limit * stress_margin`` are rejected as pathological.
STAGE_RATE_LIMITS: dict[int, float] = {
    0: 90.0,
    1: 300.0,
    2: 900.0,
    3: 2000.0,
    4: 3500.0,
    5: 6000.0,
}
STRESS_MARGIN = 2.0

ANALYTIC_SAFETY_FACTOR = 2.5
PARALLEL_MACHINE_ASSUMPTION = 8

# Research feasibility: assume modest lab throughput when estimating whether
# missing technology fits inside a proposed deadline.
RESEARCH_SECONDS_PER_UNIT_ASSUMPTION = 30.0
MACHINE_SETUP_SECONDS_PER_CATEGORY = 120.0


class DifficultyModel(Protocol):
    def evaluate(
        self, features: ContractDifficultyFeatures
    ) -> tuple[float, float, float]:
        """Return (raw_difficulty, state_advantage, effective_difficulty)."""


def _canonical(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str
    ).encode()


def _stable_seed(*parts: Any) -> int:
    return int.from_bytes(hashlib.sha256(_canonical(parts)).digest()[:8], "big")


# ---------------------------------------------------------------------------
# Candidates
# ---------------------------------------------------------------------------


class ContractCandidate(WireModel):
    """One generated order proposal, including rejection verdicts."""

    schema_version: str = ADAPTIVE_BENCHMARK_SCHEMA_VERSION
    template_id: str
    mixture_class: ContractMixtureClass
    generation_seed: int
    item_name: str
    quantity: int = 0
    deadline_ticks: int = 0
    analytic_minimum_ticks: int = 0
    predicted_quantile_ticks: int | None = None
    features: ContractDifficultyFeatures | None = None
    raw_difficulty: float | None = None
    state_advantage: float | None = None
    effective_difficulty: float | None = None
    family: str = ""
    rejection_reason: str | None = None
    rejection_detail: dict[str, Any] = Field(default_factory=dict)

    @property
    def accepted(self) -> bool:
        return self.rejection_reason is None


# ---------------------------------------------------------------------------
# Template bank
# ---------------------------------------------------------------------------


class TemplateBank:
    """Versioned collection of order families.

    The official bank freezes private seeds plus an immutable copy of the
    template set; training banks may extend freely without touching scoring.
    """

    def __init__(
        self,
        templates: list[ContractTemplateSpec],
        bank_version: str = CONTRACT_GENERATOR_VERSION,
    ):
        ids = [t.template_id for t in templates]
        if len(ids) != len(set(ids)):
            raise ValueError("Template ids must be unique within a bank")
        self.bank_version = bank_version
        self._templates = {t.template_id: t for t in templates}
        self._ordered = list(templates)

    def __len__(self) -> int:
        return len(self._ordered)

    def all(self) -> list[ContractTemplateSpec]:
        return list(self._ordered)

    def get(self, template_id: str) -> ContractTemplateSpec:
        return self._templates[template_id]

    def by_mixture_class(
        self, mixture_class: ContractMixtureClass
    ) -> list[ContractTemplateSpec]:
        return [t for t in self._ordered if t.mixture_class == mixture_class]


def default_templates() -> TemplateBank:
    """The version-2 built-in bank.

    Products resolve against pinned game data at generation time; templates
    constrain families and bands rather than enumerating exact orders, so the
    official bank need not enumerate every possible context instantiation.
    """

    consolidation = [
        ContractTemplateSpec(
            template_id="consolidate-smelting",
            mixture_class="consolidation",
            families=("smelting",),
            products=("iron-plate", "copper-plate", "stone-brick"),
            stage_bands=(0, 1, 2, 3),
            pressure_multiplier_range=(1.5, 3.0),
            production_window_minutes_range=(15.0, 45.0),
        ),
        ContractTemplateSpec(
            template_id="consolidate-components",
            mixture_class="consolidation",
            families=("components", "circuits"),
            products=(
                "iron-gear-wheel",
                "copper-cable",
                "electronic-circuit",
            ),
            stage_bands=(1, 2, 3, 4, 5),
            pressure_multiplier_range=(1.3, 2.5),
            production_window_minutes_range=(10.0, 40.0),
        ),
        ContractTemplateSpec(
            template_id="consolidate-advanced-components",
            mixture_class="consolidation",
            families=("components", "circuits", "chemistry"),
            products=(
                "advanced-circuit",
                "plastic-bar",
                "battery",
            ),
            stage_bands=(2, 3, 4, 5),
            pressure_multiplier_range=(1.3, 2.5),
            production_window_minutes_range=(10.0, 40.0),
        ),
        ContractTemplateSpec(
            template_id="consolidate-processing-units",
            mixture_class="consolidation",
            families=("circuits",),
            products=("processing-unit",),
            stage_bands=(3, 4, 5),
            pressure_multiplier_range=(1.2, 2.0),
            production_window_minutes_range=(15.0, 45.0),
        ),
        ContractTemplateSpec(
            template_id="consolidate-logistics",
            mixture_class="consolidation",
            families=("logistics", "transport"),
            products=(
                "engine-unit",
                "rail",
            ),
            stage_bands=(2, 3, 4, 5),
            pressure_multiplier_range=(1.3, 2.2),
            production_window_minutes_range=(15.0, 45.0),
        ),
        ContractTemplateSpec(
            template_id="consolidate-robotics",
            mixture_class="consolidation",
            families=("logistics", "robots"),
            products=("electric-engine-unit", "flying-robot-frame"),
            stage_bands=(3, 4, 5),
            pressure_multiplier_range=(1.2, 2.0),
            production_window_minutes_range=(15.0, 45.0),
        ),
    ]
    frontier = [
        ContractTemplateSpec(
            template_id="frontier-early-automation",
            mixture_class="frontier",
            families=("smelting", "circuits"),
            products=("steel-plate", "electronic-circuit"),
            stage_bands=(1,),
            pressure_multiplier_range=(1.0, 1.4),
            production_window_minutes_range=(20.0, 50.0),
        ),
        ContractTemplateSpec(
            template_id="frontier-circuits",
            mixture_class="frontier",
            families=("circuits",),
            products=("advanced-circuit",),
            stage_bands=(2,),
            pressure_multiplier_range=(1.0, 1.6),
            production_window_minutes_range=(20.0, 60.0),
        ),
        ContractTemplateSpec(
            template_id="frontier-processing-units",
            mixture_class="frontier",
            families=("circuits",),
            products=("processing-unit",),
            stage_bands=(3,),
            pressure_multiplier_range=(1.0, 1.5),
            production_window_minutes_range=(25.0, 65.0),
        ),
        ContractTemplateSpec(
            template_id="frontier-chemistry",
            mixture_class="frontier",
            families=("chemistry", "components"),
            products=("sulfur", "plastic-bar", "battery", "lubricant-barrel"),
            stage_bands=(2,),
            pressure_multiplier_range=(1.0, 1.8),
            production_window_minutes_range=(20.0, 60.0),
        ),
        ContractTemplateSpec(
            template_id="frontier-rocket-chain",
            mixture_class="frontier",
            families=("rocket", "robots"),
            products=(
                "low-density-structure",
                "processing-unit",
                "rocket-fuel",
                "construction-robot",
                "logistic-robot",
            ),
            stage_bands=(3, 4, 5),
            pressure_multiplier_range=(1.0, 1.5),
            production_window_minutes_range=(30.0, 75.0),
        ),
        ContractTemplateSpec(
            template_id="frontier-military-power",
            mixture_class="frontier",
            families=("military", "power"),
            products=("uranium-rounds-magazine", "artillery-shell", "nuclear-fuel"),
            stage_bands=(2, 3, 4, 5),
            pressure_multiplier_range=(1.0, 1.6),
            production_window_minutes_range=(25.0, 70.0),
        ),
    ]
    stress = [
        ContractTemplateSpec(
            template_id="stress-throughput-scaling",
            mixture_class="stress",
            families=("smelting", "components", "circuits"),
            products=(
                "iron-plate",
                "copper-plate",
                "electronic-circuit",
                "steel-plate",
            ),
            stage_bands=(1, 2, 3, 4, 5),
            pressure_multiplier_range=(3.0, 5.0),
            production_window_minutes_range=(15.0, 35.0),
        ),
        ContractTemplateSpec(
            template_id="stress-power-logistics",
            mixture_class="stress",
            families=("structural", "logistics", "transport"),
            products=("concrete", "engine-unit", "electric-engine-unit", "rail"),
            stage_bands=(2, 3, 4, 5),
            pressure_multiplier_range=(2.2, 4.0),
            production_window_minutes_range=(12.0, 35.0),
        ),
    ]
    return TemplateBank(consolidation + frontier + stress)


DEFAULT_TEMPLATE_BANK = default_templates()


# ---------------------------------------------------------------------------
# Deterministic generation
# ---------------------------------------------------------------------------


def round_to_batch(quantity: float) -> int:
    """Snap quantities onto human-plausible batch granularities."""
    if quantity <= 0:
        return 1
    if quantity < 100:
        return max(int(round(quantity)), 1)
    if quantity < 1000:
        return max(int(round(quantity / 25.0)) * 25, 25)
    if quantity < 10000:
        return max(int(round(quantity / 100.0)) * 100, 100)
    return max(int(round(quantity / 500.0)) * 500, 500)


def baseline_rate(
    snapshot: ContractContextSnapshot, product_id: str, band: int
) -> float:
    """Section 9.3: max(existing rate, stage reference rate, epsilon)."""
    existing = max(
        snapshot.production_rates_300s.get(product_id, 0.0),
        snapshot.production_rates_60s.get(product_id, 0.0),
    )
    return max(existing, STAGE_REFERENCE_RATES.get(band, 30.0), EPSILON_RATE)


def analytic_feasibility(
    catalog: ProductCatalog,
    product_id: str,
    quantity: int,
    snapshot: ContractContextSnapshot,
) -> int:
    """Analytic minimum completion time in ticks (lower bound, optimistic)."""

    construction_seconds = catalog.analytic_minimum_seconds(
        product_id, quantity, parallel_machines=PARALLEL_MACHINE_ASSUMPTION
    )
    facts = catalog.require(product_id)
    researched = set(snapshot.technology_ids)
    missing_techs = sorted(facts.enabling_technologies - researched)
    research_seconds = sum(_technology_seconds(catalog, name) for name in missing_techs)
    missing_machine_categories = catalog.missing_machine_categories(
        product_id, snapshot.placed_entity_counts
    )
    machine_setup_seconds = (
        len(missing_machine_categories) * MACHINE_SETUP_SECONDS_PER_CATEGORY
    )
    return int(
        math.ceil(
            (construction_seconds + research_seconds + machine_setup_seconds) * 60.0
        )
    )


def _technology_seconds(catalog: ProductCatalog, tech_name: str) -> float:
    tech = catalog._source.technology(tech_name)
    if tech is None:
        # Unknown cost: assume one standard unit pack of work per unknown.
        return RESEARCH_SECONDS_PER_UNIT_ASSUMPTION
    return max(float(tech.unit_count) * float(tech.unit_energy_seconds), 0.0)


def _resolve_product(
    template: ContractTemplateSpec,
    rng: random.Random,
    catalog: ProductCatalog,
    snapshot: ContractContextSnapshot,
    mixture_class: ContractMixtureClass,
    band: int,
    *,
    force_unproduced: bool = False,
    exclude_products: set[str] | None = None,
) -> str | None:
    """Pick a product for the template under the mixture rule.

    Consolidation prefers currently-produced items; frontier looks one
    capability step beyond current production; stress samples unlocked
    high-volume products.  Returns None when no product satisfies the rule.
    """
    pool = [
        product for product in template.products if catalog.facts(product) is not None
    ]
    if not pool:
        return None

    produced = {
        item
        for item, rate in snapshot.production_rates_300s.items()
        if rate > EPSILON_RATE
    }

    if mixture_class == "consolidation":
        overlapping = [p for p in pool if p in produced]
        unproduced = [p for p in pool if p not in produced]
        if force_unproduced and unproduced:
            population = unproduced
        elif overlapping:
            # Consolidation remains biased toward installed production without
            # collapsing the candidate pool onto one product forever.
            population = overlapping * 3 + unproduced
        else:
            population = pool
    elif mixture_class == "frontier":
        unlocked = [
            p
            for p in pool
            if _recipe_is_reachable(catalog, p)
            and snapshot.inventory_counts.get(p, 0) >= 0
        ]
        beyond = [p for p in (unlocked or pool) if p not in produced]
        population = beyond or unlocked or pool
    else:  # stress
        population = [p for p in pool if _recipe_is_reachable(catalog, p)] or pool
    unsampled = [p for p in population if p not in (exclude_products or set())]
    if unsampled:
        population = unsampled
    return rng.choice(sorted(population)) if population else None


def _recipe_is_reachable(catalog: ProductCatalog, product: str) -> bool:
    """Return whether a prototype is usable now or researchable from the dump.

    Static prototype exports commonly report ``enabled=False`` for recipes
    that are initially locked.  A known enabling technology makes that a
    frontier candidate with an explicit research cost; only a disabled
    recipe with no enabling path is unreachable.
    """
    facts = catalog.facts(product)
    if facts is None:
        return False
    return facts.recipe.enabled is not False or bool(facts.enabling_technologies)


def generate_candidates(
    *,
    template: ContractTemplateSpec,
    generation_seed: int,
    context: ContractContextSnapshot,
    catalog: ProductCatalog,
    difficulty_model: DifficultyModel,
    remaining_session_ticks: int | None = None,
    recent_family_counts: dict[str, int] | None = None,
    family_repetition_cap: int = 3,
    predicted_quantile_ticks: int | None = None,
    calibration_envelope: dict[str, tuple[float, float]] | None = None,
    pool_size: int = 6,
) -> list[ContractCandidate]:
    """Expand one template into a bounded, deterministic candidate slice."""

    rng = random.Random(
        _stable_seed(
            template.template_version,
            template.template_id,
            generation_seed,
            context.state_digest,
            catalog.game_version,
        )
    )
    band = context_band(context, template)
    recent = recent_family_counts or {}
    candidates: list[ContractCandidate] = []
    sampled_products: set[str] = set()

    for index in range(pool_size):
        product = _resolve_product(
            template,
            rng,
            catalog,
            context,
            template.mixture_class,
            band,
            force_unproduced=(template.mixture_class == "consolidation" and index == 0),
            exclude_products=sampled_products,
        )
        if product is not None:
            sampled_products.add(product)
        base = dict(
            template_id=template.template_id,
            mixture_class=template.mixture_class,
            generation_seed=_stable_seed(generation_seed, index),
            item_name=product or "",
        )
        if product is None:
            candidates.append(
                ContractCandidate(**base, rejection_reason="absent_product")
            )
            continue

        try:
            facts: ProductFacts = catalog.require(product)
        except GameDataError:
            candidates.append(
                ContractCandidate(**base, rejection_reason="absent_product")
            )
            continue

        pressure_lo, pressure_hi = template.pressure_multiplier_range
        window_lo, window_hi = template.production_window_minutes_range
        pressure = rng.uniform(pressure_lo, pressure_hi)
        window_minutes = rng.uniform(window_lo, window_hi)

        target_rate = baseline_rate(context, product, band) * pressure
        quantity = round_to_batch(target_rate * window_minutes)
        analytic_ticks = analytic_feasibility(catalog, product, quantity, context)
        guard_ticks = max(
            int(analytic_ticks * ANALYTIC_SAFETY_FACTOR),
            predicted_quantile_ticks or 0,
        )
        deadline = max(guard_ticks, int(window_minutes * TICKS_PER_MINUTE))
        deadline = int(deadline * rng.uniform(1.05, 1.35))
        features = _features_for(context, product, quantity, deadline, catalog, band)

        reject = _rejection_reason(
            catalog=catalog,
            context=context,
            facts=facts,
            product=product,
            quantity=quantity,
            deadline_ticks=deadline,
            analytic_minimum_ticks=analytic_ticks,
            remaining_session_ticks=remaining_session_ticks,
            template=template,
            recent_family_counts=recent,
            family_repetition_cap=family_repetition_cap,
            calibration_envelope=calibration_envelope,
            features=features,
        )
        if reject is not None:
            reason, detail = reject
            candidates.append(
                ContractCandidate(
                    **base,
                    quantity=quantity,
                    deadline_ticks=deadline,
                    analytic_minimum_ticks=analytic_ticks,
                    family=facts.recipe.category,
                    rejection_reason=reason,
                    rejection_detail=detail,
                )
            )
            continue

        raw, advantage, effective = _evaluate_difficulty(
            difficulty_model, features, template.template_id
        )
        candidates.append(
            ContractCandidate(
                **base,
                quantity=quantity,
                deadline_ticks=deadline,
                analytic_minimum_ticks=analytic_ticks,
                predicted_quantile_ticks=predicted_quantile_ticks,
                features=features,
                raw_difficulty=raw,
                state_advantage=advantage,
                effective_difficulty=effective,
                family=facts.recipe.category,
            )
        )

    return candidates


def context_band(
    context: ContractContextSnapshot, template: ContractTemplateSpec
) -> int:
    """Target band: frontier probes one step ahead, other work stays current."""

    current = max(min(_snapshot_band(context), 5), 0)
    if template.mixture_class == "frontier":
        return min(current + 1, 5)
    return current


def _evaluate_difficulty(
    difficulty_model: DifficultyModel,
    features: ContractDifficultyFeatures,
    template_id: str,
) -> tuple[float, float, float]:
    """Pass template identity when supported, preserving older model hooks."""
    try:
        return difficulty_model.evaluate(features, template_id=template_id)
    except TypeError as exc:
        # Training/test models written against the original one-argument
        # protocol remain valid; do not hide errors from the actual evaluator.
        if "template_id" not in str(exc):
            raise
        return difficulty_model.evaluate(features)


_SNAPSHOT_BAND_CACHE: dict[str, int] = {}


def _snapshot_band(context: ContractContextSnapshot) -> int:
    from fle.envd.contract_features import classify_progression_band

    cached = _SNAPSHOT_BAND_CACHE.get(context.state_digest)
    if cached is None:
        cached = classify_progression_band(context)
        if len(_SNAPSHOT_BAND_CACHE) > 512:
            _SNAPSHOT_BAND_CACHE.clear()
        _SNAPSHOT_BAND_CACHE[context.state_digest] = cached
    return cached


def _features_for(
    context: ContractContextSnapshot,
    product: str,
    quantity: int,
    deadline_ticks: int,
    catalog: ProductCatalog,
    band: int,
) -> ContractDifficultyFeatures:
    from fle.envd.contract_features import extract_difficulty_features

    return extract_difficulty_features(
        snapshot=context,
        product_id=product,
        quantity=quantity,
        deadline_ticks=deadline_ticks,
        catalog=catalog,
        stage_band=band,
    )


def _rejection_reason(
    *,
    catalog: ProductCatalog,
    context: ContractContextSnapshot,
    facts: ProductFacts,
    product: str,
    quantity: int,
    deadline_ticks: int,
    analytic_minimum_ticks: int,
    remaining_session_ticks: int | None,
    template: ContractTemplateSpec,
    recent_family_counts: dict[str, int],
    family_repetition_cap: int,
    calibration_envelope: dict[str, tuple[float, float]] | None,
    features: ContractDifficultyFeatures,
) -> tuple[str, dict[str, Any]] | None:
    """Section 9.4 rejection policy; returns (reason, detail) or None."""

    if facts.recipe.enabled is False and not facts.enabling_technologies:
        return (
            "recipe_locked",
            {"reason": "no_known_enabling_technology"},
        )

    if features.stage_band not in template.stage_bands:
        return (
            "stage_band_unsupported",
            {
                "stage_band": features.stage_band,
                "supported_stage_bands": list(template.stage_bands),
            },
        )

    if analytic_minimum_ticks > deadline_ticks:
        return (
            "infeasible_analytic",
            {
                "analytic_minimum_ticks": analytic_minimum_ticks,
                "deadline_ticks": deadline_ticks,
            },
        )

    stage_limit = STAGE_RATE_LIMITS.get(features.stage_band, STAGE_RATE_LIMITS[5])
    required_rate = quantity / max(deadline_ticks / TICKS_PER_MINUTE, EPSILON_RATE)
    if required_rate > stage_limit * STRESS_MARGIN:
        return (
            "rate_exceeds_stage_limit",
            {
                "required_rate_per_minute": required_rate,
                "stage_limit": stage_limit,
                "stress_margin": STRESS_MARGIN,
            },
        )

    # Section 9.4: uncommitted inventory already covering the order makes it
    # trivial.  (Logistics-constraint templates may bypass this via a
    # template flag in a future bank version.)
    inventory_ratio = context.inventory_counts.get(product, 0) / max(quantity, 1)
    if inventory_ratio >= 1.0:
        return (
            "inventory_already_covers",
            {"inventory_coverage_ratio": round(inventory_ratio, 4)},
        )

    family = facts.recipe.category
    if recent_family_counts.get(family, 0) >= family_repetition_cap:
        return (
            "family_repetition_cap",
            {
                "family": family,
                "count": recent_family_counts[family],
                "cap": family_repetition_cap,
            },
        )

    if remaining_session_ticks is not None and deadline_ticks > remaining_session_ticks:
        return (
            "exceeds_session_horizon",
            {
                "deadline_ticks": deadline_ticks,
                "remaining_session_ticks": remaining_session_ticks,
            },
        )

    if calibration_envelope is not None:
        violations = envelope_violations(calibration_envelope, features)
        if violations:
            return ("outside_calibration_envelope", {"violations": violations})

    return None


def envelope_violations(
    supported_ranges: dict[str, tuple[float, float]],
    features: ContractDifficultyFeatures,
) -> list[str]:
    """Feature dimensions outside their supported calibration ranges."""
    from fle.envd.contract_rating import _feature_vector

    values = _feature_vector(features, tuple(supported_ranges))
    violations: list[str] = []
    for dimension, (low, high) in supported_ranges.items():
        if dimension not in values:
            continue
        value = values[dimension]
        if isinstance(value, (int, float)) and not (low <= value <= high):
            violations.append(dimension)
    return violations


def build_epoch_spec(
    *,
    session_id: str,
    epoch_index: int,
    selection_seed: int,
    candidate: ContractCandidate,
    context: ContractContextSnapshot,
    benchmark_version: str,
    calibration_version: str,
    intervention_budget: int | None = None,
) -> ContractEpochSpec:
    """Commit one accepted candidate into an immutable epoch specification."""
    if not candidate.accepted or candidate.features is None:
        raise ValueError("Cannot commit a rejected candidate")
    return ContractEpochSpec.create(
        schema_version=ADAPTIVE_BENCHMARK_SCHEMA_VERSION,
        benchmark_version=benchmark_version,
        calibration_version=calibration_version,
        session_id=session_id,
        epoch_index=epoch_index,
        template_id=candidate.template_id,
        generation_seed=candidate.generation_seed,
        selection_seed=selection_seed,
        item_name=candidate.item_name,
        quantity=candidate.quantity,
        deadline_ticks=candidate.deadline_ticks,
        intervention_budget=intervention_budget,
        context=context,
        features=candidate.features,
        raw_difficulty=float(candidate.raw_difficulty or 0.0),
        state_advantage=float(candidate.state_advantage or 0.0),
        effective_difficulty=float(candidate.effective_difficulty or 0.0),
    )


__all__ = [
    "ANALYTIC_SAFETY_FACTOR",
    "ContractCandidate",
    "DEFAULT_TEMPLATE_BANK",
    "DifficultyModel",
    "GENERATION_POLICY_VERSION",
    "MIXTURE_WEIGHTS",
    "STAGE_RATE_LIMITS",
    "STAGE_REFERENCE_RATES",
    "STRESS_MARGIN",
    "TemplateBank",
    "analytic_feasibility",
    "baseline_rate",
    "build_epoch_spec",
    "default_templates",
    "envelope_violations",
    "generate_candidates",
    "round_to_batch",
]
