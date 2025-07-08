from typing import Optional

from fle.env.entities import Position, ResourcePatch, BoundingBox
from fle.env.game_types import Resource
from fle.env.tools import Tool


class GetResourcePatch(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(
        self,
        resource: Resource,
        position: Position,
        radius: int = 30,
    ) -> Optional[ResourcePatch]:
        """
        Get the resource patch at position (x, y) if it exists in the radius.
        if radius is set to 0, it will only check the exact position for this resource patch.
        :param resource: Resource to get, e.g Resource.Coal
        :param position: Position to get resource patch
        :param radius: Radius to search for resource patch
        :example coal_patch_at_origin = get_resource_patch(Resource.Coal, Position(x=0, y=0))
        :return: ResourcePatch if found, else None
        """
        response, time_elapsed = self.execute(
            self.player_index, resource[0], position.x, position.y, radius
        )

        if not isinstance(response, dict) or response == {}:
            top_level_message = str(response).split(":")[-1].strip()
            raise Exception(
                f"Could not get {resource[0]} at {position}: {top_level_message}"
            )

        left_top = Position(
            x=response["bounding_box"]["left_top"]["x"],
            y=response["bounding_box"]["left_top"]["y"],
        )
        right_bottom = Position(
            x=response["bounding_box"]["right_bottom"]["x"],
            y=response["bounding_box"]["right_bottom"]["y"],
        )
        left_bottom = Position(
            x=response["bounding_box"]["left_top"]["x"],
            y=response["bounding_box"]["right_bottom"]["y"],
        )
        right_top = Position(
            x=response["bounding_box"]["right_bottom"]["x"],
            y=response["bounding_box"]["left_top"]["y"],
        )
        bounding_box = BoundingBox(
            left_top=left_top,
            right_bottom=right_bottom,
            left_bottom=left_bottom,
            right_top=right_top,
        )  # , center=Position(x=(left_top.x + right_bottom.x) / 2, y=(left_top.y + right_bottom.y) / 2))

        resource_patch = ResourcePatch(
            name=resource[0], size=response["size"], bounding_box=bounding_box
        )

        return resource_patch
