
from controllers.__action import Action
from typing import Tuple, List, Union

from controllers.connect_entities import ConnectEntities
from factorio_entities import Entity, Position, EntityGroup
from factorio_types import Prototype


class GetConnectionAmount(Action):

    def __init__(self, connection, game_state):
        self.game_state = game_state
        super().__init__(connection, game_state)
        self.connect_entities = ConnectEntities(connection, game_state)


    def __call__(self,
                 source: Union[Position, Entity, EntityGroup],
                 target: Union[Position, Entity, EntityGroup],
                 connection_type: Prototype = Prototype.Pipe
                 ) -> int:
        """
        Connect two entities or positions.
        :param source: First entity or position
        :param target: Second entity or position
        :param connection_type: a Pipe, TransportBelt or ElectricPole
        :example connect_entities(source=boiler, target=generator, connection_type=Prototype.Pipe)
        :example connect_entities(source=miner, target=stone_furnace, connection_type=Prototype.TransportBelt)
        :return: A integer representing how many entities are required to connect the source and target entities
        """

        connect_output = self.connect_entities(source, target, connection_type, dry_run=True)
        return connect_output["number_of_entities_required"]
        