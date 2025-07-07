from typing import Union

from fle.env.entities import Entity, Direction
from fle.env.game_types import prototype_by_name
from fle.env import DirectionInternal as DirectionA
from fle.env.tools.agent.can_place_entity.client import CanPlaceEntity
from fle.env.tools.agent.connect_entities.client import ConnectEntities
from fle.env.tools.agent.pickup_entity.client import PickupEntity
from fle.env.tools.agent.place_entity.client import PlaceObject as PlaceEntity
from fle.env.tools import Tool


class ShiftEntity(Tool):
    def __init__(self, connection, game_state):
        self.game_state = game_state
        super().__init__(connection, game_state)
        self.connect_entities = ConnectEntities(connection, game_state)
        self.can_place_entity = CanPlaceEntity(connection, game_state)
        self.place_entity = PlaceEntity(connection, game_state)
        self.pickup_entity = PickupEntity(connection, game_state)

    def __call__(
        self, entity: Entity, direction: Union[Direction, DirectionA], distance: int = 1
    ) -> Entity:
        """
        Calculate the number of connecting entities needed to connect two entities, positions or groups.
        :param source: First entity or position
        :param target: Second entity or position
        :param connection_type: a Pipe, TransportBelt or ElectricPole
        :return: A integer representing how many entities are required to connect the source and target entities
        """
        assert isinstance(entity, Entity), "First argument must be an entity object"
        assert isinstance(direction, (Direction, DirectionA)), (
            "Second argument must be a direction"
        )

        pickup_successful = self.pickup_entity(entity)

        if not pickup_successful:
            raise Exception("Could not shift entity, as the initial pickup failed")

        original_position = entity.position
        match direction:
            case Direction.UP:
                entity.position.y -= distance
            case Direction.DOWN:
                entity.position.y += distance
            case Direction.LEFT:
                entity.position.x -= distance
            case _:
                entity.position.x += distance

        prototype = prototype_by_name.get(entity.name)
        can_place_new_position = self.can_place_entity(
            prototype, Direction(entity.direction), entity.position
        )

        if not can_place_new_position:
            try:
                entity = self.place_entity(
                    prototype, entity.direction, original_position
                )
            except Exception:
                raise Exception(
                    "Uh oh, I can't put the entity back in its original position. This shouldn't happen."
                )

            raise Exception("Could not place entity in the new position")

        entity = self.place_entity(prototype, entity.direction, entity.position)

        return entity
