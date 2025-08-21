from fle.env.tools import Tool
from typing import Dict, Any
from slpp import slpp as lua
import json



class SetInventory(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self, player_index: int, inventory: Dict[str, Any]) -> bool:
        """
        Sets the inventory for an agent character
        """
        inventory_json = json.dumps(inventory)
        response, elapsed = self.execute(player_index, inventory_json)
        return True
