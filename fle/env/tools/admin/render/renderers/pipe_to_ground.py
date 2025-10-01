# renderers/pipe_to_ground.py
"""
Pipe to ground renderer
"""

from typing import Dict, Tuple, Optional, Callable
from PIL import Image

RELATIVE_DIRECTIONS = {0: "north", 2: "east", 4: "south", 6: "west"}


def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render pipe to ground"""
    direction = entity.get("direction", 0)
    return image_resolver(f"{entity['name']}_{RELATIVE_DIRECTIONS[direction]}")


def render_shadow(
    entity: Dict, grid, image_resolver: Callable
) -> Optional[Image.Image]:
    """Pipe to ground has no shadow"""
    return None


def get_key(entity: Dict, grid) -> str:
    """Get cache key"""
    return str(entity.get("direction", 0))


def get_size(entity: Dict) -> Tuple[float, float]:
    """Pipe to ground is 1x1"""
    return (1, 1)
