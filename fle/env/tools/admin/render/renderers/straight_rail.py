# renderers/straight_rail.py
"""
Straight rail renderer
"""

from typing import Dict, Tuple, Optional, Callable
from PIL import Image


def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Straight rail rendering is handled in main render loop"""
    return None


def render_shadow(
    entity: Dict, grid, image_resolver: Callable
) -> Optional[Image.Image]:
    """Rails have no shadows"""
    return None


def get_key(entity: Dict, grid) -> str:
    """Get cache key"""
    return str(entity.get("direction", 0))


def get_size(entity: Dict) -> Tuple[float, float]:
    """Straight rail is 3x3"""
    return (3, 3)
