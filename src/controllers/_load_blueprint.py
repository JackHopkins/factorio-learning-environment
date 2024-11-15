from controllers.__action import Action
from factorio_entities import Position
from factorio_instance import PLAYER


class LoadBlueprint(Action):

    def __init__(self, *args):
        super().__init__(*args)

    def __call__(self, blueprint: str, position: Position) -> bool:
        """
        Loads a blueprint into the game.
        :param blueprint: Name of the blueprint to load
        :return: True if successful, False otherwise
        """

        assert isinstance(blueprint, str)

        result, _ = self.execute(PLAYER, blueprint, position.x, position.y)

        if result == 0:
            return True
        return False