from controllers._action import Action
from typing import Tuple, OrderedDict, Union

from factorio_entities import Recipe, Entity, Inventory, Ingredient
from factorio_instance import PLAYER
from factorio_types import Prototype
from utilities.parse_lua_dict import parse_lua_dict


class GetPrototypeRecipe(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self, prototype: Union[Prototype, str]) -> Recipe:
        """
        Get the recipe of the given entity prototype.
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

        parsed_response = parse_lua_dict(response)

        def _get_prototype_from_name(name: str) -> Prototype:
            for prototype in Prototype:
                if prototype.value[0] == name:
                    return prototype

        ingredients = [Ingredient(name=ingredient['name'], count=ingredient['amount']) for ingredient in parsed_response['ingredients']]

        return Recipe(name=name, ingredients=ingredients)
