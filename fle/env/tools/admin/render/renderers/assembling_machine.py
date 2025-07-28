# renderers/assembling_machine.py
"""
Assembling machine renderer with recipe icons
"""

from typing import Dict, Tuple, Optional, Callable
from PIL import Image, ImageDraw

from fle.env import EntityCore

DIRECTIONS = {
    0: "north",
    2: "east",
    4: "south",
    6: "west"
}


def render(ent: EntityCore, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render arithmetic combinator with display"""
    entity = ent.model_dump()
    """Render assembling machine with recipe icon"""
    base_image = image_resolver(entity['name'])
    if base_image is None:
        return None

    # If no recipe, return base image
    if 'recipe' not in entity:
        return base_image

    # Create a copy to modify
    result = base_image.copy()

    # Try to get recipe icon
    icon = image_resolver(f"icon_{entity['recipe']}")
    if icon:
        # Draw dark circle background
        draw = ImageDraw.Draw(result)
        center_x = result.width // 2
        center_y = result.height // 2 - 10
        radius = 23

        draw.ellipse(
            [center_x - radius, center_y - radius,
             center_x + radius, center_y + radius],
            fill=(0, 0, 0, 166)
        )

        # Paste icon
        icon_x = center_x - icon.width // 2
        icon_y = center_y - icon.height // 2
        result.paste(icon, (icon_x, icon_y), icon if icon.mode == 'RGBA' else None)

    return result


def render_shadow(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render shadow"""
    return image_resolver(entity['name'], True)


def get_key(entity: Dict, grid) -> str:
    """Get cache key including recipe"""
    recipe = entity.get('recipe', '')
    direction = entity.get('direction', 0)
    return f"{recipe}_{direction}"


def get_size(entity: Dict) -> Tuple[float, float]:
    """Assembling machine is 3x3"""
    return (3, 3)