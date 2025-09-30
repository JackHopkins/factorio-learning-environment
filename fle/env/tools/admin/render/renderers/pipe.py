# renderers/pipe.py
"""
Pipe renderer with connection logic
"""

from typing import Dict, Tuple, Optional, Callable
from PIL import Image


def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render pipe based on connections"""
    around = get_around(entity, grid)
    count = sum(around)

    image_name = None

    if count == 0:
        image_name = "pipe_straight_horizontal"
    elif count == 1:
        if around[0] == 1:
            image_name = "pipe_ending_up"
        elif around[1] == 1:
            image_name = "pipe_ending_right"
        elif around[2] == 1:
            image_name = "pipe_ending_down"
        else:
            image_name = "pipe_ending_left"
    elif count == 2:
        if around[0] == 1:
            if around[1] == 1:
                image_name = "pipe_corner_up_right"
            elif around[2] == 1:
                image_name = "pipe_straight_vertical"
            elif around[3] == 1:
                image_name = "pipe_corner_up_left"
        elif around[1] == 1:
            if around[2] == 1:
                image_name = "pipe_corner_down_right"
            elif around[3] == 1:
                image_name = "pipe_straight_horizontal"
        else:
            image_name = "pipe_corner_down_left"
    elif count == 3:
        if around[0] == 0:
            image_name = "pipe_t_down"
        elif around[1] == 0:
            image_name = "pipe_t_left"
        elif around[2] == 0:
            image_name = "pipe_t_up"
        elif around[3] == 0:
            image_name = "pipe_t_right"
    else:
        image_name = "pipe_cross"

    return image_resolver(image_name)


def render_shadow(
    entity: Dict, grid, image_resolver: Callable
) -> Optional[Image.Image]:
    """Pipes have no shadows"""
    return None


def get_key(entity: Dict, grid) -> str:
    """Get cache key based on connections"""
    around = get_around(entity, grid)
    return "_".join(map(str, around))


def get_around(entity: Dict, grid) -> list:
    """Check surrounding pipe connections"""
    # Simplified version - would need full connection logic
    return [
        # North
        is_pipe(grid.get_relative(0, -1), 4)
        or is_entity_in_direction(grid.get_relative(0, -1), "offshore-pump", 0),
        # East
        is_pipe(grid.get_relative(1, 0), 6)
        or is_entity_in_direction(grid.get_relative(1, 0), "offshore-pump", 2),
        # South
        is_pipe(grid.get_relative(0, 1), 0)
        or is_entity_in_direction(grid.get_relative(0, 1), "offshore-pump", 4),
        # West
        is_pipe(grid.get_relative(-1, 0), 2)
        or is_entity_in_direction(grid.get_relative(-1, 0), "offshore-pump", 6),
    ]


def is_pipe(entity: Optional[Dict], direction: int) -> int:
    """Check if entity is pipe or pipe-to-ground"""
    if entity is None:
        return 0

    if entity["name"] == "pipe":
        return 1
    elif entity["name"] == "pipe-to-ground":
        if entity.get("direction", 0) == direction:
            return 1

    return 0


def is_entity_in_direction(entity: Optional[Dict], target: str, direction: int) -> int:
    """Check if entity matches target and direction"""
    if entity is None:
        return 0

    if entity["name"] == target and entity.get("direction", 0) == direction:
        return 1

    return 0


def get_size(entity: Dict) -> Tuple[float, float]:
    """Pipe is 1x1"""
    return (1, 1)
