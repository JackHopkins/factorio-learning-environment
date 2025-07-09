import math
from time import sleep

from fle.env.entities import Position
from fle.env.instance import NONE
from fle.env.game_types import Prototype
from fle.env.tools.admin.get_path.client import GetPath
from fle.env.tools.admin.request_path.client import RequestPath
from fle.env.tools import Tool
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
                x=self.game_state.player_location.x, y=self.game_state.player_location.y
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
                self.game_state.player_location = Position(
                    x=response["x"], y=response["y"]
                )

            # If `fast` is turned off - we need to long poll the game state to ensure the player has moved
            if not self.game_state.instance.fast:
                remaining_steps = self.connection.rcon_client.send_command(
                    f"/silent-command rcon.print(global.actions.get_walking_queue_length({self.player_index}))"
                )
                while remaining_steps != "0":
                    sleep(0.5)
                    remaining_steps = self.connection.rcon_client.send_command(
                        f"/silent-command rcon.print(global.actions.get_walking_queue_length({self.player_index}))"
                    )
                self.game_state.player_location = Position(x=position.x, y=position.y)

            return Position(x=response["x"], y=response["y"])  # , execution_time
        except Exception as e:
            raise Exception(f"Cannot move. {e}")
