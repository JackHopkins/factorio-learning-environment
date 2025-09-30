# renderers/chemical_plant.py
"""
Chemical plant renderer with recipe icons
"""

from typing import Dict, Tuple, Optional, Callable
from PIL import Image, ImageDraw

DIRECTIONS = {0: "north", 2: "east", 4: "south", 6: "west"}


def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render chemical plant with recipe icon"""
    direction = entity.get("direction", 0)
    base = image_resolver(f"{entity['name']}_{DIRECTIONS[direction]}")

    if base is None:
        return None

    if "recipe" not in entity:
        return base

    # Create a copy to modify
    result = base.copy()
    icon = image_resolver(f"icon_{entity['recipe']}")

    if icon:
        # Draw dark circle background
        draw = ImageDraw.Draw(result)
        center_x = result.width // 2
        center_y = result.height // 2 - 10
        radius = 23

        draw.ellipse(
            [
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
            ],
            fill=(0, 0, 0, 166),
        )

        # Paste icon
        icon_x = center_x - icon.width // 2
        icon_y = center_y - icon.height // 2
        result.paste(icon, (icon_x, icon_y), icon if icon.mode == "RGBA" else None)

    return result


def render_shadow(
    entity: Dict, grid, image_resolver: Callable
) -> Optional[Image.Image]:
    """Render shadow"""
    direction = entity.get("direction", 0)
    return image_resolver(f"{entity['name']}_{DIRECTIONS[direction]}", True)


def get_key(entity: Dict, grid) -> str:
    """Get cache key including recipe"""
    recipe = entity.get("recipe", "")
    direction = entity.get("direction", 0)
    return f"{recipe}_{direction}"


def get_size(entity: Dict) -> Tuple[float, float]:
    """Chemical plant is 3x3"""
    return (3, 3)
