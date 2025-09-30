from fle.env.tools import Tool


class GetElapsedTicks(Tool):
    """Admin tool to get the current elapsed ticks from the game."""

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self):
        """
        Get the current elapsed ticks from the game.

        Returns:
            int: The current elapsed ticks
        """
        response, _ = self.execute()
        return response
