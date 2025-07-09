from fle.env import entities as ent
from fle.env.game_types import Prototype
from fle.env.tools import Tool


class CanPlaceEntity(Tool):
    def __init__(self, *args):
        super().__init__(*args)

    def __call__(
        self,
        entity: Prototype,
        direction: ent.Direction = ent.Direction.UP,
        position: ent.Position = ent.Position(x=0, y=0),
    ) -> bool:
        """
        Tests to see if an entity can be placed at a given position
        :param entity: Entity to place from inventory
        :param direction: Cardinal direction to place entity
        :param position: Position to place entity
        :return: True if entity can be placed at position, else False
        """

        assert isinstance(entity, Prototype)
        assert isinstance(direction, ent.Direction)

        # If position is a tuple, cast it to a Position object:
        if isinstance(position, tuple):
            position = ent.Position(x=position[0], y=position[1])

        assert isinstance(position, ent.Position)

        x, y = self.get_position(position)
        name, metaclass = entity.value

        response, elapsed = self.execute(
            self.player_index, name, direction.value + 1, x, y
        )

        if not isinstance(response, dict):
            if isinstance(response, bool):
                return response
            if isinstance(response, str):
                return False
        return True
