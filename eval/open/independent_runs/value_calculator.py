from typing import Dict, Set, List
import math
import json
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class Recipe:
    """Represents a recipe with ingredients and their amounts"""

    name: str
    ingredients: Dict[str, float]  # ingredient_name -> amount
    energy: float = 1.0  # Default energy cost


class ValueCalculator:
    """Calculates item values based on recipes and complexity"""

    def __init__(self, recipes_file: str, beta: float = 1.025):
        self.beta = beta
        self.raw_prices = {
            "iron-ore": 3.1,
            "copper-ore": 3.6,
            "coal": 3.0,
            "stone": 2.4,
            "uranium-ore": 8.2,
        }
        self.recipes = self._load_recipes(recipes_file)
        self.cached_values = {}
        self._calculate_all_values()

    def _load_recipes(self, recipes_file: str) -> Dict[str, List[Recipe]]:
        """Load and parse recipes from JSONL file"""
        recipes = defaultdict(list)

        with open(recipes_file, "r") as f:
            for line in f:
                recipe_data = json.loads(line)
                recipe = self._parse_recipe(recipe_data)
                if recipe:
                    recipes[recipe_data["name"]].append(recipe)

        return recipes

    def _parse_recipe(self, recipe_data: Dict) -> Recipe:
        """Parse a recipe from JSON format"""
        ingredients = {}

        def process_ingredient(ing_data):
            name = ing_data["name"]
            amount = float(ing_data.get("amount", 1))

            if ing_data.get("ingredients"):
                for sub_ing in ing_data["ingredients"]:
                    sub_name = sub_ing["name"]
                    sub_amount = float(sub_ing.get("amount", 1))
                    ingredients[sub_name] = (
                        ingredients.get(sub_name, 0) + sub_amount * amount
                    )
            else:
                ingredients[name] = ingredients.get(name, 0) + amount

        for ing in recipe_data.get("ingredients", []):
            process_ingredient(ing)

        return Recipe(name=recipe_data["name"], ingredients=ingredients)

    def _complexity_multiplier(self, num_ingredients: int) -> float:
        """Calculate complexity multiplier α(n)"""
        if num_ingredients <= 1:
            return 1.0
        return self.beta ** (num_ingredients - 2)

    def _energy_cost(self, recipe: Recipe, base_cost: float) -> float:
        """Calculate energy cost term E(r, Cr)"""
        return math.log(recipe.energy + 1) * math.sqrt(base_cost)

    def _calculate_value(self, item: str, visited: Set[str] = None) -> float:
        """Calculate value of an item using the recursive formula"""
        if visited is None:
            visited = set()

        # Return cached value if available
        if item in self.cached_values:
            return self.cached_values[item]

        # Return raw price for basic resources
        if item in self.raw_prices:
            self.cached_values[item] = self.raw_prices[item]
            return self.raw_prices[item]

        # Detect cycles
        if item in visited:
            return float("inf")

        visited.add(item)

        # If no recipes available, treat as raw resource with default value
        if item not in self.recipes:
            self.cached_values[item] = 0.1  # Default value for unknown items
            return 0.1

        min_value = float("inf")

        # Calculate value using each available recipe
        for recipe in self.recipes[item]:
            base_cost = 0
            total_ingredient_value = 0

            for ing_name, amount in recipe.ingredients.items():
                ing_value = self._calculate_value(ing_name, visited.copy())
                base_cost += ing_value * amount
                total_ingredient_value += ing_value * amount

            complexity_mult = self._complexity_multiplier(len(recipe.ingredients))
            energy_cost = self._energy_cost(recipe, base_cost)

            recipe_value = total_ingredient_value * complexity_mult + energy_cost
            min_value = min(min_value, recipe_value)

        visited.remove(item)
        self.cached_values[item] = min_value
        return min_value

    def _calculate_all_values(self):
        """Pre-calculate values for all items in recipes"""
        items = set()
        for recipe_list in self.recipes.values():
            for recipe in recipe_list:
                items.add(recipe.name)
                items.update(recipe.ingredients.keys())

        for item in items:
            self._calculate_value(item)

    def get_value(self, item: str) -> float:
        """Get the calculated value for an item"""
        print(f"Getting value of {item} - {self.cached_values.get(item, 10.0)}")
        return self.cached_values.get(item, 10.0)  # Default value for unknown items
