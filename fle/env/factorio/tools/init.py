from fle.env.factorio.tools.controller import Controller
from fle.env.instance import FactorioInstance, FactorioServer


class Init(Controller):
    def __init__(
        self,
        factorio_server: "FactorioServer",
        game_state: "FactorioInstance",
        *args,
        **kwargs,
    ):
        super().__init__(factorio_server, game_state)
        self.load()

    def load(self):
        self.factorio_server.load_init_into_game(self.name)
