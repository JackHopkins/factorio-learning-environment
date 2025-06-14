from env.src.tools.controller import Controller


class Init(Controller):
    def __init__(
        self,
        lua_script_manager: "FactorioLuaScriptManager",
        game_state: "FactorioInstance",
        *args,
        **kwargs,
    ):
        super().__init__(lua_script_manager, game_state)
        self.load()

    def load(self):
        self.lua_script_manager.load_init_into_game(self.name)
