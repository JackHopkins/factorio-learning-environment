from fle.env.tools import Tool


class GetProductionStats(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.name = "production_stats"
        self.game_state = game_state

    def __call__(self, *args, **kwargs):
        response, execution_time = self.execute(self.player_index, *args, **kwargs)
        return response
