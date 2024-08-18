import math

import numpy as np
from scipy import ndimage

from factorio_entities import ResourcePatch


class InspectResources:

    def __init__(self, connection, game_state):
        self.game_state = game_state

    def __call__(self, position,
                 #relative=False
                 ) -> ResourcePatch:
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
                    #"offset": abs(y_offset),
                    #"named_direction": named_dir,
                    "top_left_position": (x_min, y_min),
                    "bottom_right_position": (x_max, y_max)
                }

                if group_size < 50:
                    if item not in small_groups:
                        small_groups[item] = {"count": 0}
                    small_groups[item]["count"] += group_size
                    small_groups[item][named_dir] = small_groups[item].get(named_dir,0) + abs(y_offset)
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
                #{"distance": (value if value < 1000 else math.floor(value / 1000)),
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

        return groups