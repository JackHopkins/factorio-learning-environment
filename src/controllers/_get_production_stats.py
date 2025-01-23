from controllers.__action import Action
from factorio_instance import PLAYER

class GetProductionStats(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.name = "production_stats"
        self.game_state = game_state

    def __call__(self, *args, **kwargs):
        response, execution_time = self.execute(PLAYER, *args, **kwargs)
        return response
