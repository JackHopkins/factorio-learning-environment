# curriculum_strategies.py
from abc import ABC, abstractmethod
from trace import Trace
from typing import Dict, Tuple, List
import logging

from datasetgen.recipe_manager import RecipeManager, Recipe

logger = logging.getLogger(__name__)


class CurriculumStrategy(ABC):
    """Abstract base class for curriculum strategies"""

    @abstractmethod
    def generate_next_task(self, task_history: List[Trace], instance) -> Tuple[str, Dict]:
        """Generate next task description and target P/L"""
        pass

    @abstractmethod
    def update_task_history(self, trace: Trace):
        """Update any strategy-specific state based on task completion"""
        pass

    @abstractmethod
    def get_task_dir(self, trace: Trace):
        """Get the name of the subdirectory we should store the task-specific trace"""


class RecipeBasedCurriculum(CurriculumStrategy):
    def __init__(self, recipe_file: str, difficulty_step: float = 0.2):
        self.recipe_manager = RecipeManager(recipe_file)
        self.difficulty_step = difficulty_step

    def get_task_dir(self, trace: Trace):
        return trace.task_description.replace(" ", "_").replace("-", "_").lower()
    def generate_next_task(self, task_history: List[Trace], instance) -> Dict:
        if not task_history or not any([t for t in task_history if t.success]):
            logger.info("No previous tasks - starting with initial iron plate production")
            initial_pl = {
                "input": {"iron-ore": 10},
                "output": {"iron-plate": 10}
            }
            return "Set up initial iron plate production", initial_pl

        # Get accumulated outputs from successful tasks
        accumulated_outputs = self._get_accumulated_outputs(task_history)

        # Find craftable recipes and select next one
        craftable_recipes = self.recipe_manager.get_craftable_recipes(accumulated_outputs)
        logger.info("Found %d craftable recipes", len(craftable_recipes))

        next_recipe = self._select_next_recipe(craftable_recipes, task_history)
        logger.info("Selected recipe: %s", next_recipe.name if next_recipe else "None")

        # Generate new target P/L
        new_target = self._generate_target_pl(next_recipe, task_history)

        return f"Create {next_recipe.name}", new_target

    def _generate_target_pl(self, next_recipe: Recipe, task_history: List[Trace]) -> Dict[str, Dict[str, int]]:
        """Generate target P/L including the new recipe"""
        last_task = next(reversed([t for t in task_history if t.success]), None)
        if not last_task:
            return {
                "input": {"iron-ore": 10},
                "output": {"iron-plate": 10}
            }

        new_target = {
            "input": {
                item: int(count * (1 + self.difficulty_step))
                for item, count in last_task.achieved_pl["input"].items()
            },
            "output": {
                item: int(count * (1 + self.difficulty_step))
                for item, count in last_task.achieved_pl["output"].items()
            }
        }

        if next_recipe:
            # Add recipe ingredients to input
            for ingredient in next_recipe.ingredients:
                new_target["input"][ingredient.name] = new_target["input"].get(
                    ingredient.name, 0) + ingredient.amount
            # Add recipe output
            new_target["output"][next_recipe.name] = 1

        return new_target

    def _select_next_recipe(self, craftable_recipes: List[Recipe], task_history: List[Trace]) -> Recipe:
        """Select the next recipe to target based on complexity and previous tasks"""
        if not craftable_recipes:
            return None

        # Score recipes based on:
        # 1. Number of ingredients
        # 2. Depth of ingredient tree
        # 3. Whether it's been crafted before
        def recipe_score(recipe: Recipe) -> float:
            ingredient_count = len(recipe.ingredients)
            depth = self._get_recipe_depth(recipe)
            previously_crafted = any(
                recipe.name in task.achieved_pl["output"]
                for task in task_history if task.success
            )
            return (ingredient_count * 0.5 + depth * 0.3) * (0.5 if previously_crafted else 1.0)

        return max(craftable_recipes, key=recipe_score)

    def _get_recipe_depth(self, recipe: Recipe, depth: int = 0) -> int:
        """Calculate the depth of a recipe's ingredient tree"""
        if not recipe.ingredients:
            return depth
        return max(self._get_recipe_depth(ingredient, depth + 1)
                   for ingredient in recipe.ingredients)

    def update_task_history(self, trace: Trace):
        # No special state to update for recipe-based curriculum
        pass

    def _get_accumulated_outputs(self, task_history: List[Trace]) -> Dict[str, int]:
        accumulated = {}
        for task in task_history:
            if task.success:
                for item, count in task.achieved_pl["output"].items():
                    accumulated[item] = accumulated.get(item, 0) + count
        return accumulated
