import json
from typing import Any, Dict, Set, List, Tuple
import os
from pathlib import Path

from agents import TaskResponse
from env.src.entities import Entity
from env.src.instance import FactorioInstance
from env.src.utils.achievements import eval_program_with_achievements
from eval.tasks.task_abc import TaskABC
from models.achievements import ProductionFlows

LAB_PLAY_POPULATED_STARTING_INVENTORY = {"coal": 500, "burner-mining-drill": 50, "wooden-chest": 10,
                                         "burner-inserter": 50, "inserter": 50, "transport-belt": 500,
                                         "stone-furnace": 10, "boiler": 2, "offshore-pump": 2, "steam-engine": 2,
                                         "electric-mining-drill": 50, "small-electric-pole": 500, "pipe": 500,
                                         "assembling-machine-2": 10, "electric-furnace": 10, "pipe-to-ground": 100,
                                         "underground-belt": 100,
                                         "pumpjack": 10, "oil-refinery": 5, "chemical-plant": 5, "storage-tank": 10,
                                         # "solar-panel": 50,
                                         }

INSTRUCTIONS = """
You must create an AUTOMATIC factory that automatically creates a target entity by itself. You are given the entity for which you need to create a factory for. You are also given the target throughput that the factory must achieve.

After each step, the throughput of your factory is evaluated during 60 seconds of worktime and the results are supplied to you in the response. You'll also receive a progress score that rewards you for creating prerequisites of the target item.

If you have achieved the target throughput, make sure to fuel the factory and make small improvements but do not break the factory.
"""

CRAFTING_STATISTICS = """
Crafting speeds for solids
Iron gear wheel - 120 per 60 seconds
Copper Cable - 240 per 60 seconds
Pipe - 120 per 60 seconds
Steel plate - 3.75 per 60 seconds
Engine unit - 6 per 60 seconds
Electronic circuit - 120 per 60 seconds
Electric Engine unit - 6 per 60 seconds
Flying robot frame - 3 per 60 seconds
Sulfur - 120 per 60 seconds. Can only be produced by a chemical plant
Plastic bar - 120 per 60 seconds. Can only be produced by a chemical plant
Advanced circuit - 10 per 60 seconds
Processing unit - 6 per 60 seconds
Low density structure - 4 per 60 seconds
Copper plate - 18.75 per 60 seconds
Iron plate - 18.75 per 60 seconds
Stone brick - 18.75 per 60 seconds
Battery - 20 per 60 seconds. Can only be produced by a chemical plant
"""


class ProgressiveThroughputTask(TaskABC):
    """
    A task in which the agent must meet a certain production quota for an entity over a 60-second period
    _after_ the program is executed. This measures purely automated production.

    This task rewards making intermediate progress by providing partial rewards for creating prerequisites
    of the target entity. The rewards are proportional to the ingredient's contribution to the recipe.
    """

    def __init__(self, trajectory_length, goal_description: str, task_key: str,
                 throughput_entity: Entity, quota: int, holdout_wait_period: int,
                 recipes_file: str, prerequisite_discount: float = 0.5,
                 pre_holdout_wait_period: int = 0,
                 include_crafting_stats: bool = True,
                 use_populated_inventory: bool = True):

        # Add crafting statistics to the goal description if requested
        self.include_crafting_stats = include_crafting_stats
        if include_crafting_stats:
            goal_description += "\n\n##Useful statistics\n" + CRAFTING_STATISTICS

        goal_description += f"\n{INSTRUCTIONS}"

        starting_inventory = LAB_PLAY_POPULATED_STARTING_INVENTORY if use_populated_inventory else {}

        super().__init__(trajectory_length,
                         starting_inventory=starting_inventory,
                         goal_description=goal_description,
                         task_key=task_key,
                         all_technology_researched=True)

        self.throughput_entity = throughput_entity
        self.quota = quota
        self.holdout_wait_period = holdout_wait_period
        self.pre_holdout_wait_period = pre_holdout_wait_period
        self.starting_game_state = None
        self.prerequisite_discount = prerequisite_discount

        # Load recipe data
        self.recipes = self._load_recipes(recipes_file)

        # Calculate proportional values for ingredients
        self.proportional_values = {}
        if self.throughput_entity in self.recipes:
            self.proportional_values = self._calculate_proportional_values(self.recipes[self.throughput_entity])

    def _load_recipes(self, recipes_file: str) -> Dict:
        """Load recipe data from a JSONL file."""
        recipes = {}
        try:
            path = Path(recipes_file)
            with open(path, 'r') as f:
                for line in f:
                    recipe = json.loads(line.strip())
                    recipes[recipe['name']] = recipe
            return recipes
        except Exception as e:
            print(f"Error loading recipes from {recipes_file}: {e}")
            return {}

    def _calculate_ingredient_needs(self, recipe, needs=None, multiplier=1):
        """
        Calculate the total needs of all ingredients recursively.
        Returns a dictionary with ingredients as keys and total amounts as values.
        """
        if needs is None:
            needs = {}

        # For each ingredient in the recipe
        for ingredient in recipe.get("ingredients", []):
            ingredient_name = ingredient["name"]
            ingredient_amount = ingredient["amount"] * multiplier

            # Add or update the amount needed
            if ingredient_name not in needs:
                needs[ingredient_name] = 0
            needs[ingredient_name] += ingredient_amount

            # Recursively process this ingredient's ingredients
            if "ingredients" in ingredient and ingredient["ingredients"]:
                self._calculate_ingredient_needs(ingredient, needs, ingredient_amount)

        return needs

    def _calculate_proportional_values(self, recipe):
        """
        Calculate the proportional value of each ingredient in a recipe.
        The value is based on the ingredient's proportion of the total needs.
        """
        # Calculate total ingredient needs
        needs = self._calculate_ingredient_needs(recipe)

        # Calculate the sum of all ingredient amounts
        total_needs_sum = sum(needs.values())

        # Calculate proportion of each ingredient
        proportions = {}
        for item, amount in needs.items():
            proportions[item] = amount / total_needs_sum

        # The target item (recipe name) gets full value
        proportions[recipe["name"]] = 1.0

        return proportions

    def verify(self, score: float, instance: FactorioInstance, step_statistics: Dict) -> TaskResponse:
        """
        Verify the task by measuring throughput during the holdout period.
        """
        max_achieved_throughput = 0
        max_achievements = None

        # Wait the pre-holdout period if specified
        if self.pre_holdout_wait_period > 0:
            instance.namespace.sleep(self.pre_holdout_wait_period)

        # Measure throughput over multiple holdout periods, keeping the maximum
        while True:
            result_list, result, error, achievements = eval_program_with_achievements(
                program=f"sleep({self.holdout_wait_period})",
                instance=instance
            )

            if max_achievements is None:
                max_achievements = achievements

            dynamic_achievements = achievements.get("dynamic", {})
            target_throughput = dynamic_achievements.get(self.throughput_entity, 0)

            if target_throughput > max_achieved_throughput:
                max_achieved_throughput = target_throughput
                max_achievements = achievements
            else:
                break

        # Calculate the progressive reward score
        progressive_score = self._calculate_progressive_score(dynamic_achievements)

        # Add the progressive score to the meta information
        if max_achievements and "meta" not in max_achievements:
            max_achievements["meta"] = {}

        if max_achievements:
            max_achievements["meta"]["progressive_score"] = progressive_score

        return TaskResponse(
            success=max_achieved_throughput >= self.quota,
            meta={"achievements": max_achievements}
        )

    def _calculate_progressive_score(self, achievements: Dict[str, int]) -> float:
        """
        Calculate a progressive score based on achievements and proportional ingredient values.

        Args:
            achievements: Dictionary of items produced and their counts

        Returns:
            A score that rewards progress toward the target item
        """
        if not achievements:
            return 0.0

        # Full reward for the target item
        target_count = achievements.get(self.throughput_entity, 0)
        total_score = target_count * 1.0

        # Calculate partial rewards for prerequisites based on their proportional values
        for item, count in achievements.items():
            if item != self.throughput_entity and item in self.proportional_values:
                # Apply the prerequisite discount (e.g., 0.5) and then multiply by the proportional value
                partial_reward = count * self.prerequisite_discount * self.proportional_values[item]
                total_score += partial_reward

        return total_score

    def _to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for serialization."""
        return {
            "task": self.goal_description,
            "throughput_entity": self.throughput_entity,
            "quota": self.quota,
            "trajectory_length": self.trajectory_length,
            "starting_inventory": self.starting_inventory,
            "initial_state": self.starting_game_state.to_raw() if self.starting_game_state else None,
        }

    def setup_instance(self, instance):
        """Code to provision the task environment"""
        pass

    def enhance_response_with_task_output(self, response: str, task_response: TaskResponse) -> str:
        """Add task specific information to the environment response."""
        task_throughputs = task_response.meta.get("achievements", None)

        if task_throughputs:
            dynamic_throughput = task_throughputs.get("dynamic", {})
            progressive_score = task_throughputs.get("meta", {}).get("progressive_score", 0)

            response += f"\n\nHere is the current throughput of your factory: {dynamic_throughput} created per 60 seconds"
            response += f"\n\nProgress score: {progressive_score:.2f} (higher score means you're getting closer to the target)"

        return response

    def reward(self, raw_reward: float, achievements: Dict, flows: ProductionFlows, ticks: int) -> float:
        """
        Return the reward for a program in this task.
        Uses proportional reward structure based on creating prerequisites.

        Args:
            raw_reward: The base reward
            achievements: Production achievements
            flows: Production flows
            ticks: Number of ticks elapsed

        Returns:
            Modified reward incorporating progressive score - rewards for partial ingredient automation
        """
        # Get the dynamic achievements (items produced during this period)
        dynamic_achievements = achievements.get("dynamic", {})

        # Calculate progressive score
        progressive_score = self._calculate_progressive_score(dynamic_achievements)

        # Use progressive score as the reward
        return progressive_score