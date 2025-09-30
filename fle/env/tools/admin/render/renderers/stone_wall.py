# renderers/stone_wall.py
"""
Stone wall renderer with connection logic
"""

from typing import Dict, Tuple, Optional, Callable
from PIL import Image


def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render stone wall based on connections"""
    return image_resolver(get_name(entity, grid))


def render_shadow(
    entity: Dict, grid, image_resolver: Callable
) -> Optional[Image.Image]:
    """Render shadow"""
    return image_resolver(get_name(entity, grid), True)


def get_name(entity: Dict, grid) -> str:
    """Get wall sprite name based on connections"""
    around = get_around(entity, grid)
    count = sum(around)

    if count == 0:
        return "stone-wall_single"
    elif count == 1:
        if around[0] == 1:
            return "stone-wall_single"
        elif around[1] == 1:
            return "stone-wall_ending_right"
        elif around[2] == 1:
            return "stone-wall_straight_vertical"
        else:
            return "stone-wall_ending_left"
    elif count == 2:
        if around[0] == 1:
            if around[1] == 1:
                return "stone-wall_ending_right"
            elif around[2] == 1:
                return "stone-wall_straight_vertical"
            elif around[3] == 1:
                return "stone-wall_ending_left"
        elif around[1] == 1:
            if around[2] == 1:
                return "stone-wall_corner_right_down"
            elif around[3] == 1:
                return "stone-wall_straight_horizontal"
        else:
            return "stone-wall_corner_left_down"
    elif count == 3:
        if around[0] == 0:
            return "stone-wall_t_up"
        elif around[1] == 0:
            return "stone-wall_corner_left_down"
        elif around[2] == 0:
            return "stone-wall_straight_horizontal"
        elif around[3] == 0:
            return "stone-wall_corner_right_down"
    else:
        return "stone-wall_t_up"


def get_key(entity: Dict, grid) -> str:
    """Get cache key based on connections"""
    around = get_around(entity, grid)
    return "_".join(map(str, around))


def get_around(entity: Dict, grid) -> list:
    """Check surrounding wall connections"""
    return [
        # North
        is_stone_wall(grid.get_relative(0, -1)) or is_gate(grid.get_relative(0, -1), 0),
        # East
        is_stone_wall(grid.get_relative(1, 0)) or is_gate(grid.get_relative(1, 0), 2),
        # South
        is_stone_wall(grid.get_relative(0, 1)) or is_gate(grid.get_relative(0, 1), 0),
        # West
        is_stone_wall(grid.get_relative(-1, 0)) or is_gate(grid.get_relative(-1, 0), 2),
    ]


def is_stone_wall(entity: Optional[Dict]) -> int:
    """Check if entity is stone wall"""
    if entity is None:
        return 0
    return 1 if entity["name"] == "stone-wall" else 0


def is_gate(entity: Optional[Dict], direction: int) -> int:
    """Check if entity is gate with direction"""
    if entity is None:
        return 0
    return (
        1 if entity["name"] == "gate" and entity.get("direction", 0) == direction else 0
    )


def get_size(entity: Dict) -> Tuple[float, float]:
    """Stone wall is 1x1"""
    return (1, 1)
