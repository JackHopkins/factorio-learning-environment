from time import sleep

from fle.env.game_types import Prototype
from fle.env.tools.agent.inspect_inventory.client import InspectInventory
from fle.env.tools import Tool


class CraftItem(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.inspect_inventory = InspectInventory(connection, game_state)

    def __call__(self, entity: Prototype, quantity: int = 1) -> int:
        """
        Craft an item from a Prototype if the ingredients exist in your inventory.
        :param entity: Entity to craft
        :param quantity: Quantity to craft
        :return: Number of items crafted
        """

        if hasattr(entity, "value"):
            name, _ = entity.value
        else:
            name = entity

        count_in_inventory = 0
        if not self.game_state.instance.fast:
            count_in_inventory = self.inspect_inventory()[entity]

        success, elapsed = self.execute(self.player_index, name, quantity)
        if success != {} and isinstance(success, str):
            if success is None:
                raise Exception(
                    f"Could not craft a {name} - Ingredients cannot be crafted by hand."
                )
            else:
                result = self.get_error_message(success)
                raise Exception(result)

        if not self.game_state.instance.fast:
            sleep(0.5)
            attempt = 0
            max_attempts = 10
            while (
                self.inspect_inventory()[entity] - count_in_inventory < quantity
                and attempt < max_attempts
            ):
                sleep(0.5)
                attempt += 1

        return success
