from controllers.__action import Action

from factorio_entities import Entity, Direction as DirectionA # We have 2 Direction objects to avoid circular deps
from factorio_instance import PLAYER, Direction
from factorio_types import prototype_by_name


class RotateEntity(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self, entity: Entity, direction: Direction = Direction.UP) -> Entity:
        """
        Rotate an entity at position (x, y) if it exists on the world.
        :param entity: Entity to rotate
        :param direction: Direction to rotate
        :example rotate_entity(iron_chest, Direction.UP)
        :return: Returns the rotated entity
        """
        if not isinstance(entity, Entity):
            raise ValueError("The first argument must be an Entity object")
        if entity is None:
            raise ValueError("The entity argument must not be None")
        if not isinstance(direction, (Direction, DirectionA)) and not (hasattr(direction, "name") and hasattr(direction, "value")):
            raise ValueError("The second argument must be a Direction")

        try:
            x, y = self.get_position(entity.position)

            # get metaclass from pydantic model
            metaclass = entity.__class__

            factorio_direction = Direction.to_factorio_direction(direction)

            response, elapsed = self.execute(PLAYER, x, y, factorio_direction, entity.name)

            if not response:
                raise Exception(f"Could not rotate: {response}")

        except Exception as e:
            raise e

        cleaned_response = self.clean_response(response)

        if 'prototype' not in cleaned_response.keys():

            if isinstance(entity.prototype, str):
                prototype = prototype_by_name[entity.name]
            else:
                prototype = entity.prototype
            cleaned_response['prototype'] = prototype

        # Ensure the position is properly aligned to the grid
        if 'position' in cleaned_response:
            cleaned_response['position'] = {
                'x': round(cleaned_response['position']['x'] * 2) / 2,
                'y': round(cleaned_response['position']['y'] * 2) / 2
            }

        if 'direction' in cleaned_response.keys():
            cleaned_response['direction'] = cleaned_response['direction']

        try:
            object = metaclass(**cleaned_response)
        except Exception as e:
            raise Exception(f"Could not create {entity.name} object from response: {response}", e)

        return object

