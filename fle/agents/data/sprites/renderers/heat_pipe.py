# renderers/heat_pipe.py
"""
Heat pipe renderer with connection logic
"""

from typing import Dict, Tuple, Optional, Callable
from PIL import Image


def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render heat pipe based on connections"""
    around = get_around(entity, grid)
    count = sum(around)

    image_name = None

    if count == 0:
        image_name = "heat-pipe_single"
    elif count == 1:
        if around[0] == 1:
            image_name = "heat-pipe_ending_up"
        elif around[1] == 1:
            image_name = "heat-pipe_ending_right"
        elif around[2] == 1:
            image_name = "heat-pipe_ending_down"
        else:
            image_name = "heat-pipe_ending_left"
    elif count == 2:
        if around[0] == 1:
            if around[1] == 1:
                image_name = "heat-pipe_corner_right_up"
            elif around[2] == 1:
                image_name = "heat-pipe_straight_vertical"
            elif around[3] == 1:
                image_name = "heat-pipe_corner_left_up"
        elif around[1] == 1:
            if around[2] == 1:
                image_name = "heat-pipe_corner_right_down"
            elif around[3] == 1:
                image_name = "heat-pipe_straight_horizontal"
        else:
            image_name = "heat-pipe_corner_left_down"
    elif count == 3:
        if around[0] == 0:
            image_name = "heat-pipe_t_down"
        elif around[1] == 0:
            image_name = "heat-pipe_t_left"
        elif around[2] == 0:
            image_name = "heat-pipe_t_up"
        elif around[3] == 0:
            image_name = "heat-pipe_t_right"
    else:
        image_name = "heat-pipe_cross"

    return image_resolver(image_name)


def render_shadow(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Heat pipes have no shadows"""
    return None


def get_key(entity: Dict, grid) -> str:
    """Get cache key based on connections"""
    around = get_around(entity, grid)
    return '_'.join(map(str, around))


def get_around(entity: Dict, grid) -> list:
    """Check surrounding heat connections"""
    return [
        # North
        is_heat_pipe(grid.get_relative(0, -1)) or
        is_entity_in_direction(grid.get_relative(0, -1.5), "heat-exchanger", 0) or
        is_entity(grid.get_relative(-2, -3), "nuclear-reactor") or
        is_entity(grid.get_relative(0, -3), "nuclear-reactor") or
        is_entity(grid.get_relative(2, -3), "nuclear-reactor"),

        # East
        is_heat_pipe(grid.get_relative(1, 0)) or
        is_entity_in_direction(grid.get_relative(1.5, 0), "heat-exchanger", 2) or
        is_entity(grid.get_relative(3, -2), "nuclear-reactor") or
        is_entity(grid.get_relative(3, 0), "nuclear-reactor") or
        is_entity(grid.get_relative(3, 2), "nuclear-reactor"),

        # South
        is_heat_pipe(grid.get_relative(0, 1)) or
        is_entity_in_direction(grid.get_relative(0, 1.5), "heat-exchanger", 4) or
        is_entity(grid.get_relative(-2, 3), "nuclear-reactor") or
        is_entity(grid.get_relative(0, 3), "nuclear-reactor") or
        is_entity(grid.get_relative(2, 3), "nuclear-reactor"),

        # West
        is_heat_pipe(grid.get_relative(-1, 0)) or
        is_entity_in_direction(grid.get_relative(-1.5, 0), "heat-exchanger", 6) or
        is_entity(grid.get_relative(-3, -2), "nuclear-reactor") or
        is_entity(grid.get_relative(-3, 0), "nuclear-reactor") or
        is_entity(grid.get_relative(-3, 2), "nuclear-reactor")
    ]


def is_heat_pipe(entity: Optional[Dict]) -> int:
    """Check if entity is heat pipe"""
    if entity is None:
        return 0
    return 1 if entity['name'] == 'heat-pipe' else 0


def is_entity(entity: Optional[Dict], target: str) -> int:
    """Check if entity matches target"""
    if entity is None:
        return 0
    return 1 if entity['name'] == target else 0


def is_entity_in_direction(entity: Optional[Dict], target: str, direction: int) -> int:
    """Check if entity matches target and direction"""
    if entity is None:
        return 0
    return 1 if entity['name'] == target and entity.get('direction', 0) == direction else 0


def get_size(entity: Dict) -> Tuple[float, float]:
    """Heat pipe is 1x1"""
    return (1, 1)