from typing import Union

from entities import Recipe, Ingredient
from instance import PLAYER
from game_types import Prototype
from tools.tool import Tool


class GetPrototypeRecipe(Tool):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self, prototype: Union[Prototype, str]) -> Recipe:
        """
        Get the recipe (cost to make) of the given entity prototype.
        :param prototype: Prototype to get recipe from
        :return: Recipe of the given prototype
        """

        if isinstance(prototype, Prototype):
            name, _ = prototype.value
        else:
            name = prototype

        response, elapsed = self.execute(PLAYER, name)

        if not isinstance(response, dict):
            raise Exception(f"Could not get recipe of {name}", response)

        parsed_response = self.parse_lua_dict(response)

        ingredients = [Ingredient(name=ingredient['name'], count=ingredient['amount'], type=ingredient['type'] if 'type' in ingredient else None) for ingredient in parsed_response['ingredients']]

        return Recipe(name=name, ingredients=ingredients)
