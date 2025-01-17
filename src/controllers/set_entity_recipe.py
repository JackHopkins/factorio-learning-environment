from controllers.__action import Action
from typing import Tuple

from factorio_entities import Recipe, Entity
from factorio_instance import PLAYER
from factorio_types import Prototype


class SetEntityRecipe(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self, entity: Entity, prototype: Prototype,
                # **kwargs
                 ) -> bool:
        """
        Sets the recipe of an given entity.
        :param entity: Entity to set recipe
        :param recipe: Recipe to set
        :return: True if recipe was set successfully
        """

        x, y = entity.position.x, entity.position.y
        try:

            name, _ = prototype.value
        except AttributeError as e:
            raise ValueError(f"Invalid entity type: {prototype}")

        #if not relative:
        #    x -= self.game_state.last_observed_player_location[0]
        #    y -= self.game_state.last_observed_player_location[1]

        response, elapsed = self.execute(PLAYER, name, x, y)

        if not isinstance(response, dict):
            raise Exception(f"Could not set recipe to {name}"+str(response).split(":")[-1].strip())

        cleaned_response = self.clean_response(response)

        # Find the matching Prototype
        matching_prototype = None
        for prototype in Prototype:
            if prototype.value[0] == cleaned_response['name'].replace('_', '-'):
                matching_prototype = prototype
                break

        if matching_prototype is None:
            print(f"Warning: No matching Prototype found for {cleaned_response['name']}")
            raise Exception(f"Could not set recipe to {name}", response)

        metaclass = matching_prototype.value[1]

        #obj = get_attr(factorio_entities, entity.prototype) (**response)
        # for key, value in response.items():
        #     try:
        #         value_class = entity.__getattribute__(key).__class__
        #         # if value_class is a pydantic model, construct it
        #         if hasattr(value_class, "construct"):
        #             response[key] = value_class.construct(**value)
        #         elif isinstance(value, dict):
        #             if 1 in value.keys():
        #                 response[key] = []
        #                 for sub_key, sub_value in value.items():
        #                     response[key].append(sub_value)
        #     except AttributeError as e:
        #         pass
        entity = metaclass(**cleaned_response, prototype=matching_prototype)
        #entity = entity.__class__.construct(**response)
        entity.recipe = name

        return entity
