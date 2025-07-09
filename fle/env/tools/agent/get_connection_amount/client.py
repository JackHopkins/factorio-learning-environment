from typing import Union

from fle.env.entities import Entity, Position, EntityGroup
from fle.env.game_types import Prototype
from fle.env.tools.agent.connect_entities.client import ConnectEntities
from fle.env.tools import Tool


class GetConnectionAmount(Tool):
    def __init__(self, connection, game_state):
        self.game_state = game_state
        super().__init__(connection, game_state)
        self.connect_entities = ConnectEntities(connection, game_state)

    def __call__(
        self,
        source: Union[Position, Entity, EntityGroup],
        target: Union[Position, Entity, EntityGroup],
        connection_type: Prototype = Prototype.Pipe,
    ) -> int:
        """
        Calculate the number of connecting entities needed to connect two entities, positions or groups.
        :param source: First entity or position
        :param target: Second entity or position
        :param connection_type: a Pipe, TransportBelt or ElectricPole
        :return: A integer representing how many entities are required to connect the source and target entities
        """

        connect_output = self.connect_entities(
            source, target, connection_type, dry_run=True
        )
        return connect_output["number_of_entities_required"]
