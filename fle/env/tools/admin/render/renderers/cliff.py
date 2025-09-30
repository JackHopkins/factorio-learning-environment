# renderers/cliff.py
"""
Cliff renderer using orientation data from server
"""

import random
from typing import Dict, Tuple, Optional, Callable
from PIL import Image


def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render cliff based on orientation from server"""
    orientation = get_orientation(entity)
    cliff_type = determine_cliff_type_from_orientation(orientation)

    sprite_name = get_cliff_sprite_name(cliff_type, orientation)
    return image_resolver(sprite_name)


def render_shadow(
    entity: Dict, grid, image_resolver: Callable
) -> Optional[Image.Image]:
    """Render cliff shadow"""
    orientation = get_orientation(entity)
    cliff_type = determine_cliff_type_from_orientation(orientation)

    sprite_name = get_cliff_sprite_name(cliff_type, orientation)
    return image_resolver(sprite_name, True)


def get_orientation(entity: Dict) -> str:
    """Extract orientation from entity data"""
    # Handle quoted string from Lua
    orientation = entity.get("cliff_orientation", "").strip('"')

    if not orientation:
        # Fallback to direction field if available
        if "direction" in entity:
            direction = str(entity["direction"]).strip('"')
            if direction and "-to-" in direction:
                orientation = direction

    return orientation or "west-to-east"


def determine_cliff_type_from_orientation(orientation: str) -> str:
    """
    Determine cliff type based on orientation pattern.

    In Factorio:
    - cliff-sides: Standard straight cliff pieces and basic corners
    - cliff-outer: Convex (outward) corners
    - cliff-inner: Concave (inward) corners
    - cliff-entrance: End pieces and special transitions
    """

    # Parse orientation
    from_dir, to_dir = parse_orientation(orientation)

    # Terminal pieces (one end is "none") -> entrance
    if from_dir == "none" or to_dir == "none":
        return "cliff-entrance"

    # Analyze the turn angle to determine corner type
    direction_order = ["north", "east", "south", "west"]

    if from_dir in direction_order and to_dir in direction_order:
        from_idx = direction_order.index(from_dir)
        to_idx = direction_order.index(to_dir)

        # Calculate turn direction and angle
        turn = (to_idx - from_idx) % 4

        if turn == 0:
            # Same direction - shouldn't happen
            return "cliff-sides"
        elif turn == 2:
            # Opposite directions - straight cliff
            return "cliff-sides"
        elif turn == 1:
            # 90-degree right turn - outer corner
            return "cliff-outer"
        elif turn == 3:
            # 90-degree left turn (270 right) - inner corner
            return "cliff-inner"

    # Default to sides for any unhandled cases
    return "cliff-sides"


def parse_orientation(orientation: str) -> Tuple[str, str]:
    """Parse orientation string into from and to directions"""
    parts = orientation.split("-to-")
    if len(parts) == 2:
        return parts[0], parts[1]
    return "west", "east"


def get_cliff_sprite_name(cliff_type: str, orientation: str) -> str:
    """
    Map cliff orientation to sprite name based on the cliff type.

    Each cliff type has different sprite organization:
    - cliff-sides: 8x4 grid - main cliff pieces
    - cliff-inner: 8x2 grid - inner corners
    - cliff-outer: 8x2 grid - outer corners
    - cliff-entrance: 4x4 grid - terminals and special pieces
    """

    if cliff_type == "cliff-entrance":
        # cliff-entrance uses a 4x4 layout
        orientation_map = {
            # Terminal pieces (where cliffs end/start)
            "none-to-east": (1, 4),  # 1-2 -> 4
            "west-to-none": (3, 4),  # 3-4 -> 4
            "none-to-south": (1, 1),  # 1-2 -> 1
            "north-to-none": (3, 1),  # 3-4 -> 1
            "none-to-west": (1, 2),  # 1-2 -> 2
            "east-to-none": (3, 2),  # 3-4 -> 2
            "none-to-north": (1, 3),  # 1,2 -> 3
            "south-to-none": (3, 3),  # 3,4 -> 3
        }
        row, col = orientation_map.get(orientation, (1, 1))
        return f"{cliff_type}_{row}_{col}"

    elif cliff_type == "cliff-outer":
        # Outer corners - 90 degree right turns
        orientation_map = {
            "west-to-north": 2,
            "north-to-east": 1,
            "east-to-south": 2,
            "south-to-west": 1,
        }

    elif cliff_type == "cliff-inner":
        # Inner corners - 90 degree left turns
        orientation_map = {
            "west-to-south": 2,
            "south-to-east": 1,
            "east-to-north": 2,
            "north-to-west": 1,
        }

    else:  # cliff-sides
        # Main cliff pieces and basic transitions
        orientation_map = {
            "north-to-south": 1,  # Horizontal cliff facing down
            "west-to-east": 2,  # Vertical cliff facing right
            "east-to-west": 4,  # Vertical cliff facing left
            "south-to-north": 3,  # Horizontal cliff facing up
        }

    # Get the mapping with fallback
    row = orientation_map.get(orientation, 1)

    # # Ensure we stay within bounds for each cliff type
    # if cliff_type == 'cliff-inner' and row > 2:
    #     row = 2
    # elif cliff_type == 'cliff-outer' and row > 2:
    #     row = 2
    # elif cliff_type == 'cliff-entrance' and (col > 4 or row > 4):
    #     col = min(col, 4)
    #     row = min(row, 4)
    # elif cliff_type == 'cliff-sides' and row > 4:
    #     row = 4

    variant = random.choice([1, 2, 3, 4])
    return f"{cliff_type}_{variant}_{row}"


def get_key(entity: Dict, grid) -> str:
    """Get cache key"""
    orientation = get_orientation(entity)
    cliff_type = determine_cliff_type_from_orientation(orientation)
    return f"{cliff_type}_{orientation}"


def get_size(entity: Dict) -> Tuple[float, float]:
    """Get cliff size"""
    return (2, 2)
