from typing import Tuple

from entities import Inventory, Entity, Position
from tools.tool import Tool


class InspectInventory(Tool):

    def __init__(self, *args):
        super().__init__(*args)

    def __call__(self, entity=None) -> Inventory:
        """
        Inspects the inventory of the given entity. If no entity is given, inspect your own inventory.
        :param entity: Entity to inspect
        :return: Inventory of the given entity
        """

        if entity:
            if isinstance(entity, Entity):
                x, y = self.get_position(entity.position)
            elif isinstance(entity, Position):
                x, y = entity.x, entity.y
            else:
                raise ValueError(f"The first argument must be an Entity or Position object, you passed in a {type(entity)} object.")
        else:
            x, y = 0, 0

        response, execution_time = self.execute(self.player_index, entity == None, x, y, entity.name if entity else "")

        if not isinstance(response, dict):
            if entity:
                raise Exception(f"Could not inspect inventory of {entity}.", response)
            else:
                #raise Exception("Could not inspect None inventory.", response)
                return Inventory()

        return Inventory(**response)


