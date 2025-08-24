from fle.env.tools import Tool


class CreateAgentCharacters(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self, num_agents: int) -> bool:
        """
        Creates an agent character
        """
        response, elapsed = self.execute(num_agents)
        return True
