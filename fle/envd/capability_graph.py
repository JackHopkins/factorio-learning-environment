"""Advisory capability evidence and minimal customer follow-up policy.

This module intentionally has no control authority.  It turns two passive
factory snapshots into evidence and a directional hint; the customer may
still choose a remote stretch product.  Contract delivery remains the only
rating outcome.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from fle.envd.contract_features import EPSILON_RATE, ProductCatalog
from fle.envd.models import (
    CapabilityDelta,
    CapabilityGraphSnapshot,
    CapabilityNodeEvidence,
    CapabilityNodeStatus,
    ContractContextSnapshot,
)


def _recipe_records(catalog: ProductCatalog) -> dict[str, Any]:
    raw = getattr(catalog._source, "_raw_recipes", None)
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _technology_records(catalog: ProductCatalog) -> dict[str, Any]:
    raw = getattr(catalog._source, "_raw_technologies", None)
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items()}
    return {}


def _recipe_chain(product_id: str, catalog: ProductCatalog) -> set[str]:
    records = _recipe_records(catalog)
    found: set[str] = set()
    pending = [product_id]
    while pending:
        current = pending.pop()
        if current in found:
            continue
        found.add(current)
        recipe = records.get(current)
        if not isinstance(recipe, dict):
            facts = catalog.facts(current)
            if facts is None:
                continue
            pending.extend(name for name, _ in facts.recipe.ingredients)
            continue
        pending.extend(
            str(item.get("name"))
            for item in recipe.get("ingredients", ()) or ()
            if isinstance(item, dict) and item.get("name")
        )
    return found


def _product_prerequisites(product_id: str, catalog: ProductCatalog) -> tuple[str, ...]:
    facts = catalog.facts(product_id)
    if facts is None:
        return ()
    return tuple(
        sorted(
            {
                f"product:{name}"
                for name, _ in facts.recipe.ingredients
                if catalog.facts(name) is not None
            }
            | {f"technology:{name}" for name in facts.enabling_technologies}
        )
    )


def _status_for_product(
    product_id: str,
    snapshot: ContractContextSnapshot,
    catalog: ProductCatalog,
    delivered_products: set[str],
) -> CapabilityNodeStatus:
    if product_id in delivered_products:
        return "delivered"
    if snapshot.production_rates_300s.get(product_id, 0.0) > EPSILON_RATE or snapshot.production_rates_60s.get(product_id, 0.0) > EPSILON_RATE:
        return "producing"
    if product_id in snapshot.unlocked_recipe_ids:
        return "unlocked"
    facts = catalog.facts(product_id)
    if facts is None:
        return "locked"
    if facts.recipe.enabled is False and not facts.enabling_technologies:
        return "locked"
    if set(facts.enabling_technologies).issubset(snapshot.technology_ids):
        return "reachable"
    return "locked"


def build_capability_graph(
    snapshot: ContractContextSnapshot,
    catalog: ProductCatalog,
    *,
    target_product: str | None = None,
    delivered_products: Iterable[str] = (),
) -> CapabilityGraphSnapshot:
    """Build a deterministic advisory graph from a passive snapshot."""
    products = set(_recipe_records(catalog))
    products.update(snapshot.production_rates_60s)
    products.update(snapshot.production_rates_300s)
    products.update(snapshot.unlocked_recipe_ids)
    if target_product:
        products.update(_recipe_chain(target_product, catalog))
    delivered = set(delivered_products)
    nodes: list[CapabilityNodeEvidence] = []
    techs = set(snapshot.technology_ids) | set(_technology_records(catalog))
    for technology_id in sorted(techs):
        record = _technology_records(catalog).get(technology_id, {})
        prerequisites = tuple(f"technology:{item}" for item in record.get("prerequisites", ()) or ()) if isinstance(record, dict) else ()
        status: CapabilityNodeStatus = "unlocked" if technology_id in snapshot.technology_ids else "locked"
        if status == "locked" and all(
            item.removeprefix("technology:") in snapshot.technology_ids for item in prerequisites
        ):
            status = "reachable"
        nodes.append(
            CapabilityNodeEvidence(
                node_id=f"technology:{technology_id}",
                kind="technology",
                status=status,
                prerequisites=prerequisites,
                first_evidence_tick=snapshot.captured_tick if status == "unlocked" else None,
                latest_evidence_tick=snapshot.captured_tick if status == "unlocked" else None,
                evidence={"canonical_id": technology_id},
            )
        )
    for product_id in sorted(products):
        status = _status_for_product(product_id, snapshot, catalog, delivered)
        rate = max(
            snapshot.production_rates_300s.get(product_id, 0.0),
            snapshot.production_rates_60s.get(product_id, 0.0),
        )
        nodes.append(
            CapabilityNodeEvidence(
                node_id=f"product:{product_id}",
                kind="product",
                status=status,
                prerequisites=_product_prerequisites(product_id, catalog),
                first_evidence_tick=snapshot.captured_tick if status in {"producing", "delivered"} else None,
                latest_evidence_tick=snapshot.captured_tick if status in {"producing", "delivered"} else None,
                production_rate_per_minute=round(rate, 4),
                evidence={"canonical_id": product_id},
            )
        )
    for machine_id, count in sorted(snapshot.placed_entity_counts.items()):
        if count <= 0:
            continue
        nodes.append(
            CapabilityNodeEvidence(
                node_id=f"machine:{machine_id}",
                kind="machine",
                status="constructed",
                first_evidence_tick=snapshot.captured_tick,
                latest_evidence_tick=snapshot.captured_tick,
                evidence={"canonical_id": machine_id, "count": int(count)},
            )
        )

    node_by_id = {node.node_id: node for node in nodes}
    advisory_frontier = tuple(
        sorted(
            node.node_id
            for node in nodes
            if node.kind == "product"
            and node.status in {"reachable", "unlocked"}
            and all(
                node_by_id.get(prerequisite) is None
                or node_by_id[prerequisite].status
                in {"reachable", "unlocked", "constructed", "producing", "delivered"}
                for prerequisite in node.prerequisites
                if prerequisite.startswith("technology:")
            )
        )
    )
    target_path = tuple(
        _dependency_path(target_product, catalog) if target_product else ()
    )
    return CapabilityGraphSnapshot(
        factorio_version=catalog.game_version,
        state_digest=snapshot.state_digest,
        captured_tick=snapshot.captured_tick,
        nodes=nodes,
        advisory_frontier=advisory_frontier,
        target_path=target_path,
    )


def _dependency_path(product_id: str, catalog: ProductCatalog) -> list[str]:
    """Stable depth-first path used only for explanatory evidence."""
    if not product_id:
        return []
    facts = catalog.facts(product_id)
    if facts is None:
        return [f"product:{product_id}"]
    path: list[str] = []
    seen: set[str] = set()
    required_technologies: set[str] = set()

    def visit(item: str) -> None:
        if item in seen:
            return
        seen.add(item)
        item_facts = catalog.facts(item)
        if item_facts is not None:
            for ingredient, _ in sorted(item_facts.recipe.ingredients):
                visit(ingredient)
            required_technologies.update(item_facts.enabling_technologies)
        path.append(f"product:{item}")

    visit(product_id)
    technologies = _technology_records(catalog)
    seen_technologies: set[str] = set()

    def visit_technology(technology: str) -> None:
        if technology in seen_technologies:
            return
        seen_technologies.add(technology)
        record = technologies.get(technology, {})
        if isinstance(record, dict):
            for prerequisite in sorted(record.get("prerequisites", ()) or ()):
                visit_technology(str(prerequisite))
        path.append(f"technology:{technology}")

    for technology in sorted(required_technologies):
        visit_technology(technology)
    return path


def compare_capability_snapshots(
    before: ContractContextSnapshot,
    after: ContractContextSnapshot,
    *,
    target_product: str,
    catalog: ProductCatalog,
) -> CapabilityDelta:
    """Compute evidence movement without awarding rating credit."""
    before_tech = set(before.technology_ids)
    after_tech = set(after.technology_ids)
    before_recipes = set(before.unlocked_recipe_ids)
    after_recipes = set(after.unlocked_recipe_ids)
    before_machines = {name for name, count in before.placed_entity_counts.items() if count > 0}
    after_machines = {name for name, count in after.placed_entity_counts.items() if count > 0}
    produced_before = {
        item for item, rate in {**before.production_rates_300s, **before.production_rates_60s}.items() if rate > EPSILON_RATE
    }
    produced_after = {
        item for item, rate in {**after.production_rates_300s, **after.production_rates_60s}.items() if rate > EPSILON_RATE
    }
    rate_deltas = {
        item: round(
            max(after.production_rates_300s.get(item, 0.0), after.production_rates_60s.get(item, 0.0))
            - max(before.production_rates_300s.get(item, 0.0), before.production_rates_60s.get(item, 0.0)),
            4,
        )
        for item in set(before.production_rates_300s) | set(after.production_rates_300s) | set(before.production_rates_60s) | set(after.production_rates_60s)
        if max(after.production_rates_300s.get(item, 0.0), after.production_rates_60s.get(item, 0.0))
        - max(before.production_rates_300s.get(item, 0.0), before.production_rates_60s.get(item, 0.0)) > EPSILON_RATE
    }
    path = _dependency_path(target_product, catalog)
    before_graph = build_capability_graph(before, catalog, target_product=target_product)
    after_graph = build_capability_graph(after, catalog, target_product=target_product)
    before_status = {node.node_id: node.status for node in before_graph.nodes}
    after_status = {node.node_id: node.status for node in after_graph.nodes}
    path_before = tuple(node for node in path if before_status.get(node) in {"unlocked", "constructed", "producing", "delivered"})
    path_after = tuple(node for node in path if after_status.get(node) in {"unlocked", "constructed", "producing", "delivered"})
    newly_producing = tuple(sorted(produced_after - produced_before))
    path_products = {
        node.removeprefix("product:")
        for node in path
        if node.startswith("product:")
    }
    path_technologies = {
        node.removeprefix("technology:")
        for node in path
        if node.startswith("technology:")
    }
    relevant_rate_deltas = {
        item: rate for item, rate in rate_deltas.items() if item in path_products
    }
    # Rate snapshots are intentionally diagnostic only.  A higher 60s/300s
    # value can be a transient buffer drain or a measurement-window change;
    # it must never by itself qualify as capability progress.  Count only
    # structural target-path nodes becoming unlocked/constructed, or explicit
    # target-path technology/recipe unlocks.
    structural_statuses = {"unlocked", "constructed"}
    path_before_structural = {
        node for node in path if before_status.get(node) in structural_statuses
    }
    path_after_structural = {
        node for node in path if after_status.get(node) in structural_statuses
    }
    structural_path_delta = path_after_structural - path_before_structural
    path_technology_delta = (after_tech - before_tech) & path_technologies
    path_recipe_delta = (after_recipes - before_recipes) & path_products
    meaningful = bool(
        structural_path_delta or path_technology_delta or path_recipe_delta
    )
    return CapabilityDelta(
        before_state_digest=before.state_digest,
        after_state_digest=after.state_digest,
        target_id=target_product,
        new_technologies=tuple(sorted(after_tech - before_tech)),
        new_recipes=tuple(sorted(after_recipes - before_recipes)),
        new_machines=tuple(sorted(after_machines - before_machines)),
        newly_producing=newly_producing,
        production_rate_deltas=rate_deltas,
        path_nodes_before=path_before,
        path_nodes_after=path_after,
        path_progress=len(structural_path_delta),
        meaningful_progress=meaningful,
        evidence={
            "target_path": list(path),
            "relevant_rate_deltas": relevant_rate_deltas,
            "structural_path_delta": sorted(structural_path_delta),
            "path_technology_delta": sorted(path_technology_delta),
            "path_recipe_delta": sorted(path_recipe_delta),
            "before_captured_tick": before.captured_tick,
            "after_captured_tick": after.captured_tick,
        },
    )


__all__ = [
    "build_capability_graph",
    "compare_capability_snapshots",
]
