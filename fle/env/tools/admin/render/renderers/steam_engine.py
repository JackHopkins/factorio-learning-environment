# renderers/steam_engine.py
"""
Steam engine renderer
"""

from typing import Dict, Tuple, Optional, Callable
from PIL import Image


def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render steam engine"""
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
    """Get steam engine size based on direction"""
    direction = entity.get('direction', 0)
    if direction in [2, 6]:  # East/West (horizontal)
        return (5, 3)
    else:  # North/South (vertical)
        return (3, 5)