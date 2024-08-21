
from time import sleep

from controllers._action import Action

class Sleep(Action):

    def __init__(self, connection, game_state):
        self.game_state = game_state
        super().__init__(connection, game_state)

    def load(self):
        pass

    def __call__(self, seconds: int) -> bool:
        """
        Sleep for up to 15 seconds before continuing. Useful for waiting for actions to complete.
        :param seconds: Number of seconds to sleep.
        :return: True if sleep was successful.
        """
        sleep(min(15, seconds))
        return True

