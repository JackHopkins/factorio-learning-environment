import os
import sys
import time
from typing import List, Tuple, Dict, Any, Union

from slpp import slpp as lua, ParseError
from timeit import default_timer as timer

from controllers.__controller import Controller
from factorio_entities import Position, Entity
from factorio_rcon_utils import _lua2python, _load_action


class Init(Controller):

    def __init__(self, lua_script_manager: 'FactorioLuaScriptManager', game_state: 'FactorioInstance', *args, **kwargs):
        super().__init__(lua_script_manager, game_state)
        self.load()

    def load(self):
        self.lua_script_manager.load_init_into_game(self.name)