from fle.env.entities import Position
from fle.env.tools import Tool


class LoadBlueprint(Tool):
    def __init__(self, *args):
        super().__init__(*args)

    def __call__(self, blueprint: str, position: Position) -> bool:
        """
        Loads a blueprint into the game.
        :param blueprint: Name of the blueprint to load
        :return: True if successful, False otherwise
        """

        assert isinstance(blueprint, str)

        result, _ = self.execute(self.player_index, blueprint, position.x, position.y)

        if result == 0:
            return True
        return False
