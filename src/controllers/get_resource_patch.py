from typing import Tuple

import numpy as np
from scipy import ndimage

from controllers.__action import Action
from factorio_entities import Position, ResourcePatch, BoundingBox

from factorio_instance import PLAYER
from factorio_types import Resource


class GetResourcePatch(Action):

    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self,
                 resource: Resource,
                 position: Position,
                 radius: int = 10,
                 #relative=False
                 ) -> ResourcePatch:
        """
        Get the resource patch at position (x, y) if it exists on the world.
        :param resource: Resource to get, e.g Resource.Coal
        :param position: Position to get resource patch
        :param radius: Radius to search for resource patch
        :example coal_patch_at_origin = get_resource_patch(Resource.Coal, Position(x=0, y=0))
        :return: ResourcePatch
        """
        response, time_elapsed = self.execute(PLAYER, resource[0], position.x, position.y, radius)

        if not isinstance(response, dict) or response == {}:
            raise Exception(f"Could not get {resource[0]} at {position}.", response)

        left_top = Position(x=response['bounding_box']['left_top']['x'], y=response['bounding_box']['left_top']['y'])
        right_bottom = Position(x=response['bounding_box']['right_bottom']['x'], y=response['bounding_box']['right_bottom']['y'])
        bounding_box = BoundingBox(left_top=left_top, right_bottom=right_bottom, center=Position(x=(left_top.x + right_bottom.x) / 2, y=(left_top.y + right_bottom.y) / 2))

        resource_patch = ResourcePatch(name=resource[0], size=response['size'], bounding_box=bounding_box)

        return resource_patch
        def get_direction(y_offset, x_offset):
            angle = (np.arctan2(-y_offset, -x_offset) * 180 / np.pi) - 90

            if angle < 0:
                angle += 360

            directions = [
                (348.75, 360, "north"),
                (0, 11.25, "north"),
                (11.25, 33.75, "north-northeast"),
                (33.75, 56.25, "northeast"),
                (56.25, 78.75, "east-northeast"),
                (78.75, 101.25, "east"),
                (101.25, 123.75, "east-southeast"),
                (123.75, 146.25, "southeast"),
                (146.25, 168.75, "south-southeast"),
                (168.75, 191.25, "south"),
                (191.25, 213.75, "south-southwest"),
                (213.75, 236.25, "southwest"),
                (236.25, 258.75, "west-southwest"),
                (258.75, 281.25, "west"),
                (281.25, 303.75, "west-northwest"),
                (303.75, 326.25, "northwest"),
                (326.25, 348.75, "north-northwest"),
            ]

            for start, end, direction in directions:
                if angle >= start and angle < end:
                    return direction

            return "north"

        vocabulary = self.game_state.vocabulary.i_vocabulary
        grid_world = self.game_state.grid_world
        unique_objects = np.unique(grid_world)

        groups = {}
        small_groups = {}

        for obj in unique_objects:
            if obj == 0:
                continue

            binary_array = (grid_world == obj).astype(int)
            connected_components, num_labels = ndimage.measurements.label(binary_array)

            for label in range(1, num_labels + 1):
                if obj == -1:
                    continue
                item = vocabulary[obj]
                if item == "character":
                    continue

                group_indices = np.where(connected_components == label)
                group_size = len(group_indices[0])

                y_offset = int(np.mean(group_indices[0])) - (self.game_state.bounding_box // 2)
                x_offset = int(np.mean(group_indices[1])) - (self.game_state.bounding_box // 2)

                #if relative:
                #    y_offset -= self.game_state.last_observed_player_location[1]
                #    x_offset -= self.game_state.last_observed_player_location[0]

                y_max = int(np.max(group_indices[0])) - (self.game_state.bounding_box // 2)
                x_max = int(np.max(group_indices[1])) - (self.game_state.bounding_box // 2)

                y_min = int(np.min(group_indices[0])) - (self.game_state.bounding_box // 2)
                x_min = int(np.min(group_indices[1])) - (self.game_state.bounding_box // 2)
                named_dir = get_direction(y_offset, x_offset)
                direction = {
                    # "offset": abs(y_offset),
                    # "named_direction": named_dir,
                    "top_left_position": (x_min, y_min),
                    "bottom_right_position": (x_max, y_max)
                }

                if group_size < 50:
                    if item not in small_groups:
                        small_groups[item] = {"count": 0}
                    small_groups[item]["count"] += group_size
                    small_groups[item][named_dir] = small_groups[item].get(named_dir, 0) + abs(y_offset)
                else:
                    if item not in groups:
                        groups[item] = []

                    group_description = {
                        "size": group_size,
                        **direction
                    }
                    groups[item].append(group_description)

        for item, data in small_groups.items():
            count = data["count"]
            # cardinals = [
            # {"distance": (value if value < 1000 else math.floor(value / 1000)),
            # "unit": "metres" if value < 1000 else "km"}
            #  for key, value in data.items()
            # ]
            # if not cardinals:
            #     continue

            # if count > 1000:
            #    count_str = math.floor((float(count) / 100)) / 10

            if item not in groups:
                groups[item] = []

            group_description = {
                "size": count,
                # "directions": cardinals,
                "scattered": True
            }
            groups[item].append(group_description)

        name, metaclass = resource
        if name in groups:
            for group in groups[name]:
                top_left_x, top_left_y = group["top_left_position"]
                bottom_right_x, bottom_right_y = group["bottom_right_position"]

                #if top_left_x <= position.x <= bottom_right_x+0.5 and top_left_y <= position.y <= bottom_right_y+0.5:

                return metaclass(
                    name=name,
                    size=group.get("size", 0),
                    bounding_box=BoundingBox(left_top=Position(x=top_left_x, y=top_left_y),
                                             right_bottom=Position(x=bottom_right_x, y=bottom_right_y),
                                             center=Position(x=(top_left_x + bottom_right_x) / 2,
                                                                y=(top_left_y + bottom_right_y) / 2)
                                                )
                )

        return None
        #return groups
