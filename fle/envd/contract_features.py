"""Passive context snapshots, progression bands, and difficulty features.

Everything here is read-only with respect to the simulation: capture may
query authoritative game state but never mutates it.  All expensive game-data
facts (recipe graph topology, enabling technologies, machine categories) are
derived once per product through memoized tables so candidate generation over
bounded pools stays pure dictionary arithmetic.

Determinism contract: given identical snapshots and an identical pinned
catalog, every function is a pure function -- no clocks, no randomness, no
game queries beyond the initial capture.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Iterable

from fle.envd.models import (
    CONTRACT_FEATURES_VERSION,
    ADAPTIVE_BENCHMARK_SCHEMA_VERSION,
    ContractContextSnapshot,
    ContractDifficultyFeatures,
    canonical_hash,
)

TICKS_PER_MINUTE = 3600
EPSILON_RATE = 1e-9

# Representative machine power draw (kW) per crafting category, used only for
# the coarse ``estimated_power_fraction`` feature.  Static, versioned with the
# features schema; calibration absorbs systematic error.
_CATEGORY_POWER_KW: dict[str, float] = {
    "crafting": 75.0,  # assembling machine 1
    "advanced-crafting": 375.0,  # assembling machine 3 class
    "smelting": 90.0,
    "chemistry": 210.0,
    "oil-processing": 420.0,
    "centrifuging": 350.0,
    "electromagnetics": 750.0,
    "cryogenics": 1200.0,
    "agriculture": 300.0,
    "metallurgy": 190.0,
    "electronics": 375.0,
    "fuel-refining": 420.0,
}

# Crafting-category -> representative placing entity names.  A category counts
# as "missing" when none of these entities exist in the factory census.
_CATEGORY_MACHINES: dict[str, tuple[str, ...]] = {
    "crafting": (
        "assembling-machine-1",
        "assembling-machine-2",
        "assembling-machine-3",
    ),
    "advanced-crafting": ("assembling-machine-2", "assembling-machine-3"),
    "smelting": ("stone-furnace", "steel-furnace", "electric-furnace"),
    "chemistry": ("chemical-plant",),
    "oil-processing": ("oil-refinery",),
    "centrifuging": ("centrifuge",),
    "electromagnetics": ("electromagnetic-plant",),
    "cryogenics": ("cryogenic-plant",),
    "agriculture": ("biocham",),
    "metallurgy": ("foundry",),
    "electronics": (
        "assembling-machine-2",
        "assembling-machine-3",
        "electromagnetic-plant",
    ),
    "fuel-refining": ("oil-refinery", "chemical-plant"),
    "rocket-building": ("rocket-silo",),
}

# Machine categories implied by entity types when a live census reports types
# rather than categories (belt/logistics coverage heuristics).
_TRANSPORT_HEAVY_THRESHOLD = 30.0  # items/minute where trains become relevant


# ---------------------------------------------------------------------------
# Pinned game data
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecipeFacts:
    """Normalized, immutable facts about one recipe."""

    name: str
    category: str
    energy_seconds: float
    ingredients: tuple[tuple[str, float], ...]
    products: tuple[tuple[str, float], ...]
    # None when the data source cannot determine unlock state; False is the
    # authoritative signal that the force has not researched the recipe.
    enabled: bool | None = None


@dataclass(frozen=True)
class TechnologyFacts:
    """Normalized facts about one technology."""

    name: str
    prerequisites: tuple[str, ...]
    unlocked_recipes: tuple[str, ...]
    unit_count: int
    unit_energy_seconds: float


def _num(value: Any, default: float = 0.0) -> float:
    """Defensively parse Lua/RCON numbers that may arrive as strings."""
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        text = str(value).strip().strip('"')
        return float(text)
    except ValueError:
        return default


def _clean_name(value: Any) -> str:
    text = str(value).strip()
    return text.strip('"')


class GameDataError(RuntimeError):
    """Pinned game data was absent or malformed for a benchmark product."""


class RecipeDataSource:
    """Read-only accessor over pinned Factorio prototypes.

    Subclasses adapt live RCON namespaces, exported dumps, or test fixtures.
    Lookups are cached after first success; failures raise immediately so
    generation can reject the candidate instead of guessing.
    """

    def __init__(self, game_version: str = "unknown"):
        self._game_version = game_version
        self._recipes: dict[str, RecipeFacts | None] = {}
        self._technologies: dict[str, TechnologyFacts] = {}

    @property
    def game_version(self) -> str:
        return self._game_version

    def recipe(self, item_name: str) -> RecipeFacts | None:
        if item_name not in self._recipes:
            self._recipes[item_name] = self._load_recipe(item_name)
        return self._recipes[item_name]

    def technology(self, name: str) -> TechnologyFacts | None:
        if name not in self._technologies:
            self._technologies[name] = self._load_technology(name)
        return self._technologies[name]

    def _load_recipe(self, item_name: str) -> RecipeFacts | None:
        raise NotImplementedError

    def _load_technology(self, name: str) -> TechnologyFacts | None:
        return None

    def recipes_for_technology(self, tech_name: str) -> tuple[str, ...]:
        tech = self.technology(tech_name)
        return tech.unlocked_recipes if tech else ()


class StaticRecipeDataSource(RecipeDataSource):
    """In-memory source for tests and offline calibration fixtures."""

    def __init__(
        self,
        recipes: Iterable[dict[str, Any]],
        technologies: Iterable[dict[str, Any]] = (),
        game_version: str = "test-data",
    ):
        super().__init__(game_version=game_version)
        self._raw_recipes = {r["name"]: r for r in recipes}
        self._raw_technologies = {t["name"]: t for t in technologies}
        self._tech_by_recipe: dict[str, list[str]] = {}
        for tech in self._raw_technologies.values():
            for recipe_name in tech.get("unlocked_recipes", ()):
                self._tech_by_recipe.setdefault(recipe_name, []).append(tech["name"])

    def _load_recipe(self, item_name: str) -> RecipeFacts | None:
        raw = self._raw_recipes.get(item_name)
        if raw is None:
            return None
        return RecipeFacts(
            name=_clean_name(raw["name"]),
            category=str(raw.get("category", "crafting")),
            energy_seconds=_num(raw.get("energy"), 0.5),
            ingredients=tuple(
                sorted(
                    (_clean_name(i["name"]), _num(i["amount"]))
                    for i in raw.get("ingredients", ())
                )
            ),
            products=tuple(
                sorted(
                    (_clean_name(p["name"]), _num(p["amount"]))
                    for p in raw.get("products", ())
                )
            ),
            enabled=(bool(raw["enabled"]) if "enabled" in raw else None),
        )

    def _load_technology(self, name: str) -> TechnologyFacts | None:
        raw = self._raw_technologies.get(name)
        if raw is None:
            return None
        return TechnologyFacts(
            name=_clean_name(raw["name"]),
            prerequisites=tuple(sorted(raw.get("prerequisites", ()))),
            unlocked_recipes=tuple(sorted(raw.get("unlocked_recipes", ()))),
            unit_count=int(_num(raw.get("unit_count"), 1)),
            unit_energy_seconds=_num(raw.get("unit_energy"), 30.0),
        )


class NamespaceRecipeDataSource(RecipeDataSource):
    """Live source backed by an FLE namespace (RCON-backed prototypes).

    Recipe lookups are one RCON round-trip per product, cached permanently;
    technology facts come from a single research-state pull shared with the
    telemetry cache.
    """

    def __init__(self, namespace: Any, game_version: str = "2.0.73"):
        super().__init__(game_version=game_version)
        self._namespace = namespace
        self._research_state = None

    def _research(self):
        if self._research_state is None:
            self._research_state = self._namespace._save_research_state()
        return self._research_state

    def _load_recipe(self, item_name: str) -> RecipeFacts | None:
        try:
            raw = self._jsonable(self._namespace.get_prototype_recipe(item_name))
        except Exception:
            return None
        if not isinstance(raw, dict) or "ingredients" not in raw:
            return None
        ingredients = raw.get("ingredients") or []
        if isinstance(ingredients, dict):  # slpp index-keyed arrays
            ingredients = [ingredients[key] for key in sorted(ingredients, key=int)]
        products = raw.get("products") or []
        if isinstance(products, dict):
            products = [products[key] for key in sorted(products, key=int)]
        return RecipeFacts(
            name=_clean_name(raw.get("name", item_name)),
            category=_clean_name(raw.get("category", "crafting")),
            energy_seconds=_num(raw.get("energy"), 0.5),
            ingredients=tuple(
                sorted((_clean_name(i["name"]), _num(i["amount"])) for i in ingredients)
            ),
            products=tuple(
                sorted(
                    (_clean_name(p["name"]), _num(p["amount"], 1.0)) for p in products
                )
            ),
            enabled=(
                bool(raw.get("enabled"))
                if isinstance(raw.get("enabled"), bool)
                else None
            ),
        )

    def _load_technology(self, name: str) -> TechnologyFacts | None:
        state = self._research()
        tech = state.technologies.get(name) if state else None
        if tech is None:
            return None
        return TechnologyFacts(
            name=name,
            prerequisites=tuple(sorted(getattr(tech, "prerequisites", ()))),
            unlocked_recipes=self._recipes_unlocked_by(name),
            unit_count=int(getattr(tech, "research_unit_count", 1) or 1),
            unit_energy_seconds=float(
                getattr(tech, "research_unit_energy", 30.0) or 30.0
            ),
        )

    def _recipes_unlocked_by(self, tech_name: str) -> tuple[str, ...]:
        # Live unlock lists are not exposed per technology through the FLE
        # namespace; generation treats unknown unlocks conservatively (the
        # recipe's own enabling technology must be researched, which is the
        # dominant difficulty signal anyway).
        return ()

    @staticmethod
    def _jsonable(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if hasattr(value, "to_dict"):
            return value.to_dict()
        return value


# ---------------------------------------------------------------------------
# Product catalog: memoized derived facts
# ---------------------------------------------------------------------------


@dataclass
class ProductFacts:
    """Transitive supply-chain facts for one product."""

    product_id: str
    recipe: RecipeFacts
    depth: int
    craft_time_seconds: float  # total chain seconds for ONE unit (sum/energy)
    enabling_technologies: frozenset[str]
    machine_categories: frozenset[str]
    intermediates: frozenset[str]
    fluid_ingredients: bool
    cyclic: bool


class ProductCatalog:
    """Memoized derivation of supply-chain facts over a recipe source.

    Graph traversal happens once per product per process lifetime; repeated
    candidate evaluation performs dictionary lookups only.
    """

    def __init__(self, source: RecipeDataSource):
        self._source = source
        self._facts: dict[str, ProductFacts | None] = {}
        self._depth_memo: dict[str, int] = {}
        self._tech_closure: dict[str, frozenset[str]] = {}
        self._intermediates: dict[str, frozenset[str]] = {}
        self._chain_seconds: dict[str, float] = {}

    @property
    def game_version(self) -> str:
        return self._source.game_version

    def facts(self, product_id: str) -> ProductFacts | None:
        if product_id not in self._facts:
            self._facts[product_id] = self._derive(product_id)
        return self._facts[product_id]

    def require(self, product_id: str) -> ProductFacts:
        facts = self.facts(product_id)
        if facts is None:
            raise GameDataError(
                f"Product {product_id!r} is absent from pinned game data "
                f"(version {self.game_version})"
            )
        return facts

    def _derive(self, product_id: str) -> ProductFacts | None:
        recipe = self._source.recipe(product_id)
        if recipe is None:
            return None
        visited: set[str] = set()
        cyclic = self._has_cycle(product_id, visited, stack=set())
        techs = self.enabling_technologies(product_id)
        categories = self.machine_categories(product_id)
        return ProductFacts(
            product_id=product_id,
            recipe=recipe,
            depth=self.depth(product_id),
            craft_time_seconds=self.chain_craft_seconds(product_id),
            enabling_technologies=techs,
            machine_categories=categories,
            intermediates=self.intermediate_items(product_id),
            fluid_ingredients=any(
                name.startswith("fluid-")
                or "barrel" in name
                or name in ("crude-oil", "water", "steam", "lubricant")
                for name, _ in self._all_ingredients(product_id)
            ),
            cyclic=cyclic,
        )

    # -- traversals ---------------------------------------------------------

    def _recipe_or_none(self, item: str) -> RecipeFacts | None:
        return self._source.recipe(item)

    def _all_ingredients(self, product_id: str) -> list[tuple[str, float]]:
        recipe = self._source.recipe(product_id)
        if recipe is None:
            return []
        collected: list[tuple[str, float]] = list(recipe.ingredients)
        seen = {product_id}
        frontier = [name for name, _ in recipe.ingredients]
        while frontier:
            current = frontier.pop()
            if current in seen:
                continue
            seen.add(current)
            sub = self._source.recipe(current)
            if sub is None:
                continue
            collected.extend(sub.ingredients)
            frontier.extend(name for name, _ in sub.ingredients)
        return collected

    def _has_cycle(self, item: str, visited: set[str], stack: set[str]) -> bool:
        if item in stack:
            return True
        if item in visited:
            return False
        visited.add(item)
        stack.add(item)
        recipe = self._source.recipe(item)
        result = False
        if recipe is not None:
            for name, _ in recipe.ingredients:
                if self._source.recipe(name) is not None:
                    if self._has_cycle(name, visited, stack):
                        result = True
                        break
        stack.discard(item)
        return result

    def depth(self, product_id: str, _seen: frozenset[str] = frozenset()) -> int:
        """Longest ingredient-chain depth; back-edges add nothing."""
        if product_id in self._depth_memo:
            return self._depth_memo[product_id]
        recipe = self._source.recipe(product_id)
        if recipe is None:
            return 0
        best = 0
        next_seen = _seen | {product_id}
        for name, _ in recipe.ingredients:
            if name in next_seen:
                continue  # cyclic/catalyst edge: contributes no depth
            best = max(best, self.depth(name, next_seen))
        result = best + 1
        self._depth_memo[product_id] = result
        return result

    def chain_craft_seconds(
        self, product_id: str, _visiting: frozenset[str] = frozenset()
    ) -> float:
        """Total machine-seconds for one final unit along the deepest chain.

        Cyclic edges contribute nothing (catalytic loops are bounded by the
        visiting set), keeping this a strict lower bound.
        """
        if product_id in _visiting:
            return 0.0
        if not _visiting and product_id in self._chain_seconds:
            return self._chain_seconds[product_id]
        recipe = self._source.recipe(product_id)
        if recipe is None:
            return 0.0
        total = recipe.energy_seconds
        yield_per_craft = max(
            (amount for name, amount in recipe.products if name == product_id),
            default=1.0,
        )
        worst_sub = 0.0
        next_visiting = _visiting | {product_id}
        for name, amount in recipe.ingredients:
            sub_recipe = self._source.recipe(name)
            if sub_recipe is None or name in next_visiting:
                continue  # raw resource or cyclic edge
            sub_total = self.chain_craft_seconds(name, next_visiting)
            worst_sub = max(worst_sub, sub_total * amount / yield_per_craft)
        result = total + worst_sub
        if not _visiting:
            self._chain_seconds[product_id] = result
        return result

    def enabling_technologies(self, product_id: str) -> frozenset[str]:
        """Technologies required to unlock the full chain."""
        cached = self._tech_closure.get(product_id)
        if cached is not None:
            return cached
        recipe = self._source.recipe(product_id)
        techs: set[str] = set()
        if recipe is not None:
            direct = self._enabling_for_item(product_id)
            techs.update(direct)
            frontier = [name for name, _ in recipe.ingredients]
            seen = {product_id}
            while frontier:
                current = frontier.pop()
                if current in seen:
                    continue
                seen.add(current)
                techs.update(self._enabling_for_item(current))
                sub = self._source.recipe(current)
                if sub is not None:
                    frontier.extend(name for name, _ in sub.ingredients)
        closure = frozenset(techs)
        self._tech_closure[product_id] = closure
        return closure

    def _enabling_for_item(self, item: str) -> set[str]:
        found: set[str] = set()

        def walk_prereqs(tech_name: str, seen: set[str]) -> None:
            if tech_name in seen:
                return
            seen.add(tech_name)
            found.add(tech_name)
            tech = self._source.technology(tech_name)
            if tech is None:
                return
            for prereq in tech.prerequisites:
                walk_prereqs(prereq, seen)

        # Direct lookup path: sources that expose recipe->tech mappings.
        if hasattr(self._source, "_tech_by_recipe"):
            for tech_name in getattr(self._source, "_tech_by_recipe").get(item, ()):
                found.add(tech_name)
                walk_prereqs(tech_name, set())
        else:
            # Conservative fallback: scan technologies once for the recipe.
            for tech_name, tech in list(self._iter_technologies()):
                if item in tech.unlocked_recipes:
                    found.add(tech_name)
                    walk_prereqs(tech_name, set())
        return found

    def missing_machine_categories(
        self, product_id: str, placed_entity_counts: dict[str, int]
    ) -> frozenset[str]:
        """Crafting categories whose representative infrastructure is absent."""

        facts = self.require(product_id)
        return frozenset(
            category
            for category in facts.machine_categories
            if not any(
                placed_entity_counts.get(machine, 0) > 0
                for machine in _CATEGORY_MACHINES.get(category, ())
            )
        )

    def _iter_technologies(self):
        # Hook for sources able to enumerate technologies; the live source
        # cannot, so this yields nothing there.
        return ()

    def machine_categories(self, product_id: str) -> frozenset[str]:
        recipe = self._source.recipe(product_id)
        if recipe is None:
            return frozenset()
        categories = {recipe.category}
        frontier = [name for name, _ in recipe.ingredients]
        seen = {product_id}
        while frontier:
            current = frontier.pop()
            if current in seen:
                continue
            seen.add(current)
            sub = self._source.recipe(current)
            if sub is not None:
                categories.add(sub.category)
                frontier.extend(name for name, _ in sub.ingredients)
        return frozenset(categories & set(_CATEGORY_MACHINES))

    def intermediate_items(self, product_id: str) -> frozenset[str]:
        cached = self._intermediates.get(product_id)
        if cached is not None:
            return cached
        recipe = self._source.recipe(product_id)
        if recipe is None:
            return frozenset()
        items: set[str] = set()
        frontier = [(name, False) for name, _ in recipe.ingredients]
        seen = {product_id}
        while frontier:
            current, is_intermediate = frontier.pop()
            if current in seen:
                continue
            seen.add(current)
            sub = self._source.recipe(current)
            if sub is not None:
                if is_intermediate or current != product_id:
                    items.add(current)
                frontier.extend((name, True) for name, _ in sub.ingredients)
        result = frozenset(items - {product_id})
        self._intermediates[product_id] = result
        return result

    def analytic_minimum_seconds(
        self, product_id: str, quantity: int, *, parallel_machines: int = 8
    ) -> float:
        """Lower bound on production time for ``quantity`` units.

        Assumes perfect existing infrastructure and bounded parallelism;
        intentionally optimistic because it is a floor, not an estimate.
        """

        facts = self.require(product_id)
        per_unit_chain = facts.craft_time_seconds
        return quantity * per_unit_chain / max(parallel_machines, 1)


# ---------------------------------------------------------------------------
# Snapshot digests and watermarks
# ---------------------------------------------------------------------------


def compute_state_digest(snapshot_fields: dict[str, Any]) -> str:
    """Canonical digest of the semantically-relevant snapshot content.

    Excludes volatile bookkeeping (schema/session/epoch) so two captures of
    an unchanged world hash identically.
    """
    relevant = {
        key: value
        for key, value in snapshot_fields.items()
        if key not in ("schema_version", "session_id", "epoch_index")
    }
    return canonical_hash(relevant)


def watermark_is_monotonic(
    previous: tuple[str, int, int, str] | None,
    candidate: tuple[str, int, int, str],
) -> bool:
    """Reject snapshots older than the prior finalized epoch."""
    if previous is None:
        return True
    same_session = previous[0] == candidate[0]
    advances = candidate[1] > previous[1] or (
        candidate[1] == previous[1] and candidate[2] >= previous[2]
    )
    return same_session and advances


# ---------------------------------------------------------------------------
# Passive capture
# ---------------------------------------------------------------------------


def capture_context_snapshot(
    namespace: Any,
    *,
    session_id: str,
    epoch_index: int,
    captured_tick: int,
    map_seed_hash: str,
    game_version: str = "2.0.73",
    prior_watermark: tuple[str, int, int, str] | None = None,
    flow_history: list[tuple[int, dict[str, float]]] | None = None,
    observed_unlocked_recipes: Iterable[str] = (),
) -> ContractContextSnapshot:
    """Freeze passive factory measurements into an immutable snapshot.

    ``flow_history`` carries recent cumulative-output samples
    ``(tick, output_counts)`` maintained by the caller (backend); rates are
    computed as O(items) deltas without running simulation.
    ``observed_unlocked_recipes`` is the caller's session cache of recipe
    names whose live query returned enabled, merged with items showing
    nonzero production.  Raises ``ValueError`` when the watermark regresses.
    """

    from fle.envd.models import ContractContextSnapshot

    research = namespace._save_research_state()
    technology_ids = tuple(
        sorted(name for name, tech in research.technologies.items() if tech.researched)
    )
    inventory = {
        str(item): int(count)
        for item, count in (namespace.inspect_inventory() or {}).items()
        if count
    }
    engine = _objective_engine_telemetry(namespace)
    placed_entity_counts = _entity_counts(namespace, engine)
    pollution_raw = engine.get("pollution_total")
    evolution_raw = engine.get("evolution_factor")

    outputs_now = {
        str(item): float(count)
        for item, count in (engine.get("produced") or {}).items()
    }
    # Caller history plus the fresh sample; same-tick duplicates collapse.
    prior_history = [
        sample for sample in (flow_history or []) if sample[0] < captured_tick
    ]
    samples = prior_history + [(captured_tick, outputs_now)]
    rates_60s = _window_rate(samples, 3600)
    rates_300s = _window_rate(samples, 18000)

    power = _power_summary(namespace)

    fields: dict[str, Any] = {
        "captured_tick": int(captured_tick),
        "technology_ids": technology_ids,
        "unlocked_recipe_ids": _unlocked_recipes(engine, observed_unlocked_recipes),
        "inventory_counts": inventory,
        "placed_entity_counts": placed_entity_counts,
        "production_rates_60s": rates_60s,
        "production_rates_300s": rates_300s,
        "power_capacity_kw": power[0],
        "power_utilization": power[1],
        "logistic_network_count": _logistic_network_count(namespace),
        "train_stop_count": placed_entity_counts.get("train-stop", 0),
        "pollution_total": (
            float(pollution_raw) if isinstance(pollution_raw, (int, float)) else None
        ),
        "evolution_factor": (
            float(evolution_raw) if isinstance(evolution_raw, (int, float)) else None
        ),
        "map_seed_hash": map_seed_hash,
    }

    candidate_watermark = (
        session_id,
        epoch_index,
        int(captured_tick),
        "",
    )
    if not watermark_is_monotonic(prior_watermark, candidate_watermark):
        raise ValueError(
            f"Context capture regressed: {candidate_watermark[:3]} follows "
            f"{prior_watermark[:3]}"
        )

    fields["state_digest"] = hashlib.sha256(
        json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:32]

    snapshot = ContractContextSnapshot(
        schema_version=ADAPTIVE_BENCHMARK_SCHEMA_VERSION,
        session_id=session_id,
        epoch_index=epoch_index,
        **fields,
    )
    return snapshot


def _objective_engine_telemetry(namespace: Any) -> dict[str, Any]:
    getter = getattr(namespace, "_objective_telemetry", None)
    if getter is None:
        return {}
    try:
        value = getter(False)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _entity_counts(namespace: Any, engine: dict[str, Any]) -> dict[str, int]:
    """Return a flat entity census, retaining old telemetry compatibility."""
    census_getter = getattr(namespace, "_entity_census", None)
    if census_getter is not None:
        try:
            response = census_getter() or {}
            census = response.get("census") or {}
            return {
                str(name): sum(int(count) for count in (statuses or {}).values())
                for name, statuses in census.items()
            }
        except Exception:
            pass
    return {
        str(name): int(count)
        for name, count in (engine.get("entity_counts") or {}).items()
    }


def _unlocked_recipes(
    engine: dict[str, Any], observed_unlocked: Iterable[str]
) -> tuple[str, ...]:
    """Recipes with demonstrated or observed unlock state.

    Union of the caller's session cache (live recipe queries that reported
    enabled) and items with nonzero recorded production.  This is a
    conservative, evidence-based subset -- generation still verifies the
    authoritative live flag before committing any candidate.
    """
    unlocked = set(observed_unlocked)
    for item in engine.get("produced") or {}:
        if float(engine["produced"][item] or 0) > 0:
            unlocked.add(str(item))
    return tuple(sorted(unlocked))


def _window_rate(
    history: list[tuple[int, dict[str, float]]], window_ticks: int
) -> dict[str, float]:
    """Per-minute production deltas between now and now-window."""
    if len(history) < 2:
        return {}
    ordered = sorted(history, key=lambda sample: sample[0])
    now_tick, now_counts = ordered[-1]
    cutoff = now_tick - window_ticks
    base_counts: dict[str, float] | None = None
    base_tick: int | None = None
    for tick, counts in ordered:
        if tick <= cutoff:
            base_counts = counts
            base_tick = tick
    if base_counts is None:
        # A short history still gives a valid delta, but only from its oldest
        # available sample.  Falling back to ``now`` would divide by epsilon
        # and turn cumulative totals into absurd rates.
        base_tick, base_counts = ordered[0]
    span_ticks = now_tick - base_tick
    if span_ticks <= 0:
        return {}
    span_minutes = span_ticks / TICKS_PER_MINUTE
    rates = {
        item: max((now_counts.get(item, 0.0) - amount), 0.0) / span_minutes
        for item, amount in base_counts.items()
    }
    for item, amount in now_counts.items():
        if item not in rates:
            rates[item] = amount / span_minutes
    return {item: round(rate, 4) for item, rate in rates.items() if rate > 0}


def _power_summary(namespace: Any) -> tuple[float, float]:
    """(capacity_kw, utilization) from electric network statistics."""
    getter = getattr(namespace, "_electric_network_stats", None)
    if getter is None:
        return (0.0, 0.0)
    try:
        stats = getter() or {}
        capacity = float(stats.get("capacity_kw") or 0.0)
        usage = float(stats.get("usage_kw") or 0.0)
        utilization = usage / capacity if capacity > 0 else 0.0
        return (capacity, min(utilization, 1.0))
    except Exception:
        return (0.0, 0.0)


def _logistic_network_count(namespace: Any) -> int:
    getter = getattr(namespace, "_logistic_network_count", None)
    if getter is None:
        return 0
    try:
        return int(getter() or 0)
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Progression bands
# ---------------------------------------------------------------------------

BAND_NAMES = {
    0: "bootstrap",
    1: "early_automation",
    2: "scaling",
    3: "advanced_industry",
    4: "launch_capable",
    5: "endgame",
}

# Ordered ascending table tests over stable infrastructure signals.  A band
# threshold fires on technology presence OR physical infrastructure; inventory
# deliberately plays no role so consumption cannot demote a session.
_BAND_TESTS: tuple[tuple[int, tuple[str, ...], tuple[str, ...]], ...] = (
    (1, ("electricity",), ("assembling-machine-1", "small-electric-pole")),
    (
        2,
        ("oil-processing", "railway", "steel-processing", "concrete"),
        ("pumpjack", "oil-refinery", "locomotive", "steel-furnace"),
    ),
    (
        3,
        (
            "robotics",
            "chemical-science-pack",
            "production-science-pack",
            "advanced-material-processing-2",
        ),
        ("roboport", "chemical-plant", "centrifuge"),
    ),
    (4, ("rocket-silo", "space-science-pack"), ("rocket-silo",)),
    (
        5,
        ("space-science-pack", "prod-effectivity-module-3"),
        (),
    ),  # endgame requires sustained science production, tested separately
)


def classify_progression_band(snapshot: ContractContextSnapshot) -> int:
    """Highest progression band whose threshold the stable state satisfies."""

    techs = set(snapshot.technology_ids)
    entities = snapshot.placed_entity_counts
    band = 0
    for threshold_band, tech_names, entity_names in _BAND_TESTS:
        hit = any(name in techs for name in tech_names) or any(
            entities.get(name, 0) > 0 for name in entity_names
        )
        if threshold_band == 5:
            sustained = any(
                item.startswith("space-science-pack") and rate >= 1.0
                for item, rate in snapshot.production_rates_300s.items()
            )
            hit = hit and (sustained or "space-science-pack" in techs)
        if hit:
            band = max(band, threshold_band)
    return band


def ratchet_progression_band(previous: int, observed: int) -> int:
    """Sessions never move backward merely because inventory was consumed."""
    return max(previous, observed)


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------


def extract_difficulty_features(
    *,
    snapshot: ContractContextSnapshot,
    product_id: str,
    quantity: int,
    deadline_ticks: int,
    catalog: ProductCatalog,
    stage_band: int | None = None,
) -> ContractDifficultyFeatures:
    """Deterministic order features from frozen context plus pinned data."""

    facts = catalog.require(product_id)
    resolved_band = (
        stage_band if stage_band is not None else classify_progression_band(snapshot)
    )

    unlocked = set(snapshot.technology_ids)
    missing_techs = sorted(facts.enabling_technologies - unlocked)
    missing_machines = sorted(
        catalog.missing_machine_categories(product_id, snapshot.placed_entity_counts)
    )
    rates = snapshot.production_rates_300s
    required_new_intermediates = sum(
        1
        for item in facts.intermediates
        if rates.get(item, 0.0) <= EPSILON_RATE
        and snapshot.inventory_counts.get(item, 0) <= 0
    )

    deadline_minutes = deadline_ticks / TICKS_PER_MINUTE
    required_rate = quantity / deadline_minutes
    existing_rate = max(rates.get(product_id, 0.0), rates_60(snapshot, product_id))
    inventory_coverage = min(
        snapshot.inventory_counts.get(product_id, 0) / max(quantity, 1), 1.0
    )

    estimated_power_fraction = _estimate_power_fraction(
        facts, missing_machines, snapshot
    )
    transport = _transport_complexity(facts, required_rate, snapshot)

    tier = min(3, facts.depth // 2)

    return ContractDifficultyFeatures(
        schema_version=CONTRACT_FEATURES_VERSION,
        product_id=product_id,
        product_tier=tier,
        recipe_depth=facts.depth,
        missing_technology_count=len(missing_techs),
        missing_machine_type_count=len(missing_machines),
        required_new_intermediate_count=required_new_intermediates,
        log_quantity=math.log(max(quantity, 1)),
        deadline_ticks=deadline_ticks,
        required_rate_per_minute=round(required_rate, 4),
        existing_rate_per_minute=round(existing_rate, 4),
        inventory_coverage_ratio=round(inventory_coverage, 4),
        estimated_power_fraction=round(min(estimated_power_fraction, 10.0), 4),
        transport_complexity=round(transport, 4),
        stage_band=resolved_band,
    )


def rates_60(snapshot: ContractContextSnapshot, item: str) -> float:
    return snapshot.production_rates_60s.get(item, 0.0)


def missing_detail(
    snapshot: ContractContextSnapshot, catalog: ProductCatalog, product_id: str
) -> dict[str, list[str]]:
    """Human-auditable missing-prerequisite breakdown for rejection records."""
    facts = catalog.require(product_id)
    unlocked = set(snapshot.technology_ids)
    return {
        "missing_technologies": sorted(facts.enabling_technologies - unlocked),
        "missing_machines": sorted(
            category
            for category in facts.machine_categories
            if not any(
                snapshot.placed_entity_counts.get(machine, 0) > 0
                for machine in _CATEGORY_MACHINES.get(category, ())
            )
        ),
    }


def _estimate_power_fraction(
    facts: ProductFacts,
    missing_machines: list[str],
    snapshot: ContractContextSnapshot,
) -> float:
    if not missing_machines:
        return 0.0
    demand_kw = sum(_CATEGORY_POWER_KW.get(cat, 150.0) for cat in missing_machines)
    capacity_kw = snapshot.power_capacity_kw
    if capacity_kw <= 0:
        return 10.0  # no measurable grid: maximal pressure signal
    spare = max(capacity_kw * (1.0 - snapshot.power_utilization), 1.0)
    return demand_kw / spare


def _transport_complexity(
    facts: ProductFacts,
    required_rate: float,
    snapshot: ContractContextSnapshot,
) -> float:
    complexity = 0.0
    if facts.fluid_ingredients:
        complexity += 0.25
    if len(facts.intermediates) >= 4:
        complexity += 0.25
    if required_rate >= _TRANSPORT_HEAVY_THRESHOLD:
        complexity += 0.25
        has_trains = snapshot.train_stop_count > 0
        has_logistics = snapshot.logistic_network_count > 0
        if not (has_trains or has_logistics):
            complexity += 0.25
    return min(complexity, 1.0)


__all__ = [
    "CONTRACT_FEATURES_VERSION",
    "BAND_NAMES",
    "GameDataError",
    "ProductCatalog",
    "ProductFacts",
    "RecipeDataSource",
    "RecipeFacts",
    "StaticRecipeDataSource",
    "NamespaceRecipeDataSource",
    "TechnologyFacts",
    "TICKS_PER_MINUTE",
    "capture_context_snapshot",
    "classify_progression_band",
    "compute_state_digest",
    "extract_difficulty_features",
    "missing_detail",
    "ratchet_progression_band",
    "watermark_is_monotonic",
]
