from fle.env.game.tools.controller import Controller
from fle.env.game.instance import FactorioInstance, FactorioClient


class Init(Controller):
    def __init__(
        self,
        factorio_server: "FactorioClient",
        game_state: "FactorioInstance",
        *args,
        **kwargs,
    ):
        super().__init__(factorio_server, game_state)
        self.load()

    def load(self):
        self.factorio_server.load_init_into_game(self.name)
