from controllers._action import Action

from factorio_entities import Entity
from factorio_instance import PLAYER, Direction


class RotateEntity(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self, entity: Entity, direction: Direction = Direction.UP) -> bool:
        """
        Rotate an entity at position (x, y) if it exists on the world.
        :param entity: Entity to rotate
        :param direction: Direction to rotate
        :example rotate_entity(iron_chest, Direction.UP)
        :return: True if rotation was successful
        """
        if not isinstance(entity, Entity):
            raise ValueError("The first argument must be an Entity object")
        if entity is None:
            raise ValueError("The entity argument must not be None")
        if not isinstance(direction, Direction):
            raise ValueError("The second argument must be a Direction")

        try:
            x, y = self.get_position(entity.position)

            # get metaclass from pydantic model
            metaclass = entity.__class__

            factorio_direction = Direction.to_factorio_direction(direction)

            response, elapsed = self.execute(PLAYER, x, y, factorio_direction)

            if not response:
                raise Exception("Could not rotate.", response)

        except Exception as e:
            raise e
        try:
            for key, value in response.items():
                if isinstance(value, dict):
                    if 1 in value.keys():
                        response[key] = []
                        for sub_key, sub_value in value.items():
                            if 1 in sub_value.keys():
                                prototype_suffix = sub_value[1]
                                sub_value['name'] = sub_value['name'] + '-' + prototype_suffix
                                # Remove the 1 key from the dictionary
                                sub_value.pop(1)
                            response[key].append(sub_value)
        except Exception as e:
            raise Exception("Could not update entity after rotation.", e)

        if 'prototype' not in response.keys():
            response['prototype'] = entity

        # Ensure the position is properly aligned to the grid
        if 'position' in response:
            response['position'] = {
                'x': round(response['position']['x'] * 2) / 2,
                'y': round(response['position']['y'] * 2) / 2
            }

        if 'direction' in response.keys():
            response['direction'] = response['direction']

            # If we are dealing with an inserter, we need to adjust the direction from left to right, top to bottom, etc.
            #if 'inserter' in response['name']:
            #    response['direction'] = (((response['direction'] + 1) % 4) + 1 ) % 4

        try:
            object = metaclass(**response)
        except Exception as e:
            raise Exception(f"Could not create {entity.name} object from response: {response}", e)


        return object

