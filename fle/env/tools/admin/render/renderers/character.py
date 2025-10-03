# renderers/character.py
"""
Character renderer for Factorio player characters
Uses sprites with naming format: name_{variant}_{direction}.png
"""

from typing import Dict, Tuple, Optional, Callable
from PIL import Image

# Default player colors (can be customized)
DEFAULT_PLAYER_COLOR = (255, 165, 0)  # Orange

# Sprite sheet configurations
SPRITE_CONFIGS = {
    "idle": {"grid": (22, 8), "directions": "standard"},
    "idle_gun": {"grid": (22, 8), "directions": "standard"},
    "running": {"grid": (22, 8), "directions": "standard"},
    "running_gun": {"grid": (22, 18), "directions": "standard"},
    "mining": {"grid": (13, 8), "directions": "mining"},
    "dead": {"grid": (2, 1), "directions": "dead"},
}

# Direction mappings for different sprite types
DIRECTION_MAPPINGS = {
    "standard": {
        0: 0,  # North
        1: 1,  # North-East
        2: 2,  # East
        3: 3,  # South-East
        4: 4,  # South
        5: 5,  # South-West
        6: 6,  # West
        7: 7,  # North-West
    },
    "mining": {
        0: 0,  # North
        1: 0,  # NE -> North
        2: 3,  # East
        3: 3,  # SE -> East
        4: 6,  # South
        5: 6,  # SW -> South
        6: 9,  # West
        7: 9,  # NW -> West
    },
    "dead": {
        0: 0,  # North/South
        1: 1,  # NE -> East/West
        2: 1,  # East/West
        3: 1,  # SE -> East/West
        4: 0,  # South -> North/South
        5: 0,  # SW -> North/South
        6: 1,  # West -> East/West
        7: 1,  # NW -> East/West
    },
}


def get_sprite_config(state: str, has_gun: bool = False) -> Dict:
    """Get the sprite configuration for a given state."""
    if state == "idle":
        return SPRITE_CONFIGS["idle_gun" if has_gun else "idle"]
    elif state == "running":
        return SPRITE_CONFIGS["running_gun" if has_gun else "running"]
    elif state == "mining":
        return SPRITE_CONFIGS["mining"]
    elif state == "dead":
        return SPRITE_CONFIGS["dead"]
    else:
        return SPRITE_CONFIGS["idle"]


def apply_color_to_mask(mask: Image.Image, color: Tuple[int, int, int]) -> Image.Image:
    """Apply color tinting to a mask image.

    Args:
        mask: The mask image (grayscale)
        color: RGB color tuple to apply

    Returns:
        Colored mask image
    """
    # Convert mask to RGBA if not already
    if mask.mode != "RGBA":
        mask = mask.convert("RGBA")

    # Use the mask's alpha channel to blend
    result = Image.new("RGBA", mask.size, (0, 0, 0, 0))

    # Apply color based on mask brightness
    pixels = mask.load()
    result_pixels = result.load()

    for y in range(mask.height):
        for x in range(mask.width):
            r, g, b, a = pixels[x, y]
            # Use the brightness of the mask pixel to determine opacity
            brightness = (r + g + b) // 3
            if brightness > 0:
                result_pixels[x, y] = (
                    int(color[0] * brightness / 255),
                    int(color[1] * brightness / 255),
                    int(color[2] * brightness / 255),
                    a,
                )

    return result


def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render character based on state and direction."""
    # Get character properties
    direction = entity.get("direction", 0)
    state = entity.get("state", "idle")  # idle, running, mining, dead
    level = entity.get("level", 1)  # armor level: 1, 2, or 3
    has_gun = entity.get("has_gun", False)
    player_color = entity.get("color", DEFAULT_PLAYER_COLOR)
    animation_frame = entity.get("animation_frame", 0)

    # Get sprite configuration
    config = get_sprite_config(state, has_gun)
    cols, rows = config["grid"]
    direction_mapping = DIRECTION_MAPPINGS[config["directions"]]

    # Determine sprite sheet names based on state
    if state == "idle":
        if has_gun:
            base_name = f"level{level}_idle_gun"
            mask_name = f"level{level}_idle_gun_mask"
        else:
            base_name = f"level{level}_idle"
            mask_name = f"level{level}_idle_mask"
    elif state == "running":
        if has_gun:
            base_name = f"level{level}_running_gun"
            mask_name = f"level{level}_running_gun_mask"
        else:
            base_name = f"level{level}_running"
            mask_name = f"level{level}_running_mask"
    elif state == "mining":
        base_name = f"level{level}_mining_tool"
        mask_name = f"level{level}_mining_tool_mask"
    elif state == "dead":
        base_name = f"level{level}_dead"
        mask_name = f"level{level}_dead_mask"
    else:
        # Default to idle
        base_name = f"level{level}_idle"
        mask_name = f"level{level}_idle_mask"

    # Handle armor addons for levels 2 and 3
    if level > 1:
        base_name = base_name.replace(f"level{level}", f"level{level}addon")
        mask_name = mask_name.replace(f"level{level}", f"level{level}addon")

    # Calculate variant (column) and direction (row) based on the mapping
    variant = direction_mapping.get(direction, 0)
    direction_row = min(animation_frame, rows - 1)

    # Build sprite filename using variant_direction format
    sprite_filename = f"{base_name}_{variant}_{direction_row}"
    mask_filename = f"{mask_name}_{variant}_{direction_row}"

    # Try to load the base sprite
    base_sprite = image_resolver(f"character/{sprite_filename}", False)

    if not base_sprite:
        # Fallback: try without the character/ prefix
        base_sprite = image_resolver(sprite_filename, False)

    if not base_sprite:
        return None

    # Try to load the mask
    mask_sprite = image_resolver(f"character/{mask_filename}", False)
    if not mask_sprite:
        mask_sprite = image_resolver(mask_filename, False)

    # If we have a mask, apply the player color
    if mask_sprite:
        colored_mask = apply_color_to_mask(mask_sprite, player_color)

        # Composite the colored mask over the base sprite
        result = Image.new("RGBA", base_sprite.size, (0, 0, 0, 0))
        result.paste(base_sprite, (0, 0), base_sprite)
        result.paste(
            colored_mask, (9, 0), colored_mask
        )  # There is an offset with the mask

        return result

    return base_sprite


def render_shadow(
    entity: Dict, grid, image_resolver: Callable
) -> Optional[Image.Image]:
    """Render character shadow."""
    # Get character properties
    direction = entity.get("direction", 0)
    state = entity.get("state", "idle")
    level = entity.get("level", 1)
    has_gun = entity.get("has_gun", False)
    animation_frame = entity.get("animation_frame", 0)

    # Shadow sprites have different dimensions
    shadow_config = {
        "idle": (22, 8),
        "idle_gun": (22, 8),
        "running": (10, 7),  # Running shadows are smaller
        "running_gun": (10, 7),
        "mining": (13, 8),
        "dead": (2, 1),
    }

    # Determine shadow sprite name
    if state == "idle":
        if has_gun:
            shadow_base = f"level{level}_idle_gun_shadow"
            cols, rows = shadow_config["idle_gun"]
        else:
            shadow_base = f"level{level}_idle_shadow"
            cols, rows = shadow_config["idle"]
    elif state == "running":
        if has_gun:
            shadow_base = f"level{level}_running_gun_shadow"
            cols, rows = shadow_config["running_gun"]
        else:
            shadow_base = f"level{level}_running_shadow"
            cols, rows = shadow_config["running"]
    elif state == "mining":
        shadow_base = f"level{level}_mining_tool_shadow"
        cols, rows = shadow_config["mining"]
    elif state == "dead":
        shadow_base = f"level{level}_dead_shadow"
        cols, rows = shadow_config["dead"]
    else:
        shadow_base = f"level{level}_idle_shadow"
        cols, rows = shadow_config["idle"]

    # Handle armor addons
    if level > 1:
        shadow_base = shadow_base.replace(f"level{level}", f"level{level}addon")

    # Get appropriate direction mapping
    if state == "mining":
        direction_mapping = DIRECTION_MAPPINGS["mining"]
    elif state == "dead":
        direction_mapping = DIRECTION_MAPPINGS["dead"]
    else:
        # Running shadows have fewer columns, so we need to map directions differently
        if state == "running":
            # Map 8 directions to fewer columns for running shadows
            direction_mapping = {
                0: 0,  # North
                1: 1,  # NE
                2: 2,  # East
                3: 3,  # SE
                4: 4,  # South
                5: 5,  # SW
                6: 6,  # West
                7: 7,  # NW
            }
            # Adjust for actual available columns
            if cols < 8:
                direction_mapping = {
                    k: min(v, cols - 1) for k, v in direction_mapping.items()
                }
        else:
            direction_mapping = DIRECTION_MAPPINGS["standard"]

    # Calculate variant and direction
    variant = direction_mapping.get(direction, 0)
    direction_row = min(animation_frame, rows - 1)

    # Try to load shadow sprite with variant_direction format
    shadow_filename = f"{shadow_base}_{variant}_{direction_row}"
    shadow_sprite = image_resolver(f"character/{shadow_filename}", False)

    if not shadow_sprite:
        shadow_sprite = image_resolver(shadow_filename, False)

    # Some shadows might be in separate files with -1, -2 suffixes
    if not shadow_sprite:
        # Try with -1 suffix
        shadow_base_1 = shadow_base.replace("_shadow", "_shadow-1")
        shadow_filename = f"{shadow_base_1}_{variant}_{direction_row}.png"
        shadow_sprite = image_resolver(f"character/{shadow_filename}", False)

        if not shadow_sprite:
            shadow_sprite = image_resolver(shadow_filename, False)

    return shadow_sprite


def get_key(entity: Dict, grid) -> str:
    """Get cache key for character."""
    direction = entity.get("direction", 0)
    state = entity.get("state", "idle")
    level = entity.get("level", 1)
    has_gun = entity.get("has_gun", False)
    animation_frame = entity.get("animation_frame", 0)
    color = entity.get("color", DEFAULT_PLAYER_COLOR)

    color_str = f"{color[0]}_{color[1]}_{color[2]}"
    return f"{direction}_{state}_{level}_{has_gun}_{animation_frame}_{color_str}"


def get_size(entity: Dict) -> Tuple[float, float]:
    """Character is effectively 1x1 for positioning."""
    return (1, 1)
