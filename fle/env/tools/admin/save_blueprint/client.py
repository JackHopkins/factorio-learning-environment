from typing import Tuple

from fle.env.entities import Position
from fle.env.tools import Tool


class SaveBlueprint(Tool):
    def __init__(self, *args):
        super().__init__(*args)

    def __call__(self) -> Tuple[str, Position]:
        """
        Saves the current player entities on the map into a blueprint string
        :return: Blueprint and offset to blueprint from the origin.
        """
        result, _ = self.execute(self.player_index)

        blueprint = result["blueprint"]
        offset = Position(x=result["center_x"], y=result["center_y"])
        return blueprint, offset
