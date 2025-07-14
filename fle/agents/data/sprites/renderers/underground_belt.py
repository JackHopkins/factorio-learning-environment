# renderers/underground_belt.py
"""
Underground belt renderer
"""

from typing import Dict, Tuple, Optional, Callable
from PIL import Image

RELATIVE_DIRECTIONS = {
    0: "up",
    2: "right",
    4: "down",
    6: "left"
}


def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render underground belt"""
    belt_type = entity.get('type', 'input')
    direction = entity.get('direction', 0)
    prefix = 'in' if belt_type == 'input' else 'out'

    return image_resolver(f"{entity['name']}_{prefix}_{RELATIVE_DIRECTIONS[direction]}")


def render_shadow(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Underground belts have no shadows"""
    return None


def get_key(entity: Dict, grid) -> str:
    """Get cache key"""
    return f"{entity.get('direction', 0)}_{entity.get('type', 'input')}"


def get_size(entity: Dict) -> Tuple[float, float]:
    """Underground belt is 1x1"""
    return (1, 1)