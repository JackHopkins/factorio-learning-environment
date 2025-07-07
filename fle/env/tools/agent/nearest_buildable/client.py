from fle.env import entities as ent
from fle.env.game_types import Prototype
from fle.env.tools import Tool


class NearestBuildable(Tool):
    def __init__(self, lua_script_manager, game_state):
        super().__init__(lua_script_manager, game_state)
        # self.connection = connection
        self.game_state = game_state

    def __call__(
        self,
        entity: Prototype,
        building_box: ent.BuildingBox,
        center_position: ent.Position,
        **kwargs,
    ) -> ent.BoundingBox:
        """
        Find the nearest buildable area for an entity.

        :param entity: Prototype of the entity to build.
        :param building_box: The building box denoting the area of location that must be placeable.
        :param center_position: The position to find the nearest area where building box fits
        :return: BoundingBox of the nearest buildable area or None if no such area exists.
        """
        if not isinstance(entity, Prototype):
            raise Exception(
                "'nearest_buildable' requires the Prototype of the desired entity as the first argument"
            )

        MARGIN = 0
        dx = building_box.width
        dy = building_box.height
        dx = dx + MARGIN
        dy = dy + MARGIN
        bb_data = {"left_top": {"x": 0, "y": 0}, "right_bottom": {"x": dx, "y": dy}}
        # make all the values integers
        # center_position = {"x": math.ceil(center_position.x + 0.5), "y": math.ceil(center_position.y + 0.5)}
        center_position = {"x": center_position.x, "y": center_position.y}

        response, time_elapsed = self.execute(
            self.player_index, entity.value[0], bb_data, center_position
        )

        if isinstance(response, str):
            raise Exception(
                f"No viable place to put {str(entity)} near the centre position {center_position} with this BuildingBox size found on the map. Either decrease the size of the BuildingBox or use multiple smaller BuildingBoxes"
            )

        right_bottom = ent.Position(
            x=response["right_bottom"]["x"], y=response["right_bottom"]["y"]
        )
        left_top = ent.Position(
            x=response["left_top"]["x"], y=response["left_top"]["y"]
        )
        left_bottom = ent.Position(
            x=response["left_top"]["x"], y=response["right_bottom"]["y"]
        )
        right_top = ent.Position(
            x=response["right_bottom"]["x"], y=response["left_top"]["y"]
        )
        # return {"left_top": Position(x=response_x, y=response_y),
        #         "right_bottom": Position(x=response_x+dx-1,
        #                                   y=response_y+dy-1),
        #         "left_bottom": Position(x=response_x, y=response_y+dy-1),
        #         "right_top": Position(x=response_x + dx-1, y=response_y)}
        #
        # XOFFSET, YOFFSET = -0.5, -0.5
        return ent.BoundingBox(
            left_top=left_top,
            right_bottom=right_bottom,
            left_bottom=left_bottom,
            right_top=right_top,
        )
