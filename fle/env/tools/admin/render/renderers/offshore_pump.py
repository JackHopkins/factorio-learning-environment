# renderers/offshore_pump.py
"""
Offshore pump renderer
"""

from typing import Dict, Tuple, Optional, Callable
from PIL import Image

# Factorio 2.0: 16-direction system (0, 4, 8, 12 for cardinals)
DIRECTIONS = {0: "north", 4: "east", 8: "south", 12: "west"}


def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render offshore pump"""
    direction = entity.get("direction", 0)
    return image_resolver(f"{entity['name']}_{DIRECTIONS[direction]}")


def render_shadow(
    entity: Dict, grid, image_resolver: Callable
) -> Optional[Image.Image]:
    """Offshore pumps have no shadows"""
    return None


def get_key(entity: Dict, grid) -> str:
    """Get cache key"""
    return str(entity.get("direction", 0))


def get_size(entity: Dict) -> Tuple[float, float]:
    """Offshore pump is 2x2"""
    return (2, 2)
