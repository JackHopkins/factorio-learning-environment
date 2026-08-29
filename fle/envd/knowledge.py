"""Callable, versioned knowledge surfaces for Factorio evaluation.

The evaluator owns the source files and exposes only bounded, structured
answers through MCP.  A model never receives a host path or an open file
handle.  The API corpus is generated from the checked-in ``agent.md`` files
and the exact game-data source is the recipe/technology export passed to the
run.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

API_REFERENCE_VERSION = "fle-api-reference-v1"
GAME_DATA_REFERENCE_VERSION = "factorio-game-data-reference-v1"
REFERENCE_SCHEMA_VERSION = "knowledge-reference-v1"
DEFAULT_GAME_DATA_FILE = (
    Path(__file__).resolve().parents[2]
    / "benchmark"
    / "data"
    / "factorio-2.0.73-contract-game-data.json"
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9][a-z0-9_-]*", value.lower()) if token}


def _query_matches(query_tokens: set[str], searchable_tokens: set[str]) -> bool:
    """Match whole words and useful fragments of hyphenated identifiers."""
    return not query_tokens or all(
        any(query_token in searchable_token for searchable_token in searchable_tokens)
        for query_token in query_tokens
    )


def _cursor_value(cursor: str | int | None) -> int:
    if cursor in (None, ""):
        return 0
    try:
        return max(int(cursor), 0)
    except (TypeError, ValueError):
        raise ValueError("cursor must be a non-negative integer") from None


def _paginate(values: list[Any], limit: int, cursor: str | int | None) -> tuple[list[Any], str | None]:
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    start = _cursor_value(cursor)
    page = values[start : start + limit]
    next_cursor = str(start + limit) if start + limit < len(values) else None
    return page, next_cursor


@dataclass(frozen=True)
class ReferenceDocument:
    document_id: str
    title: str
    kind: str
    content: str
    source: str
    version: str

    @property
    def content_sha256(self) -> str:
        return _sha256_text(self.content)

    def summary(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "kind": self.kind,
            "source": self.source,
            "version": self.version,
            "content_sha256": self.content_sha256,
            "content_chars": len(self.content),
        }


class ApiReference:
    """Deterministic corpus containing every FLE manual under ``tools``."""

    def __init__(self, root: Path | None = None):
        self.root = root or Path(__file__).resolve().parents[1] / "env"
        self._documents: dict[str, ReferenceDocument] | None = None

    @property
    def documents(self) -> dict[str, ReferenceDocument]:
        if self._documents is None:
            documents: dict[str, ReferenceDocument] = {}
            tools_root = self.root / "tools"
            for path in sorted(tools_root.rglob("agent.md")):
                relative = path.relative_to(tools_root).as_posix()
                # Keep the root manual stable and expose nested tool manuals by
                # their complete path so admin and agent surfaces cannot collide.
                stem = relative[:-len("/agent.md")] if relative.endswith("/agent.md") else relative[:-len(".md")]
                document_id = "api/overview" if stem == "agent" else f"api/{stem}"
                content = path.read_text(encoding="utf-8")
                documents[document_id] = ReferenceDocument(
                    document_id=document_id,
                    title=stem.replace("/", " ").replace("_", " "),
                    kind="api",
                    content=content,
                    source=path.as_posix(),
                    version=API_REFERENCE_VERSION,
                )

            # The compact action contract is also callable through the same
            # reference surface.  It is the one document shared by all
            # harnesses, so keeping it in the corpus makes the manifest hash
            # cover the exact programmatic boundary exposed to the model.
            try:
                from fle.envd.action_reference import ACTION_PROFILE_REFERENCE

                documents["api/action-profile"] = ReferenceDocument(
                    document_id="api/action-profile",
                    title="action profile",
                    kind="api",
                    content=ACTION_PROFILE_REFERENCE,
                    source="fle.envd.action_reference:ACTION_PROFILE_REFERENCE",
                    version=API_REFERENCE_VERSION,
                )
            except Exception:
                # The source manuals remain queryable if the compact profile
                # cannot be imported in a reduced tooling environment.
                pass

            # Generated schemas provide the type and object contracts that are
            # not repeated in individual manuals.  Import lazily so MCP startup
            # stays cheap when a caller only uses game-data queries.
            try:
                from fle.env.utils.controller_loader.system_prompt_generator import (
                    SystemPromptGenerator,
                )

                generator = SystemPromptGenerator(str(self.root))
                generated = {
                    "api/types": generator.types(),
                    "api/entities": generator.entities(),
                    "api/method-schema": generator.schema(),
                }
                for document_id, content in generated.items():
                    documents[document_id] = ReferenceDocument(
                        document_id=document_id,
                        title=document_id.removeprefix("api/").replace("-", " "),
                        kind="api",
                        content=str(content),
                        source="generated-from-fle-source",
                        version=API_REFERENCE_VERSION,
                    )
            except Exception:
                # Individual manuals remain available if an optional generator
                # dependency or a source file is temporarily unavailable.
                pass
            self._documents = documents
        return self._documents

    @property
    def reference_hash(self) -> str:
        return _sha256_text(
            _canonical(
                [
                    (document.document_id, document.content_sha256)
                    for document in self.documents.values()
                ]
            )
        )

    def search(
        self,
        query: str = "",
        *,
        kinds: Iterable[str] | None = None,
        limit: int = 20,
        cursor: str | int | None = None,
    ) -> dict[str, Any]:
        requested_kinds = {str(kind).lower() for kind in (kinds or ())}
        query_tokens = _tokens(query)
        matches = []
        for document in self.documents.values():
            if requested_kinds and document.kind not in requested_kinds:
                continue
            searchable = _tokens(
                " ".join((document.document_id, document.title, document.content))
            )
            if not _query_matches(query_tokens, searchable):
                continue
            matches.append(document.summary())
        page, next_cursor = _paginate(matches, limit, cursor)
        return {
            "schema_version": REFERENCE_SCHEMA_VERSION,
            "reference_id": API_REFERENCE_VERSION,
            "reference_sha256": self.reference_hash,
            "query": query,
            "results": page,
            "next_cursor": next_cursor,
        }

    def read(
        self,
        document_id: str,
        *,
        section: str | None = None,
        cursor: str | int | None = None,
        max_chars: int = 12000,
    ) -> dict[str, Any]:
        normalized = document_id.replace(":", "/")
        if not normalized.startswith("api/"):
            normalized = f"api/{normalized}"
        document = self.documents.get(normalized)
        if document is None:
            raise KeyError(f"unknown API reference document: {document_id}")
        content = document.content
        if section:
            content = _select_markdown_section(content, section)
        if max_chars < 1 or max_chars > 60000:
            raise ValueError("max_chars must be between 1 and 60000")
        start = _cursor_value(cursor)
        chunk = content[start : start + max_chars]
        next_cursor = str(start + max_chars) if start + max_chars < len(content) else None
        return {
            "schema_version": REFERENCE_SCHEMA_VERSION,
            "reference_id": API_REFERENCE_VERSION,
            "reference_sha256": self.reference_hash,
            "document": document.summary(),
            "section": section,
            "content": chunk,
            "next_cursor": next_cursor,
        }


def _select_markdown_section(content: str, section: str) -> str:
    """Return a heading section without making section lookup mandatory."""
    wanted = section.strip().lower()
    lines = content.splitlines(keepends=True)
    start = None
    level = 0
    for index, line in enumerate(lines):
        match = re.match(r"^(#+)\s+(.*)\s*$", line)
        if match and match.group(2).strip().lower() == wanted:
            start = index
            level = len(match.group(1))
            break
    if start is None:
        raise KeyError(f"section not found: {section}")
    end = len(lines)
    for index in range(start + 1, len(lines)):
        match = re.match(r"^(#+)\s+", lines[index])
        if match and len(match.group(1)) <= level:
            end = index
            break
    return "".join(lines[start:end])


class GameDataReference:
    """Query an exact recipe/technology export without exposing its path."""

    def __init__(self, payload: dict[str, Any], *, source: str = "run-export"):
        if not isinstance(payload, dict):
            raise ValueError("game-data export must be a JSON object")
        recipes = payload.get("recipes")
        technologies = payload.get("technologies", [])
        if not isinstance(recipes, list) or not recipes:
            raise ValueError("game-data export must contain a non-empty recipes list")
        if not isinstance(technologies, list):
            raise ValueError("game-data technologies must be a list")
        self.factorio_version = str(payload.get("factorio_version", "unknown"))
        self.source = source
        self.payload = payload
        self.recipes = {
            str(recipe["name"]): recipe
            for recipe in recipes
            if isinstance(recipe, dict) and str(recipe.get("name", "")).strip()
        }
        self.technologies = {
            str(technology["name"]): technology
            for technology in technologies
            if isinstance(technology, dict) and str(technology.get("name", "")).strip()
        }
        self.recipe_to_technologies: dict[str, list[str]] = {}
        for name, technology in self.technologies.items():
            for recipe_id in technology.get("unlocked_recipes", []) or []:
                self.recipe_to_technologies.setdefault(str(recipe_id), []).append(name)
        self._hash = _sha256_text(_canonical(payload))

    @property
    def reference_id(self) -> str:
        return f"{GAME_DATA_REFERENCE_VERSION}/{self.factorio_version}"

    @property
    def reference_hash(self) -> str:
        return self._hash

    @staticmethod
    def _canonical_recipe_id(identifier: str) -> str:
        """Normalize the public enum aliases to Factorio recipe IDs."""

        value = identifier.strip()
        if value.startswith("RecipeName."):
            value = value.removeprefix("RecipeName.")
            # The enum is CamelCase; the explicit aliases below cover the
            # names most likely to be supplied by a model.
            value = re.sub(r"(?<!^)([A-Z])", r"-\1", value).lower()
        aliases = {
            "fill-lubricant-barrel": "lubricant-barrel",
            "fill-crude-oil-barrel": "crude-oil-barrel",
            "fill-heavy-oil-barrel": "heavy-oil-barrel",
            "fill-light-oil-barrel": "light-oil-barrel",
            "fill-petroleum-gas-barrel": "petroleum-gas-barrel",
            "fill-sulfuric-acid-barrel": "sulfuric-acid-barrel",
            "fill-water-barrel": "water-barrel",
        }
        return aliases.get(value, value)

    @staticmethod
    def _canonical_prototype_id(identifier: str) -> str:
        value = identifier.strip()
        if value.startswith("Prototype."):
            value = value.removeprefix("Prototype.")
            value = re.sub(r"(?<!^)([A-Z])", r"-\1", value).lower()
        return value

    @classmethod
    def _recipe_aliases(cls, identifier: str) -> tuple[str, ...]:
        """Return public spellings for one exact Factorio recipe ID."""

        canonical = cls._canonical_recipe_id(identifier)
        aliases: set[str] = set()
        if canonical.endswith("-barrel"):
            aliases.add(f"fill-{canonical}")
        if canonical == "lubricant-barrel":
            # This was the spelling used by an earlier agent-facing guide.
            aliases.add("fill-lubricant-barrel")
        return tuple(sorted(aliases))

    def _envelope(self, kind: str, identifier: str, data: Any) -> dict[str, Any]:
        return {
            "schema_version": REFERENCE_SCHEMA_VERSION,
            "reference_id": self.reference_id,
            "reference_sha256": self.reference_hash,
            "factorio_version": self.factorio_version,
            "kind": kind,
            "canonical_id": identifier,
            "source": self.source,
            "data": data,
        }

    def recipe(self, item_or_recipe_id: str) -> dict[str, Any]:
        requested = str(item_or_recipe_id).strip()
        identifier = self._canonical_recipe_id(requested)
        recipe = self.recipes.get(identifier)
        if recipe is None:
            candidates = [
                value
                for value in self.recipes.values()
                if any(str(product.get("name")) == identifier for product in value.get("products", []) or [])
            ]
            if len(candidates) == 1:
                recipe = candidates[0]
            elif len(candidates) > 1:
                choices = sorted(str(value.get("name")) for value in candidates)
                raise KeyError(
                    f"item {requested!r} is ambiguous; multiple recipes produce it: "
                    f"{choices}. "
                    "use factorio_search_reference or factorio_get_recipe with "
                    "one canonical recipe id"
                )
        if recipe is None:
            raise KeyError(f"unknown recipe or item id: {requested}")
        canonical = str(recipe.get("name", identifier))
        data = dict(recipe)
        data["canonical_id"] = canonical
        data["unlocked_by"] = sorted(self.recipe_to_technologies.get(canonical, ()))
        data["requested_id"] = requested
        aliases = self._recipe_aliases(canonical)
        if aliases:
            data["aliases"] = list(aliases)
        return self._envelope("recipe", canonical, data)

    def technology(self, technology_id: str) -> dict[str, Any]:
        identifier = str(technology_id).strip()
        technology = self.technologies.get(identifier)
        if technology is None:
            raise KeyError(f"unknown technology id: {identifier}")
        data = dict(technology)
        data["canonical_id"] = identifier
        return self._envelope("technology", identifier, data)

    def unlock_path(self, item_or_recipe_id: str) -> dict[str, Any]:
        recipe = self.recipe(item_or_recipe_id)
        recipe_data = recipe["data"]
        recipe_id = str(recipe_data["canonical_id"])
        technologies = sorted(self.recipe_to_technologies.get(recipe_id, ()))
        closure: set[str] = set()
        stack = list(technologies)
        while stack:
            technology_id = stack.pop()
            if technology_id in closure:
                continue
            closure.add(technology_id)
            stack.extend(str(item) for item in self.technologies.get(technology_id, {}).get("prerequisites", []) or [])
        path = {
            "recipe_id": recipe_id,
            "product_ids": sorted(
                str(product.get("name"))
                for product in recipe_data.get("products", []) or []
                if isinstance(product, dict) and product.get("name")
            ),
            "ingredient_ids": sorted(
                str(ingredient.get("name"))
                for ingredient in recipe_data.get("ingredients", []) or []
                if isinstance(ingredient, dict) and ingredient.get("name")
            ),
            "direct_unlock_technologies": technologies,
            "technology_closure": sorted(closure),
            "prerequisites": {
                technology_id: sorted(
                    str(item)
                    for item in self.technologies.get(technology_id, {}).get("prerequisites", []) or []
                )
                for technology_id in sorted(closure)
            },
        }
        return self._envelope("unlock_path", recipe_id, path)

    def machine_requirements(self, recipe_id: str) -> dict[str, Any]:
        recipe = self.recipe(recipe_id)
        data = recipe["data"]
        category = str(data.get("category", "crafting"))
        explicit = self.payload.get("machines", {})
        if isinstance(explicit, dict):
            machines = explicit.get(category) or explicit.get(str(data.get("name")))
        else:
            machines = None
        if machines is None:
            prototypes = self.payload.get("prototypes", {})
            prototype_values = (
                prototypes.values()
                if isinstance(prototypes, dict)
                else prototypes
                if isinstance(prototypes, list)
                else ()
            )
            machines = [
                str(prototype.get("name"))
                for prototype in prototype_values
                if isinstance(prototype, dict)
                and category in (prototype.get("crafting_categories") or ())
                and prototype.get("name")
            ]
            if not machines:
                machines = None
        if machines is None:
            machines = _MACHINE_CATEGORY_DEFAULTS.get(category, [])
        result = {
            "recipe_id": data["canonical_id"],
            "category": category,
            "required_machine_categories": [category],
            "machine_prototypes": list(machines),
            "machine_facts_source": (
                "export.machines"
                if explicit
                else "export.prototypes"
                if machines and self.payload.get("prototypes")
                else "versioned-fallback-catalog"
            ),
        }
        return self._envelope("machine_requirements", str(data["canonical_id"]), result)

    def prototype(self, prototype_id: str) -> dict[str, Any]:
        identifier = self._canonical_prototype_id(str(prototype_id))
        prototypes = self.payload.get("prototypes", {})
        value = prototypes.get(identifier) if isinstance(prototypes, dict) else None
        if value is None and isinstance(prototypes, list):
            value = next(
                (item for item in prototypes if isinstance(item, dict) and item.get("name") == identifier),
                None,
            )
        if value is None:
            # The recipe export is authoritative for recipes and technologies;
            # prototype queries stay explicit about the missing export rather
            # than presenting a guessed prototype as game fact.
            raise KeyError(
                f"prototype {identifier!r} is absent from this exact export; "
                "rerun export_contract_game_data with prototype metadata "
                "(the contract export must include Prototype.Lab)"
            )
        return self._envelope("prototype", identifier, value)

    def search(
        self,
        query: str = "",
        *,
        kinds: Iterable[str] | None = None,
        limit: int = 20,
        cursor: str | int | None = None,
    ) -> dict[str, Any]:
        requested = {str(kind).lower() for kind in (kinds or ())}
        q = _tokens(query)
        records: list[dict[str, Any]] = []
        datasets: list[tuple[str, Iterable[tuple[str, Any]]]] = [
            ("recipe", self.recipes.items()),
            ("technology", self.technologies.items()),
        ]
        prototypes = self.payload.get("prototypes", {})
        if isinstance(prototypes, dict):
            datasets.append(("prototype", prototypes.items()))
        elif isinstance(prototypes, list):
            datasets.append(
                ("prototype", ((str(item.get("name")), item) for item in prototypes if isinstance(item, dict) and item.get("name")))
            )
        for kind, values in datasets:
            if requested and kind not in requested:
                continue
            for identifier, value in values:
                text = _canonical(value)
                aliases = self._recipe_aliases(str(identifier)) if kind == "recipe" else ()
                if not _query_matches(q, _tokens(f"{identifier} {' '.join(aliases)} {text}")):
                    continue
                records.append({"kind": kind, "canonical_id": identifier, "title": identifier})
        records.sort(key=lambda item: (item["kind"], item["canonical_id"]))
        page, next_cursor = _paginate(records, limit, cursor)
        return {
            "schema_version": REFERENCE_SCHEMA_VERSION,
            "reference_id": self.reference_id,
            "reference_sha256": self.reference_hash,
            "factorio_version": self.factorio_version,
            "query": query,
            "results": page,
            "next_cursor": next_cursor,
        }


_MACHINE_CATEGORY_DEFAULTS: dict[str, list[str]] = {
    "crafting": ["assembling-machine-1", "assembling-machine-2", "assembling-machine-3"],
    "advanced-crafting": ["assembling-machine-2", "assembling-machine-3"],
    "smelting": ["stone-furnace", "steel-furnace", "electric-furnace"],
    "chemistry": ["chemical-plant"],
    "oil-processing": ["oil-refinery"],
    "centrifuging": ["centrifuge"],
    "electronics": ["assembling-machine-2", "assembling-machine-3"],
    "rocket-building": ["rocket-silo"],
    "metallurgy": ["foundry"],
}


def load_game_data(path: str | Path | None = None) -> tuple[GameDataReference, str]:
    """Load a run export and return the reference plus a source identifier."""
    source_path = Path(path) if path else DEFAULT_GAME_DATA_FILE
    if not source_path.exists():
        raise FileNotFoundError(f"game-data export does not exist: {source_path}")
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        # Older exports were recipe-only JSON lists.  Preserve support while
        # giving every caller the same structured, hashable envelope.
        payload = {
            "factorio_version": "unknown",
            "recipes": payload,
            "technologies": [],
        }
    return GameDataReference(payload, source="run-export"), str(source_path)


__all__ = [
    "API_REFERENCE_VERSION",
    "DEFAULT_GAME_DATA_FILE",
    "GAME_DATA_REFERENCE_VERSION",
    "ApiReference",
    "GameDataReference",
    "ReferenceDocument",
    "load_game_data",
]
