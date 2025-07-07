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
        try:
            if not isinstance(type, tuple) and isinstance(type.value, tuple):
                type = type.value

            name, metaclass = type

            if not isinstance(name, str):
                raise Exception(
                    "'Nearest' must be called with an entity name as the first argument."
                )

            response, time_elapsed = self.execute(self.player_index, name)

            if response is None or response == {}:
                if metaclass == ResourcePatch:
                    raise Exception(
                        f"No {type} found on the map within 500 tiles of the player. Move around to explore the map more."
                    )
                else:
                    raise Exception(f"No {type} found within 500 tiles of the player")

            # if not self.game_state.last_observed_player_location:
            #    self.game_state.last_observed_player_location = self.game_state.player_location

            # if relative:
            #    x = -response['x'] + self.game_state.last_observed_player_location[0]
            #    y = -response['y'] + self.game_state.last_observed_player_location[1]
            # else:
            x = response["x"]
            y = response["y"]

            position = Position(x=x, y=y)

            return position
        except TypeError:
            raise Exception(f"Could not find nearest {type[0]} on the surface")
        except Exception as e:
            raise Exception(f"Could not find nearest {type[0]}", e)
