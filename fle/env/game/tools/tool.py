from typing import Tuple, Union

from fle.env.game.entities import Position, Entity
from fle.env.game.namespace import FactorioNamespace
from fle.env.game.instance import FactorioClient
from fle.env.game.tools.controller import Controller


class Tool(Controller):
    def __init__(
        self,
        factorio_server: "FactorioClient",
        namespace: "FactorioNamespace",
        *args,
        **kwargs,
    ):
        super().__init__(factorio_server, namespace)
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
        self.factorio_server.load_tool_into_game(self.name)
