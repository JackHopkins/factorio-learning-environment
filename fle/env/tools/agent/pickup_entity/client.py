from typing import Union, Optional

from fle.env import entities as ent
from fle.env.game_types import Prototype
from fle.env.tools import Tool


class PickupEntity(Tool):
    def __init__(self, *args):
        super().__init__(*args)

    def __call__(
        self,
        entity: Union[ent.Entity, Prototype, ent.EntityGroup],
        position: Optional[ent.Position] = None,
    ) -> bool:
        """
        Pick up an entity if it exists on the world at a given position.
        :param entity: Entity prototype to pickup, e.g Prototype.IronPlate
        :param position: Position to pickup entity
        :return: True if the entity was picked up successfully, False otherwise.
        """
        if not isinstance(entity, (Prototype, ent.Entity, ent.EntityGroup)):
            raise ValueError("The first argument must be an Entity or Prototype object")
        if isinstance(entity, ent.Entity) and isinstance(position, ent.Position):
            raise ValueError(
                "If the first argument is an Entity object, the second argument must be None"
            )
        if position is not None and not isinstance(position, ent.Position):
            raise ValueError("The second argument must be a Position object")

        if isinstance(entity, Prototype):
            name, _ = entity.value
        else:
            name = entity.name
            if isinstance(entity, ent.BeltGroup):
                belts = entity.belts
                for belt in belts:
                    resp = self.__call__(belt)
                    if not resp:
                        return False
                return True
            elif isinstance(entity, ent.PipeGroup):
                pipes = entity.pipes
                for pipe in pipes:
                    resp = self.__call__(pipe)
                    if not resp:
                        return False
                return True

            elif isinstance(entity, ent.ElectricityGroup):
                poles = entity.poles
                for pole in poles:
                    resp = self.__call__(pole)
                    if not resp:
                        return False
                return True

        if position:
            x, y = position.x, position.y
            response, elapsed = self.execute(self.player_index, x, y, name)
        elif isinstance(entity, ent.UndergroundBelt):
            x, y = entity.position.x, entity.position.y
            response, elapsed = self.execute(self.player_index, x, y, name)
            if response != 1 and response != {}:
                raise Exception(f"Could not pickup: {self.get_error_message(response)}")

            x, y = entity.output_position.x, entity.output_position.y
            response, elapsed = self.execute(self.player_index, x, y, name)
            if response != 1 and response != {}:
                raise Exception(f"Could not pickup: {self.get_error_message(response)}")

        elif isinstance(entity, ent.Entity):
            x, y = entity.position.x, entity.position.y
            response, elapsed = self.execute(self.player_index, x, y, name)
        else:
            raise ValueError("The second argument must be a Position object")

        if response != 1 and response != {}:
            raise Exception(f"Could not pickup: {self.get_error_message(response)}")
        return True
