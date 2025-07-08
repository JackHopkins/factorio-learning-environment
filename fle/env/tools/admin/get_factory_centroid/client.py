from fle.env.entities import BoundingBox, Position
from fle.env.tools import Tool
from fle.env.utils.camera import Camera


class GetFactoryCentroid(Tool):
    def __init__(self, lua_script_manager, game_state):
        self.state = {"input": {}, "output": {}}
        super().__init__(lua_script_manager, game_state)

    def __call__(self) -> Camera:
        """
        Gets the bounding box of the enti factory.
        """

        result, _ = self.execute(self.player_index)

        if isinstance(result, str):
            raise Exception(result)

        result = self.clean_response(result)

        try:
            if "bounds" in result:
                bounds = BoundingBox(
                    left_top=Position(
                        x=result["bounds"]["left_top"]["x"],
                        y=result["bounds"]["left_top"]["y"],
                    ),
                    right_bottom=Position(
                        x=result["bounds"]["right_bottom"]["x"],
                        y=result["bounds"]["right_bottom"]["y"],
                    ),
                    left_bottom=Position(
                        x=result["bounds"]["left_top"]["x"],
                        y=result["bounds"]["right_bottom"]["y"],
                    ),
                    right_top=Position(
                        x=result["bounds"]["right_bottom"]["x"],
                        y=result["bounds"]["left_top"]["y"],
                    ),
                )
            else:
                bounds = BoundingBox(
                    left_top=Position(x=-10, y=-10),
                    right_bottom=Position(x=10, y=10),
                    left_bottom=Position(x=-10, y=10),
                    right_top=Position(x=10, y=-10),
                )
            return Camera(
                bounds=bounds,
                zoom=result["camera"]["zoom"],
                centroid=result["centroid"],
                raw_centroid=result["raw_centroid"],
                entity_count=result["entity_count"],
                position=result["camera"]["position"],
            )
        except Exception:
            return None
