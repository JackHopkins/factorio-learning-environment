from instance import PLAYER
from tools.tool import Tool


class GetProductionStats(Tool):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.name = "production_stats"
        self.game_state = game_state

    def __call__(self, *args, **kwargs):
        response, execution_time = self.execute(PLAYER, *args, **kwargs)
        return response
