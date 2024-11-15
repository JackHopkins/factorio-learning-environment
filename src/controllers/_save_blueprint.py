from typing import Tuple

from controllers.__action import Action
from factorio_entities import Position
from factorio_instance import PLAYER


class SaveBlueprint(Action):

    def __init__(self, *args):
        super().__init__(*args)

    def __call__(self) -> Tuple[str, Position]:
        """
        Saves the current player entities on the map into a blueprint string
        :return: Blueprint and offset to blueprint from the origin.
        """
        result, _ = self.execute(PLAYER)

        blueprint = result['blueprint']
        offset = Position(x=result['center_x'], y=result['center_y'])
        return blueprint, offset
