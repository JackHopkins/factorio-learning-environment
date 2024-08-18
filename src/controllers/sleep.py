import math
from time import sleep
from typing import Optional, Tuple, List

from numpy import ndarray

from controllers._action import Action
from controllers.get_path import GetPath
from controllers.observe_all import ObserveAll
from controllers.request_path import RequestPath
from factorio_entities import Position
from factorio_instance import PLAYER, NONE
from factorio_types import Prototype
from utilities.pathfinding import get_path


class Sleep(Action):

    def __init__(self, connection, game_state):
        self.game_state = game_state
        super().__init__(connection, game_state)

    def load(self):
        pass

    def __call__(self, seconds: int) -> bool:
        """
        Sleep for up to 15 seconds before continuing. Useful for waiting for actions to complete.
        :param seconds: Number of seconds to sleep.
        :return: True if sleep was successful.
        """
        sleep(min(15, seconds))
        return True

