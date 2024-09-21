import math

from controllers._action import Action
from factorio_instance import PLAYER


class NearestBuildable(Action):

    def __init__(self, lua_script_manager, game_state):
        super().__init__(lua_script_manager, game_state)
        #self.connection = connection
        self.game_state = game_state

    def __call__(self, type: str = 'coal',
                 #relative: bool = False,
                 **kwargs
                 ):
        if not isinstance(type, str):
            raise Exception("'nearest_buildable' requires the name of the desired entity as its argument")

        response, time_elapsed = self.execute(PLAYER, type.replace("_", "-"))

        if isinstance(response, str):
            raise Exception(f"No {type} found on the map")

        if not self.game_state.last_observed_player_location:
            self.game_state.last_observed_player_location = self.game_state.player_location

        #if relative:
        #    return (-math.floor(response['x']) + self.game_state.last_observed_player_location[0],
        #           -math.floor(response['y']) + self.game_state.last_observed_player_location[1])
        else:
            return (math.floor(response['x']), math.floor(response['y']))
