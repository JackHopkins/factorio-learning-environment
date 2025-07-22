from typing import Dict, List, Tuple, Any
from copy import deepcopy

from fle.commons.models.achievements import ProductionFlows


class AchievementTracker:
    """Tracks and calculates achievements from production flows."""

    @staticmethod
    def calculate_achievements(
        pre: ProductionFlows, post: ProductionFlows
    ) -> Dict[str, Dict[str, float]]:
        """Calculate achievements between two production states."""
        if not pre.is_valid() or not post.is_valid():
            return {"static": {}, "dynamic": {}}

        post = deepcopy(post)
        post.static_items = AchievementTracker._get_static_items(pre, post)

        return AchievementTracker._process_achievements(pre, post)

    @staticmethod
    def _get_static_items(
        pre: ProductionFlows, post: ProductionFlows
    ) -> Dict[str, float]:
        """Calculate static items from production flows."""
        new_flows = pre.get_new_flows(post)
        static_items = deepcopy(new_flows.harvested)

        for craft in new_flows.crafted:
            for item, value in craft["outputs"].items():
                static_items[item] = static_items.get(item, 0) + value

        return static_items

    @staticmethod
    def _process_achievements(
        pre: ProductionFlows, post: ProductionFlows
    ) -> Dict[str, Dict[str, float]]:
        """Process achievements from production flows."""
        achievements = {"static": {}, "dynamic": {}}

        for item in post.output:
            post_value = post.output[item]
            pre_value = pre.output.get(item, 0)

            if post_value > pre_value:
                created = post_value - pre_value
                static = post.static_items.get(item, 0)

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
    achievements = AchievementTracker.calculate_achievements(pre_flows, post_flows)

    return result.splitlines(), result, error, achievements
