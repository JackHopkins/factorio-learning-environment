from controllers.__action import Action
from typing import Tuple, Union, Optional

from factorio_entities import Position, Entity, BeltGroup, PipeGroup, EntityGroup
from factorio_instance import PLAYER
from factorio_types import Prototype


class PickupEntity(Action):

    def __init__(self, *args):
        super().__init__(*args)

    def __call__(self,
                 entity: Union[Entity, Prototype, EntityGroup],
                 position: Optional[Position] = None) -> bool:
        """
        The agent picks up an given entity prototype e at position (x, y) if it exists on the world.
        :param entity: Entity prototype to pickup, e.g Prototype.IronPlate
        :param position: Position to pickup entity
        :example: pickup_entity(Prototype.IronPlate, stone_furnace.position)
        :return:
        """
        if not isinstance(entity, (Prototype, Entity, EntityGroup)):
            raise ValueError("The first argument must be an Entity or Prototype object")
        if isinstance(entity, Entity) and isinstance(position, Position):
            raise ValueError("If the first argument is an Entity object, the second argument must be None")
        if position and not isinstance(position, Position):
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

        if position:
            x, y = position.x, position.y
        elif isinstance(entity, Entity):
            x, y = entity.position.x, entity.position.y
        else:
            raise ValueError("The second argument must be a Position object")

        response, elapsed = self.execute(PLAYER, x, y, name)
        if response != 1 and response != {}:
            raise Exception(f"Could not pickup: {self.get_error_message(response)}")
        return True
