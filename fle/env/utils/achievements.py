from typing import Dict, List, Tuple, Any
from copy import deepcopy

from fle.commons.models.achievements import ProductionFlows


def calculate_achievements(
    pre: ProductionFlows, post: ProductionFlows
) -> Dict[str, Dict[str, float]]:
    """Calculate achievements between two production states."""
    achievements = {"static": {}, "dynamic": {}}
    if not pre.is_valid() or not post.is_valid():
        print("Warning: Invalid production flows")
        return achievements

    post = deepcopy(post)

    # Calculate static items directly
    new_flows = pre.get_new_flows(post)
    static_items = deepcopy(new_flows.harvested)

    # Add crafted outputs to static items
    for craft in new_flows.crafted:
        for item, value in craft["outputs"].items():
            static_items[item] = static_items.get(item, 0) + value

    for item in post.output:
        post_value = post.output[item]
        pre_value = pre.output.get(item, 0)

        if post_value > pre_value:
            created = post_value - pre_value
            static = static_items.get(item, 0)

            if static > 0:
                achievements["static"][item] = static
            if created > static:
                achievements["dynamic"][item] = created - static

    return achievements


def eval_program_with_achievements(
    instance: Any, program: str
) -> Tuple[List[str], str, bool, Dict[str, Dict[str, float]]]:
    """Evaluate a program and calculate achievements."""
    pre_flows = ProductionFlows.from_dict(
        instance.first_namespace._get_production_stats()
    )

    try:
        score, goal, result = instance.eval_with_error(program, timeout=300)
        error = False
    except Exception as e:
        result = str(e)
        error = True

    post_flows = ProductionFlows.from_dict(
        instance.first_namespace._get_production_stats()
    )
    achievements = calculate_achievements(pre_flows, post_flows)

    return result.splitlines(), result, error, achievements
