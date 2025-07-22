# renderers/transport_belt.py
"""
Transport belt renderer
"""
from typing import Dict, Tuple, Optional, Callable

from PIL import Image

from fle.env import EntityCore, Entity
from ..constants import NORTH, SOUTH, EAST, WEST, VERTICAL, HORIZONTAL

def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render transport belt"""

    around = get_around(entity, grid)
    count = sum(around)
    direction = entity.get('direction', 0)
    degree_offset = 90

    image = None


    if count in [0, 2, 3]:
        if direction in VERTICAL:
            image = image_resolver(f"{entity['name']}_vertical")
            degree_offset = -90
        else:
            image = image_resolver(f"{entity['name']}_horizontal")
    elif count == 1:
        if around[0] == 1:  # South
            if direction in VERTICAL:
                image = image_resolver(f"{entity['name']}_vertical")
                degree_offset = -90
            elif direction == EAST:
                image = image_resolver(f"{entity['name']}_bend_left")
                degree_offset = 180
            elif direction == WEST:
                image = image_resolver(f"{entity['name']}_bend_right")
                degree_offset = 90
        elif around[1] == 1:  # West
            if direction in HORIZONTAL:
                image = image_resolver(f"{entity['name']}_horizontal")
            elif direction == NORTH:
                image = image_resolver(f"{entity['name']}_bend_right")
                degree_offset = 90
            elif direction == SOUTH:
                image = image_resolver(f"{entity['name']}_bend_left")  # Changed from bend_left
                degree_offset = -180  # Add this back
        elif around[2] == 1:  # North
            if direction in VERTICAL:
                image = image_resolver(f"{entity['name']}_vertical")
                degree_offset = -90
            elif direction == EAST:
                image = image_resolver(f"{entity['name']}_bend_right")
                degree_offset = 90
            elif direction == WEST:
                image = image_resolver(f"{entity['name']}_bend_left")
                degree_offset = 180
        elif around[3] == 1:  # East
            if direction in HORIZONTAL:
                image = image_resolver(f"{entity['name']}_horizontal")
            elif direction == NORTH:
                image = image_resolver(f"{entity['name']}_bend_left")
                degree_offset = -180
            elif direction == SOUTH:
                image = image_resolver(f"{entity['name']}_bend_right")  # Changed from bend_right
                degree_offset = 90
                # Keep default degree_offset = 90

    if image is None:
        return None

    # Rotate image based on direction
    rotation = (direction * 45) - degree_offset
    if rotation != 0:
        image = image.rotate(-rotation, expand=True)

    return image


def render_shadow(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Transport belts have no shadows"""
    return None


def get_key(entity: Dict, grid) -> str:
    """Get cache key"""
    around = get_around(entity, grid)
    return f"{entity.get('direction', 0)}_{'_'.join(map(str, around))}"


# TODO: I think the semantics are wrong here @jack
def get_around(entity: Dict, grid) -> list:
    """Check surrounding connections"""
    return [
        is_transport_belt(grid.get_relative(0, -1), SOUTH) or
        is_splitter(grid.get_relative(0.5, -1), SOUTH) or
        is_splitter(grid.get_relative(-0.5, -1), SOUTH),

        is_transport_belt(grid.get_relative(1, 0), WEST) or
        is_splitter(grid.get_relative(1, 0.5), WEST) or
        is_splitter(grid.get_relative(1, -0.5), WEST),

        is_transport_belt(grid.get_relative(0, 1),  NORTH) or
        is_splitter(grid.get_relative(0.5, 1), NORTH) or
        is_splitter(grid.get_relative(-0.5, 1), NORTH),

        is_transport_belt(grid.get_relative(-1, 0), EAST) or
        is_splitter(grid.get_relative(-1, 0.5), EAST) or
        is_splitter(grid.get_relative(-1, -0.5), EAST)
    ]


def is_transport_belt(entity: Optional[Entity], direction: int) -> int:
    """Check if entity is transport belt facing direction"""
    if entity is None:
        return 0

    belt_types = ['transport-belt', 'fast-transport-belt', 'express-transport-belt']
    underground_types = ['underground-belt', 'fast-underground-belt', 'express-underground-belt']

    if entity.name in belt_types:
        if entity.direction.value == direction:
            return 1

    if entity.name in underground_types:
        if entity.type == 'output':
            if entity.direction.value == direction:
                return 1

    return 0


def is_splitter(entity: Optional[Entity], direction: int) -> int:
    """Check if entity is splitter facing direction"""
    if entity is None:
        return 0

    splitter_types = ['splitter', 'fast-splitter', 'express-splitter']

    if entity.name in splitter_types:
        if entity.direction.value == direction:
            return 1

    return 0


def get_size(entity: Dict) -> Tuple[float, float]:
    """Transport belt is 1x1"""
    return (1, 1)