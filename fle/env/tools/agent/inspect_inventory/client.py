from typing import List, Union

from fle.env import Inventory, Entity, Position
from fle.env.tools import Tool
from fle.env.instance import NONE


class InspectInventory(Tool):
    def __init__(self, *args):
        super().__init__(*args)

    def __call__(
        self, entity=None, all_players: bool = False, tick: int = None
    ) -> Union[Inventory, List[Inventory]]:
        """
        Inspects the inventory of the given entity. If no entity is given, inspect your own inventory.
        If all_players is True, returns a list of inventories for all players.
        :param entity: Entity to inspect
        :param all_players: If True, returns inventories for all players
        :param tick: Game tick to execute this command at (for batch mode)
        :return: Inventory of the given entity or list of inventories for all players
        """

        if all_players:
            response, execution_time = self.execute_or_batch(
                tick, self.player_index, True, NONE, NONE, NONE, True
            )

            # Check if we're in batch mode - if so, return early without processing response
            if isinstance(response, dict) and response.get("batched"):
                # In batch mode, return empty inventory list as placeholder
                return []

            # Non-batch mode - process the response normally
            if not isinstance(response, list):
                raise Exception("Could not get inventories for all players", response)
            return [Inventory(**inv) for inv in response]

        if entity is None:
            response, execution_time = self.execute_or_batch(
                tick, self.player_index, True, NONE, NONE, NONE, False
            )

            # Check if we're in batch mode - if so, return early without processing response
            if isinstance(response, dict) and response.get("batched"):
                # In batch mode, return empty inventory as placeholder
                return Inventory(items=[])

        else:
            if isinstance(entity, int) or isinstance(entity, str):
                response, execution_time = self.execute_or_batch(
                    tick, self.player_index, False, NONE, entity, NONE, False
                )
            elif isinstance(entity, Entity):
                x, y = self.get_position(entity.position)
                response, execution_time = self.execute_or_batch(
                    tick, self.player_index, False, x, y, entity.name, False
                )
            elif isinstance(entity, Position):
                x, y = entity.x, entity.y
                response, execution_time = self.execute_or_batch(
                    tick, self.player_index, False, x, y, "", False
                )
            else:
                raise ValueError(f"Invalid entity type: {type(entity)}")

            # Check if we're in batch mode - if so, return early without processing response
            if isinstance(response, dict) and response.get("batched"):
                # In batch mode, return empty inventory as placeholder
                return Inventory(items=[])

        if not isinstance(response, dict):
            if entity:
                raise Exception(f"Could not inspect inventory of {entity}.", response)
            else:
                # raise Exception("Could not inspect None inventory.", response)
                return Inventory()

        return Inventory(**response)
