# renderers/burner_mining_drill.py
"""
Burner mining drill renderer
"""

from typing import Dict, Tuple, Optional, Callable
from PIL import Image

DIRECTIONS = {
    0: "north",
    2: "east",
    4: "south",
    6: "west"
}


def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render burner mining drill"""
    direction = entity.get('direction', 0)
    return image_resolver(f"{entity['name']}_{DIRECTIONS[direction]}")


def render_shadow(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render shadow"""
    direction = entity.get('direction', 0)
    return image_resolver(f"{entity['name']}_{DIRECTIONS[direction]}", True)


def get_key(entity: Dict, grid) -> str:
    """Get cache key"""
    return str(entity.get('direction', 0))


def get_size(entity: Dict) -> Tuple[float, float]:
    """Burner mining drill is 2x2"""
    return (2, 2)