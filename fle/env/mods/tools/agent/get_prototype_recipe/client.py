from typing import Union

from fle.env import Recipe, Ingredient, Product
from fle.env.game_types import Prototype, RecipeName
from fle.env.tools import Tool


class GetPrototypeRecipe(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self, prototype: Union[Prototype, RecipeName, str]) -> Recipe:
        """
        Get the recipe (cost to make) of the given entity prototype.
        :param prototype: Prototype to get recipe from
        :return: Recipe of the given prototype
        """

        if isinstance(prototype, Prototype):
            name, _ = prototype.value
        elif isinstance(prototype, RecipeName):
            name = prototype.value
        else:
            name = prototype

        response, elapsed = self.execute(self.player_index, name)

        if not isinstance(response, dict):
            raise Exception(
                f"Could not get recipe of {name} - {response}. You may need to use the RecipeName enum instead."
            )

        parsed_response = self.parse_lua_dict(response)

        ingredients = [
            Ingredient(
                name=ingredient["name"],
                count=ingredient["amount"],
                type=ingredient["type"] if "type" in ingredient else None,
            )
            for ingredient in parsed_response["ingredients"]
        ]
        products = [
            Product(
                name=product["name"],
                count=product["amount"],
                probability=product["probability"],
                type=product["type"] if "type" in product else None,
            )
            for product in parsed_response["products"]
        ]

        return Recipe(name=name, ingredients=ingredients, products=products)
