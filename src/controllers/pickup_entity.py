from controllers._action import Action
from typing import Tuple, Union

from factorio_entities import Position, Entity
from factorio_instance import PLAYER
from factorio_types import Prototype


class PickupEntity(Action):

    def __init__(self, *args):
        super().__init__(*args)

    def __call__(self, entity: Entity,
                 position: Position,
                 #relative=False
                 ) -> bool:
        """
        The agent picks up an given entity prototype e at position (x, y) if it exists on the world.
        :param entity: Entity prototype to pickup, e.g Prototype.IronPlate
        :param position: Position to pickup entity
        :example: pickup_entity(Prototype.IronPlate, stone_furnace.position)
        :return:
        """
        #x, y = self.get_position(position)
        name, _ = entity.value
        x, y = position.x, position.y
        #if relative:
        #    x += self.game_state.last_observed_player_location[0]
        #    y += self.game_state.last_observed_player_location[1]

        response, elapsed = self.execute(PLAYER, x, y, name)
        if response != 1 and response != {}:
            raise Exception("Could not pickup, did you intend to harvest?", response)
        return True
