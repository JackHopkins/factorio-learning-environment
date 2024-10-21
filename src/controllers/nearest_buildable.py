import math

from controllers._action import Action
from factorio_entities import Position
from factorio_instance import PLAYER
from factorio_types import Prototype


class NearestBuildable(Action):

    def __init__(self, lua_script_manager, game_state):
        super().__init__(lua_script_manager, game_state)
        #self.connection = connection
        self.game_state = game_state

    def __call__(self,
                 entity: Prototype,
                 **kwargs
                 ) -> Position:
        if not isinstance(entity, Prototype):
            raise Exception("'nearest_buildable' requires the Prototype of the desired entity as the first argument")

        response, time_elapsed = self.execute(PLAYER, entity.value[0])

        if isinstance(response, str):
            raise Exception(f"No {type} found on the map")

        # if not self.game_state.last_observed_player_location:
        #     self.game_state.last_observed_player_location = self.game_state.player_location
        #
        # else:
        # return (math.floor(response['x']), math.floor(response['y']))

        return Position(x=response['x'], y=response['y'])