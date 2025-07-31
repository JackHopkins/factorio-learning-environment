from typing import Union

from fle.env.entities import Position, Entity
from fle.env.instance import NONE
from fle.env.game_types import Prototype
from fle.env.tools import Tool


class ExtractItem(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(
        self,
        entity: Prototype,
        source: Union[Position, Entity],
        quantity=5,
        tick: int = None,
    ) -> int:
        """
        Extract an item from an entity's inventory at position (x, y) if it exists on the world.
        :param entity: Entity prototype to extract, e.g Prototype.IronPlate
        :param source: Entity or position to extract from
        :param quantity: Quantity to extract
        :param tick: Game tick to execute this command at (for batch mode)
        :example extract_item(Prototype.IronPlate, stone_furnace.position, 5)
        :example extract_item(Prototype.CopperWire, stone_furnace, 5)
        :return The number of items extracted.
        """
        source_name = NONE
        if isinstance(source, Position):
            x, y = self.get_position(source)

        elif isinstance(source, Entity):
            x, y = self.get_position(source.position)
            source_name = source.name

        name, _ = entity.value

        response, elapsed = self.execute_or_batch(
            tick, self.player_index, name, quantity, x, y, source_name
        )

        # Check if we're in batch mode - if so, return early without processing response
        if isinstance(response, dict) and response.get("batched"):
            # In batch mode, return expected quantity as placeholder
            return quantity

        if isinstance(response, str):
            msg = self.get_error_message(response)
            if source_name != NONE:
                raise Exception(
                    f"Could not extract {name} from {source_name} at ({x}, {y}): {msg}"
                )
            else:
                raise Exception(f"Could not extract {name} at ({x}, {y}): {msg}")

        if not response or response < 1:
            raise Exception("Could not extract.")

        return response
