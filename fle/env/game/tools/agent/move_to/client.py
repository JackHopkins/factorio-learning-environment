import math
from time import sleep

from fle.env.game.entities import Position
from fle.env.game.instance import NONE
from fle.env.game.game_types import Prototype
from fle.env.game.tools.admin.get_path.client import GetPath
from fle.env.game.tools.admin.request_path.client import RequestPath
from fle.env.game.tools import Tool
from fle.env.lua_manager import LuaScriptManager


class MoveTo(Tool):
    def __init__(self, connection: LuaScriptManager, game_state):
        super().__init__(connection, game_state)
        # self.observe = ObserveAll(connection, game_state)
        self.request_path = RequestPath(connection, game_state)
        self.get_path = GetPath(connection, game_state)

    def __call__(
        self, position: Position, laying: Prototype = None, leading: Prototype = None
    ) -> Position:
        """
        Move to a position.
        :param position: Position to move to.
        :return: Your final position
        """

        X_OFFSET, Y_OFFSET = 0, 0  # 0.5, 0

        x, y = (
            math.floor(position.x * 4) / 4 + X_OFFSET,
            math.floor(position.y * 4) / 4 + Y_OFFSET,
        )
        nposition = Position(x=x, y=y)

        path_handle = self.request_path(
            start=Position(
                x=self.namespace.player_location.x, y=self.namespace.player_location.y
            ),
            finish=nposition,
            allow_paths_through_own_entities=True,
            resolution=-1,
        )
        sleep(0.05)  # Let the pathing complete in the game.
        try:
            if laying is not None:
                entity_name = laying.value[0]
                response, execution_time = self.execute(
                    self.player_index, path_handle, entity_name, 1
                )
            elif leading:
                entity_name = leading.value[0]
                response, execution_time = self.execute(
                    self.player_index, path_handle, entity_name, 0
                )
            else:
                response, execution_time = self.execute(
                    self.player_index, path_handle, NONE, NONE
                )

            if isinstance(response, int) and response == 0:
                raise Exception("Could not move.")

            if response == "trailing" or response == "leading":
                raise Exception("Could not lay entity, perhaps a typo?")

            if response and isinstance(response, dict):
                self.namespace.player_location = Position(
                    x=response["x"], y=response["y"]
                )

            # If `fast` is turned off - we need to long poll the game state to ensure the player has moved
            if not self.namespace.instance.fast:
                remaining_steps = self.factorio_client.run_rcon_print(
                    f"global.actions.get_walking_queue_length({self.player_index})"
                )
                while remaining_steps != "0":
                    sleep(0.5)
                    remaining_steps = self.factorio_client.run_rcon_print(
                        f"global.actions.get_walking_queue_length({self.player_index})"
                    )
                self.namespace.player_location = Position(x=position.x, y=position.y)

            return Position(x=response["x"], y=response["y"])  # , execution_time
        except Exception as e:
            raise Exception(f"Cannot move. {e}")
