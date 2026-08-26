from typing import Union

from fle.env.entities import Position, ResourcePatch
from fle.env.game_types import Prototype, Resource
from fle.env.tools import Tool


class Nearest(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(
        self,
        type: Union[Prototype, Resource],
        # relative: bool = False,
        # **kwargs
    ) -> Position:
        """
        Find the nearest entity or resource to your position.
        :param type: Entity or resource type to find
        :return: Position of nearest entity or resource
        """
        name, metaclass = self._normalize_type(type)
        try:
            response, _ = self.execute(self.player_index, name)
        except Exception as exc:
            raise RuntimeError(f"nearest({name}) failed: {exc}") from exc

        if response is None or response == {}:
            if metaclass == ResourcePatch:
                raise LookupError(
                    f"No {name} found within 500 tiles. Move around to explore more."
                )
            raise LookupError(f"No {name} found within 500 tiles")

        return Position(x=response["x"], y=response["y"])

    @staticmethod
    def _normalize_type(value):
        if isinstance(value, Prototype):
            return value.value
        if (
            isinstance(value, tuple)
            and len(value) == 2
            and isinstance(value[0], str)
            and value[1] == ResourcePatch
        ):
            return value
        raise ValueError(
            "nearest() requires one specific enum member, such as "
            "Resource.Coal, Resource.IronOre, or Prototype.StoneFurnace; "
            "bare Resource/Prototype classes and strings are invalid"
        )
