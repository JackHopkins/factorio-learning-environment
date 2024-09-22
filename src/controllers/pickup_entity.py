from controllers._action import Action
from typing import Tuple, Union, Optional

from factorio_entities import Position, Entity
from factorio_instance import PLAYER
from factorio_types import Prototype


class PickupEntity(Action):

    def __init__(self, *args):
        super().__init__(*args)

    def __call__(self,
                 entity: Union[Entity, Prototype],
                 position: Optional[Position] = None) -> bool:
        """
        The agent picks up an given entity prototype e at position (x, y) if it exists on the world.
        :param entity: Entity prototype to pickup, e.g Prototype.IronPlate
        :param position: Position to pickup entity
        :example: pickup_entity(Prototype.IronPlate, stone_furnace.position)
        :return:
        """
        if not isinstance(entity, Entity) and not isinstance(entity, Prototype):
            raise ValueError("The first argument must be an Entity or Prototype object")
        if isinstance(entity, Entity) and isinstance(position, Position):
            raise ValueError("If the first argument is an Entity object, the second argument must be None")
        if position and not isinstance(position, Position):
            raise ValueError("The second argument must be a Position object")

        if isinstance(entity, Prototype):
            name, _ = entity.value
        else:
            name = entity.name

        if position:
            x, y = position.x, position.y
        elif isinstance(entity, Entity):
            x, y = entity.position.x, entity.position.y
        else:
            raise ValueError("The second argument must be a Position object")

        response, elapsed = self.execute(PLAYER, x, y, name)
        if response != 1 and response != {}:
            raise Exception("Could not pickup, did you intend to harvest?", response)
        return True
