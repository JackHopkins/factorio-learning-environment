from typing import Tuple

from controllers.__action import Action
from factorio_entities import Inventory, Entity, Position
from factorio_instance import PLAYER


class InspectInventory(Action):

    def __init__(self, *args):
        super().__init__(*args)

    def __call__(self, entity=None) -> Inventory:
        """
        Inspects the inventory of the given entity. If no entity is given, this inspects your own inventory.
        :param entity: Entity to inspect
        :example: iron_chest_inventory = inspect_inventory(nearest(Prototype.IronChest))
        :return: Inventory of the given entity
        """



        if entity:
            if isinstance(entity, Entity):
                x, y = self.get_position(entity.position)
            elif isinstance(entity, Position):
                x, y = entity.x, entity.y
            else:
                raise ValueError("The first argument must be an Entity or Position object")
        else:
            x, y = 0, 0
        response, execution_time = self.execute(PLAYER, entity == None, x, y)

        if not isinstance(response, dict):
            if entity:
                raise Exception(f"Could not inspect inventory of {entity}.", response)
            else:
                #raise Exception("Could not inspect None inventory.", response)
                return Inventory()

        return Inventory(**response)


