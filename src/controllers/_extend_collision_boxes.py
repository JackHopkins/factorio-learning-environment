import json
import time
from time import sleep
from typing import Tuple, List

from controllers.__action import Action
from factorio_entities import Position, Entity, BoundingBox

from factorio_instance import PLAYER
from factorio_types import Prototype


class ExtendCollisionBoxes(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self, source_position: Position, target_position: Position) -> bool:
        """
        Add an insulative buffer of invisible objects around all pipes within the bounding box.
        This is necessary when making other pipe connections, as adjacency can inadvertently cause different
        pipe groups to merge
        """
        response, elapsed = self.execute(PLAYER,
                                         source_position.x,
                                         source_position.y,
                                         target_position.x,
                                         target_position.y)
        return True