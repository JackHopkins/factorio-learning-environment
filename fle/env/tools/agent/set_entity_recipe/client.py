from typing import Union

from fle.env.entities import Entity
from fle.env.game_types import Prototype, RecipeName
from fle.env.tools import Tool


class SetEntityRecipe(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(
        self, entity: Entity, prototype: Union[Prototype, RecipeName]
    ) -> Entity:
        """
        Sets the recipe of an given entity.
        :param entity: Entity to set recipe
        :param prototype: The prototype to create, or a recipe name for more complex processes
        :return: Entity that had its recipe set
        """

        x, y = entity.position.x, entity.position.y

        if isinstance(prototype, Prototype):
            name, _ = prototype.value
        elif isinstance(prototype, RecipeName):
            name = prototype.value
        else:
            raise ValueError(f"Invalid entity type: {prototype}")

        response, elapsed = self.execute(self.player_index, name, x, y)

        if not isinstance(response, dict):
            raise Exception(
                f"Could not set recipe to {name}" + str(response).split(":")[-1].strip()
            )

        cleaned_response = self.clean_response(response)

        # Find the matching Prototype
        matching_prototype = None
        for prototype in Prototype:
            if prototype.value[0] == cleaned_response["name"].replace("_", "-"):
                matching_prototype = prototype
                break

        if matching_prototype is None:
            print(
                f"Warning: No matching Prototype found for {cleaned_response['name']}"
            )
            raise Exception(f"Could not set recipe to {name}", response)

        metaclass = matching_prototype.value[1]

        entity = metaclass(**cleaned_response, prototype=matching_prototype)

        # Handle filter inserters differently
        if "filter" in entity.name:
            entity.filter = name  # Store the filter item
        else:
            entity.recipe = name  # Store the recipe for assembling machines

        return entity
