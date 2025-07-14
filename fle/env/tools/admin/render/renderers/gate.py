# renderers/gate.py
"""
Gate renderer
"""

from typing import Dict, Tuple, Optional, Callable
from PIL import Image


def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render gate"""
    direction = entity.get('direction', 0)
    orientation = 'vertical' if direction == 0 else 'horizontal'
    return image_resolver(f"{entity['name']}_{orientation}")


def render_shadow(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render shadow"""
    direction = entity.get('direction', 0)
    orientation = 'vertical' if direction == 0 else 'horizontal'
    return image_resolver(f"{entity['name']}_{orientation}", True)


def get_key(entity: Dict, grid) -> str:
    """Get cache key"""
    return str(entity.get('direction', 0))


def get_size(entity: Dict) -> Tuple[float, float]:
    """Gate is 1x1"""
    return (1, 1)