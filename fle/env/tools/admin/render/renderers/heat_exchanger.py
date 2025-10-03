# renderers/heat_exchanger.py
"""
Heat exchanger renderer
"""

from typing import Dict, Tuple, Optional, Callable
from PIL import Image

DIRECTIONS = {0: "north", 2: "east", 4: "south", 6: "west"}


def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render heat exchanger"""
    direction = entity.get("direction", 0)
    return image_resolver(f"{entity['name']}_{DIRECTIONS[direction]}")


def render_shadow(
    entity: Dict, grid, image_resolver: Callable
) -> Optional[Image.Image]:
    """Render shadow"""
    direction = entity.get("direction", 0)
    return image_resolver(f"{entity['name']}_{DIRECTIONS[direction]}", True)


def get_key(entity: Dict, grid) -> str:
    """Get cache key"""
    return str(entity.get("direction", 0))


def get_size(entity: Dict) -> Tuple[float, float]:
    """Get heat exchanger size based on direction"""
    direction = entity.get("direction", 0)
    if direction in [2, 6]:  # East/West
        return (2, 3)
    else:  # North/South
        return (3, 2)
