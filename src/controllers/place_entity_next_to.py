import math

from controllers._action import Action
from factorio_entities import Position, Entity
from factorio_instance import PLAYER, Direction
from factorio_types import Prototype


class PlaceEntityNextTo(Action):

    def __init__(self, *args):
        super().__init__(*args)

    def __call__(self,
                 entity: Prototype,
                 reference_position: Position = Position(x=0, y=0),
                 direction: Direction = 1,
                 spacing: int = 0,
                 ) -> Entity:
        """
        Places an entity next to an existing entity, with an optional space in-between (0 space means adjacent).
        In order to place something with a gap, you must increase the spacing parameter.
        :param entity: Entity to place
        :param reference_position: Position of existing entity or position to place entity next to
        :param direction: Direction to place entity from reference_position
        :param spacing: Space between entity and reference_position
        :example: place_entity_next_to(Prototype.WoodenChest, Position(x=0, y=0), direction=Direction.UP, spacing=1)
        :return: Entity placed (with position of x=0, y=-1)
        """
        try:
            name, metaclass = entity.value
            #x, y = math.floor(reference_position.x*2)/2, math.floor(reference_position.y*2)/2
            x, y = reference_position.x, reference_position.y

            if isinstance(direction, Direction):
                n_dir = direction.value
            else:
                n_dir = direction

            response, elapsed = self.execute(PLAYER, name, x, y, n_dir, spacing)#-0.5)

            if not isinstance(response, dict) or response == {}:
                raise Exception(f"Could not place {name} at {reference_position}.", response)

            for key, value in response.items():
                if isinstance(value, dict):
                    if 1 in value.keys():
                        response[key] = []
                        for sub_key, sub_value in value.items():
                            response[key].append(sub_value)

                    # map direction to cardinal direction
            if 'direction' in response.keys():
                response['direction'] = response['direction'] / 2

            try:
                object = metaclass(prototype=name, **response)
            except Exception as e:
                raise Exception(f"Could not create {name} object from response: {response}", e)

            return object
        except Exception as e:
            raise e #Exception(f"Could not place {entity} at {reference_position}.", e)
