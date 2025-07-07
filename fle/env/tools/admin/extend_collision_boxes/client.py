from fle.env.entities import Position
from fle.env.tools import Tool


class ExtendCollisionBoxes(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self, source_position: Position, target_position: Position) -> bool:
        """
        Add an insulative buffer of invisible objects around all pipes within the bounding box.
        This is necessary when making other pipe connections, as adjacency can inadvertently cause different
        pipe groups to merge
        """
        response, elapsed = self.execute(
            self.player_index,
            source_position.x,
            source_position.y,
            target_position.x,
            target_position.y,
        )
        return True
