import re
from typing import Tuple, Union

from fle.env.entities import Position, Entity
from fle.env.namespace import FactorioNamespace
from fle.env.tools.controller import Controller

_LUA_SOURCE_PREFIX = re.compile(r"^(?:\[string [^\r\n]*\]|[^\r\n]*\.lua):\d+:\s*")


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

    def get_error_message(self, response: str) -> str:
        """Remove the Lua source prefix without truncating the error itself."""
        if not isinstance(response, str):
            return str(response)

        # Factorio errors normally start with a Lua source and line number, for
        # example: [string "..."]:148: "No item in inventory: ...".  Splitting
        # on every colon loses useful parts of the actual error message.
        prefix = _LUA_SOURCE_PREFIX.match(response)
        message = response[prefix.end() :] if prefix else response
        message = message.strip()

        if len(message) >= 2 and message[0] == message[-1] and message[0] in {'"', "'"}:
            message = message[1:-1]

        return message.replace(r"\'", "'").replace(r"\"", '"')

    def load(self):
        # self.lua_script_manager.load_action_into_game(self.name)
        self.lua_script_manager.load_tool_into_game(self.name)
        # script = _load_action(self.name)
        # if not script:
        #     raise Exception(f"Could not load {self.name}")
        # self.connection.send_command(f'{COMMAND} '+script)
