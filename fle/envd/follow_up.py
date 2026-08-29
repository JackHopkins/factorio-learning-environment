"""Outcome-aware customer continuation for adaptive contract sessions.

The policy intentionally has only a few branches.  It uses the capability
graph as evidence about direction while the generated candidate's quantity
and deadline remain the adaptive ladder's pressure controls.
"""

from __future__ import annotations

import math
import random
from typing import Iterable

from fle.envd.contract_features import ProductCatalog
from fle.envd.contract_generator import ContractCandidate
from fle.envd.models import (
    CapabilityDelta,
    ContractEpochOutcome,
    ContractEpochSpec,
    CustomerFollowUp,
)


def _accepted(pool: Iterable[ContractCandidate]) -> list[ContractCandidate]:
    return [candidate for candidate in pool if candidate.accepted and candidate.features is not None]


def _same_product(candidates: Iterable[ContractCandidate], product: str) -> list[ContractCandidate]:
    return [candidate for candidate in candidates if candidate.item_name == product]


def _prerequisite_products(product: str, catalog: ProductCatalog) -> set[str]:
    facts = catalog.facts(product)
    if facts is None:
        return set()
    return {
        ingredient
        for ingredient, _ in facts.recipe.ingredients
        if catalog.facts(ingredient) is not None
    }


def _path_products(product: str, catalog: ProductCatalog) -> set[str]:
    result: set[str] = set()
    pending = [product]
    while pending:
        current = pending.pop()
        if current in result:
            continue
        result.add(current)
        pending.extend(_prerequisite_products(current, catalog))
    return result


def _closest(candidates: Iterable[ContractCandidate], target_quantity: float) -> ContractCandidate | None:
    values = list(candidates)
    if not values:
        return None
    return min(
        values,
        key=lambda candidate: (
            abs(math.log(max(candidate.quantity, 1) / max(target_quantity, 1.0))),
            candidate.deadline_ticks,
            candidate.item_name,
        ),
    )


def choose_follow_up_candidate(
    pool: list[ContractCandidate],
    *,
    previous_spec: ContractEpochSpec | None,
    previous_outcome: ContractEpochOutcome | None,
    capability_delta: CapabilityDelta | None,
    catalog: ProductCatalog,
    selection_seed: int,
    stretch_probability: float = 0.10,
) -> tuple[ContractCandidate | None, CustomerFollowUp | None]:
    """Choose continuity candidate and an auditable reason.

    ``None`` means the ordinary selector should be used.  Every branch only
    changes selection; it never changes the already committed outcome or its
    TrueSkill mapping.
    """
    candidates = _accepted(pool)
    if not candidates or previous_spec is None or previous_outcome is None:
        return None, None
    previous_product = previous_spec.item_name
    status = previous_outcome.status
    previous_quantity = previous_spec.quantity
    rng = random.Random(selection_seed)
    is_frontier = previous_spec.mixture_class == "frontier" or "frontier" in previous_spec.template_id

    if status == "fulfilled":
        pressure = [
            candidate
            for candidate in _same_product(candidates, previous_product)
            if candidate.quantity > previous_quantity or candidate.deadline_ticks < previous_spec.deadline_ticks
        ]
        selected = max(
            pressure,
            key=lambda candidate: (candidate.quantity, -candidate.deadline_ticks),
            default=None,
        )
        reason = "fulfilled_pressure"
        if selected is None:
            frontier = [candidate for candidate in candidates if candidate.mixture_class == "frontier"]
            frontier = frontier or candidates
            nearest_distance = min(
                (
                    candidate.features.missing_technology_count,
                    candidate.features.missing_machine_type_count,
                )
                for candidate in frontier
                if candidate.features is not None
            )
            coherent_frontier = [
                candidate
                for candidate in frontier
                if candidate.features is not None
                and candidate.features.missing_technology_count
                <= nearest_distance[0] + 2
                and candidate.features.missing_machine_type_count
                <= nearest_distance[1] + 1
            ]
            selected = max(
                coherent_frontier or frontier,
                key=lambda candidate: candidate.effective_difficulty or 0.0,
            )
            reason = "fulfilled_frontier"
        stretch = bool(selected.features and selected.features.recipe_depth > previous_spec.features.recipe_depth + 1)
        if stretch and rng.random() >= max(min(stretch_probability, 1.0), 0.0):
            # Keep deterministic pressure when a remote stretch draw is not
            # selected; this is still a harder order on the same direction.
            same = _same_product(candidates, previous_product)
            selected = max(same or candidates, key=lambda candidate: candidate.quantity)
            stretch = False
        return selected, CustomerFollowUp(
            reason=reason,
            parent_epoch_index=previous_spec.epoch_index,
            parent_product_id=previous_product,
            selected_product_id=selected.item_name,
            selected_template_id=selected.template_id,
            target_path=tuple(sorted(_path_products(selected.item_name, catalog))),
            stretch=stretch,
            evidence={"previous_status": status, "previous_quantity": previous_quantity},
        )

    if status == "partial" and previous_outcome.delivered_quantity > 0:
        delivered = previous_outcome.delivered_quantity
        selected = _closest(_same_product(candidates, previous_product), delivered * 1.25)
        if selected is None:
            path_products = _path_products(previous_product, catalog)
            selected = _closest(
                (
                    candidate
                    for candidate in candidates
                    if candidate.item_name in path_products
                ),
                delivered * 1.25,
            )
        if selected is None:
            return None, None
        return selected, CustomerFollowUp(
            reason="partial_near_capacity",
            parent_epoch_index=previous_spec.epoch_index,
            parent_product_id=previous_product,
            selected_product_id=selected.item_name,
            selected_template_id=selected.template_id,
            target_path=tuple(sorted(_path_products(selected.item_name, catalog))),
            evidence={
                "previous_status": status,
                "delivered_quantity": previous_outcome.delivered_quantity,
                "target_quantity": delivered * 1.25,
            },
        )

    if is_frontier and capability_delta is not None and capability_delta.meaningful_progress:
        same = _same_product(candidates, previous_product)
        selected = _closest(same, max(previous_outcome.delivered_quantity, previous_quantity * 0.75))
        reason = "frontier_progress_repeat"
        if selected is None:
            path_products = _path_products(previous_product, catalog)
            nearby = [candidate for candidate in candidates if candidate.item_name in path_products]
            selected = _closest(nearby, max(previous_outcome.delivered_quantity, 1) * 1.25)
            reason = "frontier_progress_nearby"
        if selected is not None:
            return selected, CustomerFollowUp(
                reason=reason,
                parent_epoch_index=previous_spec.epoch_index,
                parent_product_id=previous_product,
                selected_product_id=selected.item_name,
                selected_template_id=selected.template_id,
                target_path=tuple(sorted(_path_products(selected.item_name, catalog))),
                evidence={
                    "previous_status": status,
                    "capability_progress": capability_delta.path_progress,
                    "new_technologies": list(capability_delta.new_technologies),
                    "new_recipes": list(capability_delta.new_recipes),
                },
            )

    # Expired/abandoned or zero-progress orders descend to a direct recipe
    # prerequisite.  If the sampled pool does not contain one, a smaller retry
    # is less dangerous than selecting a new unrelated frontier.
    prerequisites = _prerequisite_products(previous_product, catalog)
    nearby = [candidate for candidate in candidates if candidate.item_name in prerequisites]
    selected = _closest(nearby, max(previous_outcome.delivered_quantity, 1) * 1.25)
    if selected is None:
        same = [
            candidate
            for candidate in _same_product(candidates, previous_product)
            if candidate.quantity < previous_quantity or candidate.deadline_ticks > previous_spec.deadline_ticks
        ]
        selected = min(same, key=lambda candidate: (candidate.quantity, -candidate.deadline_ticks), default=None)
    if selected is None:
        return None, None
    return selected, CustomerFollowUp(
        reason="zero_progress_backoff",
        parent_epoch_index=previous_spec.epoch_index,
        parent_product_id=previous_product,
        selected_product_id=selected.item_name,
        selected_template_id=selected.template_id,
        target_path=tuple(sorted(_path_products(selected.item_name, catalog))),
        evidence={
            "previous_status": status,
            "capability_progress": bool(capability_delta and capability_delta.meaningful_progress),
            "prerequisites": sorted(prerequisites),
        },
    )


__all__ = ["choose_follow_up_candidate"]
