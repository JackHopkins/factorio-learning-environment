import math

from controllers.__action import Action
from factorio_instance import PLAYER


class RegenerateResources(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self, *args, **kwargs):
        response, time_elapsed = self.execute(PLAYER)
        return response
