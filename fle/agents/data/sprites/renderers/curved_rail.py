# renderers/curved_rail.py
"""
Curved rail renderer
"""

from typing import Dict, Tuple, Optional, Callable
from PIL import Image


def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Curved rail rendering is handled in main render loop"""
    return None


def render_shadow(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Rails have no shadows"""
    return None


def get_key(entity: Dict, grid) -> str:
    """Get cache key"""
    return str(entity.get('direction', 0))


def get_size(entity: Dict) -> Tuple[float, float]:
    """Get curved rail size based on direction"""
    direction = entity.get('direction', 0)
    if direction in [0, 1, 4, 5]:
        return (5, 9)
    else:
        return (9, 4.5)