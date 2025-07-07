from typing import List, Union

from fle.env import Inventory, Entity, Position
from fle.env.tools import Tool


class InspectInventory(Tool):
    def __init__(self, *args):
        super().__init__(*args)

    def __call__(
        self, entity=None, all_players: bool = False
    ) -> Union[Inventory, List[Inventory]]:
        """
        Inspects the inventory of the given entity. If no entity is given, inspect your own inventory.
        If all_players is True, returns a list of inventories for all players.
        :param entity: Entity to inspect
        :param all_players: If True, returns inventories for all players
        :return: Inventory of the given entity or list of inventories for all players
        """

        if all_players:
            response, execution_time = self.execute(
                self.player_index, True, 0, 0, "", True
            )
            if not isinstance(response, list):
                raise Exception("Could not get inventories for all players", response)
            return [Inventory(**inv) for inv in response]

        if entity:
            if isinstance(entity, Entity):
                x, y = self.get_position(entity.position)
            elif isinstance(entity, Position):
                x, y = entity.x, entity.y
            else:
                raise ValueError(
                    f"The first argument must be an Entity or Position object, you passed in a {type(entity)} object."
                )
        else:
            x, y = 0, 0

        response, execution_time = self.execute(
            self.player_index, entity is None, x, y, entity.name if entity else ""
        )

        if not isinstance(response, dict):
            if entity:
                raise Exception(f"Could not inspect inventory of {entity}.", response)
            else:
                # raise Exception("Could not inspect None inventory.", response)
                return Inventory()

        return Inventory(**response)
