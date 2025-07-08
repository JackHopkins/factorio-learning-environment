from fle.env.tools import Tool


class Reward(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.name = "score"
        self.game_state = game_state
        self.load()

    def __call__(self, *args, **kwargs):
        response, execution_time = self.execute(*args, **kwargs)
        if self.game_state.instance.initial_score:
            response["player"] -= self.game_state.instance.initial_score

        if "goal" in response:
            goal = response["goal"]
        else:
            goal = ""

        if isinstance(response, str):
            raise Exception("Could not get player score", response)

        return response["player"], goal


# if __name__ == "__main__":
#     score = Reward("connection", 0)
#     score.load()
#     pass
