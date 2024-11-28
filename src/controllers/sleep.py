
from time import sleep

from controllers.__action import Action

class Sleep(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def load(self):
        # We don't want to send anything to the game for this action, this is purely client side.
        pass

    def __call__(self, seconds: int) -> bool:
        """
        Sleep for up to 15 seconds before continuing. Useful for waiting for actions to complete.
        :param seconds: Number of seconds to sleep.
        :return: True if sleep was successful.
        """
        sleep(min(30, seconds/(self.game_state._speed/2+0.001)))
        return True

