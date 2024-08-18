from controllers._action import Action


class Score(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.game_state = game_state

    def __call__(self, *args, **kwargs):
        response, execution_time = self.execute(*args, **kwargs)
        if self.game_state.initial_score:
            response['player'] -= self.game_state.initial_score

        if 'goal' in response:
            goal = response['goal']
        else:
            goal = ""

        return response['player'], goal


if __name__ == "__main__":
    score = Score("connection", 0)
    score.load()
    pass
