from typing import Tuple, Union

from fle.env.entities import Position, Entity
from fle.env.namespace import FactorioNamespace
from fle.env.tools.controller import Controller


class Tool(Controller):
    def __init__(
        self,
        lua_script_manager: "FactorioLuaScriptManager",  # noqa
        game_state: "FactorioNamespace",
        *args,
        **kwargs,
    ):
        super().__init__(lua_script_manager, game_state)
        self.load()

    def get_position(self, position_or_entity: Union[Tuple, Position, Entity]):
        if isinstance(position_or_entity, tuple):
            x, y = position_or_entity
        elif isinstance(position_or_entity, Entity):
            x = position_or_entity.position.x
            y = position_or_entity.position.y
        else:
            x = position_or_entity.x
            y = position_or_entity.y

        return x, y

    def get_error_message(self, response):
        try:
            msg = (
                response.split(":")[-1]
                .replace('"', "")
                .strip()
                .replace("\\'", "")
                .replace("'", "")
            )
            return msg
        except Exception:
            return response

    def load(self):
        # self.lua_script_manager.load_action_into_game(self.name)
        self.lua_script_manager.load_tool_into_game(self.name)
        # script = _load_action(self.name)
        # if not script:
        #     raise Exception(f"Could not load {self.name}")
        # self.connection.send_command(f'{COMMAND} '+script)
