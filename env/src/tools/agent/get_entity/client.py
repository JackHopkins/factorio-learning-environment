from time import sleep
from typing import Tuple

from env.src.entities import Position, Entity

from env.src.game_types import Prototype
from env.src.tools.agent.get_entities.client import GetEntities
from env.src.tools.tool import Tool


class GetEntity(Tool):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.get_entities = GetEntities(connection, game_state)

    def __call__(self, entity: Prototype, position: Position) -> Entity:
        """
        Retrieve a given entity object at position (x, y) if it exists on the world.
        :param entity: Entity prototype to get, e.g Prototype.StoneFurnace
        :param position: Position where to look
        :return: Entity object
        """
        assert isinstance(entity, Prototype)
        assert isinstance(position, Position)
        if entity == Prototype.BeltGroup:
            entities = self.get_entities({Prototype.TransportBelt, Prototype.FastTransportBelt, Prototype.ExpressTransportBelt}, position=position)
            return entities[0] if len(entities) > 0 else None
        elif entity == Prototype.PipeGroup:
            entities = self.get_entities({Prototype.Pipe}, position=position)
            return entities[0] if len(entities) > 0 else None
        elif entity == Prototype.ElectricityGroup:
            entities = self.get_entities({Prototype.SmallElectricPole, Prototype.MediumElectricPole, Prototype.BigElectricPole}, position=position)
            return entities[0] if len(entities) > 0 else None
        else:
            try:
                x, y = self.get_position(position)
                name, metaclass = entity.value
                while isinstance(metaclass, tuple):
                    metaclass = metaclass[1]

                sleep(0.05)
                response, elapsed = self.execute(self.player_index, name, x, y)

                if response is None or response == {} or isinstance(response, str):
                    msg = response.split(':')[-1]
                    raise Exception(msg)

                cleaned_response = self.clean_response(response)
                try:
                    object = metaclass(prototype=entity.name, **cleaned_response)
                except Exception as e:
                    raise Exception(f"Could not create {name} object from response (get entity): {cleaned_response}", e)

                return object
            except Exception as e:
                raise Exception(f"Could not get {entity} at position {position}", e)

