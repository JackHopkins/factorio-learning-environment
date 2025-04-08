from typing import Tuple, Union, Optional

from entities import Position, Entity, BeltGroup, PipeGroup, EntityGroup, UndergroundBelt, Direction, ElectricityGroup
from game_types import Prototype
from tools.tool import Tool


class PickupEntity(Tool):

    def __init__(self, *args):
        super().__init__(*args)

    def __call__(self,
                 entity: Union[Entity, Prototype, EntityGroup],
                 position: Optional[Position] = None) -> bool:
        """
        Pick up an entity if it exists on the world at a given position.
        :param entity: Entity prototype to pickup, e.g Prototype.IronPlate
        :param position: Position to pickup entity
        :return: True if the entity was picked up successfully, False otherwise.
        """
        if not isinstance(entity, (Prototype, Entity, EntityGroup)):
            raise ValueError("The first argument must be an Entity or Prototype object")
        if isinstance(entity, Entity) and isinstance(position, Position):
            raise ValueError("If the first argument is an Entity object, the second argument must be None")
        if position is not None and not isinstance(position, Position):
            raise ValueError("The second argument must be a Position object")

        if isinstance(entity, Prototype):
            name, _ = entity.value
        else:
            name = entity.name
            if isinstance(entity, BeltGroup):
                belts = entity.belts
                for belt in belts:
                    resp = self.__call__(belt)
                    if not resp: return False
                return True
            elif isinstance(entity, PipeGroup):
                pipes = entity.pipes
                for pipe in pipes:
                    resp = self.__call__(pipe)
                    if not resp: return False
                return True
            
            elif isinstance(entity, ElectricityGroup):
                poles = entity.poles
                for pole in poles:
                    resp = self.__call__(pole)
                    if not resp: return False
                return True

        if position:
            x, y = position.x, position.y
            response, elapsed = self.execute(self.player_index, x, y, name)
        elif isinstance(entity, UndergroundBelt):
            x, y = entity.position.x, entity.position.y
            response, elapsed = self.execute(self.player_index, x, y, name)
            if response != 1 and response != {}:
                raise Exception(f"Could not pickup: {self.get_error_message(response)}")

            x, y = entity.output_position.x, entity.output_position.y
            response, elapsed = self.execute(self.player_index, x, y, name)
            if response != 1 and response != {}:
                raise Exception(f"Could not pickup: {self.get_error_message(response)}")

        elif isinstance(entity, Entity):
            x, y = entity.position.x, entity.position.y
            response, elapsed = self.execute(self.player_index, x, y, name)
        else:
            raise ValueError("The second argument must be a Position object")

        if response != 1 and response != {}:
            raise Exception(f"Could not pickup: {self.get_error_message(response)}")
        return True
