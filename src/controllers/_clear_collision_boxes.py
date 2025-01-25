from controllers.__action import Action

from factorio_instance import PLAYER


class ClearCollisionBoxes(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self) -> bool:
        """
        Removes all pipe insulation
        """
        response, elapsed = self.execute(PLAYER)
        return True