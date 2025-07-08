from fle.env.tools import Tool


class ClearCollisionBoxes(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self) -> bool:
        """
        Removes all pipe insulation
        """
        response, elapsed = self.execute(self.player_index)
        return True
