from fle.env.tools import Tool
import json


class Reset(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(
        self,
        inventories=None,
        reset_position=False,
        all_technologies_researched=True,
        clear_entities=True,
    ):
        """
        Reset the Factorio game state via Lua action, mirroring FactorioInstance.reset/_reset.

        Args:
                inventories (list[dict]|dict|None): Either a list indexed by agent (1-based in Lua)
                    or a dict keyed by agent index (int or str) mapping to {item_name: count}.
                reset_position (bool): If True, teleport agents to spawn offsets.
                all_technologies_researched (bool): If True, research all technologies; else reset force.
        """
        if inventories is None:
            inventories = {}

        dict_inventories = []
        for inv in inventories:
            if isinstance(inv, dict):
                dict_inventories.append(inv)
            elif hasattr(inv, "model_dump"):
                # Inventory is a pydantic extra="allow" model: item counts
                # live in __pydantic_extra__ and inv.__dict__ is {}, so the
                # previous inv.__dict__ serialization reset agents to EMPTY
                # inventories whenever a GameState was restored.
                dict_inventories.append(inv.model_dump())
            elif hasattr(inv, "items"):
                dict_inventories.append(dict(inv.items()))
            else:
                dict_inventories.append(inv.__dict__)

        # Encode to JSON string for Lua
        inventories_json = json.dumps(dict_inventories)

        response, _ = self.execute(
            inventories_json,
            reset_position,
            all_technologies_researched,
            clear_entities,
        )
        return response
