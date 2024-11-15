# recipe_manager.py
import json
from typing import Dict, List, Set
from dataclasses import dataclass

from factorio_types import prototype_by_name


@dataclass
class RecipeIngredient:
    name: str
    amount: int
    type: str
    ingredients: List['RecipeIngredient']


@dataclass
class Recipe:
    name: str
    ingredients: List[RecipeIngredient]


class RecipeManager:
    def __init__(self, recipe_file: str):
        self.recipes: Dict[str, Recipe] = self._load_recipes(recipe_file)

    def _load_recipes(self, recipe_file: str) -> Dict[str, Recipe]:
        recipes = {}
        with open(recipe_file, 'r') as f:
            for line in f:
                recipe_data = json.loads(line)
                recipes[recipe_data['name']] = self._parse_recipe(recipe_data)
        return recipes

    def _parse_recipe(self, data: dict) -> Recipe:
        return Recipe(
            name=data['name'],
            ingredients=[self._parse_ingredient(i) for i in data['ingredients']]
        )

    def _parse_ingredient(self, data: dict) -> RecipeIngredient:
        return RecipeIngredient(
            name=data['name'],
            amount=data['amount'],
            type=data['type'],
            ingredients=[self._parse_ingredient(i) for i in data['ingredients']]
        )

    def get_craftable_recipes(self, available_items: Dict[str, int]) -> List[Recipe]:
        """Returns recipes that can be crafted with given items"""
        craftable = []
        for recipe in self.recipes.values():
            if self._can_craft(recipe, available_items):
                craftable.append(recipe)
        return craftable

    def _can_craft(self, recipe: Recipe, available_items: Dict[str, int]) -> bool:
        """Check if a recipe can be crafted with available items"""
        prototype_names = prototype_by_name.keys()
        if recipe.name not in prototype_names:
            return False

        for ingredient in recipe.ingredients:
            if ingredient.name not in available_items:
                return False
            if available_items[ingredient.name] < ingredient.amount:
                return False
            if ingredient.name not in list(prototype_names):
                return False


        return True