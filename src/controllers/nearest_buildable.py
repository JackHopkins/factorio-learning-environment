import math
from typing import Optional

from controllers.__action import Action
from factorio_entities import Position, BoundingBox
from factorio_instance import PLAYER
from factorio_types import Prototype


class NearestBuildable(Action):

    def __init__(self, lua_script_manager, game_state):
        super().__init__(lua_script_manager, game_state)
        #self.connection = connection
        self.game_state = game_state

    def __call__(self,
                 entity: Prototype,
                 bounding_box: Optional[BoundingBox] = None,
                 **kwargs
                 ) -> Position:
        if not isinstance(entity, Prototype):
            raise Exception("'nearest_buildable' requires the Prototype of the desired entity as the first argument")

        # Convert bounding box to relative coordinates if provided
        bb_data = None
        dx, dy = 0, 0
        if bounding_box:
            dx = bounding_box.left_top.x# if bounding_box.left_top.x < 0 else 0
            dy = bounding_box.left_top.y# if bounding_box.left_top.y < 0 else 0
            MARGIN = 1

            bb_data = {
                "left_top": {"x": bounding_box.left_top.x-dx, "y": bounding_box.left_top.y-dy},
                "right_bottom": {"x": bounding_box.right_bottom.x-dx+MARGIN*2, "y": bounding_box.right_bottom.y-dy+MARGIN*2},
                "center": {"x": bounding_box.center.x-dx, "y": bounding_box.center.y-dy}
            }

        response, time_elapsed = self.execute(PLAYER, entity.value[0], bb_data)

        if isinstance(response, str):
            raise Exception(f"No viable place to put {str(entity)} found on the map")

        # if not self.game_state.last_observed_player_location:
        #     self.game_state.last_observed_player_location = self.game_state.player_location
        #
        # else:
        # return (math.floor(response['x']), math.floor(response['y']))
        if not bounding_box:
            return Position(x=response['x'], y=response['y'])
        else:
            return Position(x=response['x']-dx, y=response['y']-dy)