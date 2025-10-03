# renderers/rail_signal.py
"""
Rail signal and rail chain signal renderer
"""

from typing import Dict, Tuple, Optional, Callable
from PIL import Image


def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render rail signal"""
    direction = entity.get("direction", 0)
    return image_resolver(f"{entity['name']}_{direction}")


def render_shadow(
    entity: Dict, grid, image_resolver: Callable
) -> Optional[Image.Image]:
    """Rail signals have no shadows"""
    return None


def get_key(entity: Dict, grid) -> str:
    """Get cache key"""
    return str(entity.get("direction", 0))


def get_size(entity: Dict) -> Tuple[float, float]:
    """Rail signal is 1x1"""
    return (1, 1)
