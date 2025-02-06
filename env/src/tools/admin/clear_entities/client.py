import math

from instance import PLAYER
from tools.init import Init


class ClearEntities(Init):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self, *args, **kwargs):
        response, time_elapsed = self.execute(PLAYER)
        return response
