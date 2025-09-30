# renderers/decider_combinator.py
"""
Decider combinator renderer with display
"""

from typing import Dict, Tuple, Optional, Callable
from PIL import Image

DIRECTIONS = {0: "north", 2: "east", 4: "south", 6: "west"}

COMBINATOR_TO_NORMAL = {
    None: "empty",
    "+": "plus",
    "-": "minus",
    "*": "multiply",
    "/": "divide",
    "%": "modulo",
    "^": "power",
    "<<": "left_shift",
    ">>": "right_shift",
    "&": "and",
    "and": "and",
    "AND": "and",
    "|": "or",
    "or": "or",
    "OR": "or",
    "xor": "xor",
    "XOR": "xor",
    ">": "gt",
    "<": "lt",
    "=": "eq",
    "!=": "neq",
    "≠": "neq",
    ">=": "gte",
    "≥": "gte",
    "<=": "lte",
    "≤": "lte",
}


def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render decider combinator with display"""
    direction = entity.get("direction", 0)
    base = image_resolver(f"{entity['name']}_{DIRECTIONS[direction]}")

    if base is None:
        return None

    # Check for control behavior
    control = entity.get("control_behavior", {})
    conditions = control.get("decider_conditions", {})
    comparator = conditions.get("comparator")

    if comparator is None:
        return base

    # Create a copy to modify
    result = base.copy()
    display_name = COMBINATOR_TO_NORMAL.get(comparator, "empty")
    icon = image_resolver(f"display_{display_name}")

    if icon:
        # Position based on direction
        if direction in [0, 4]:
            x, y = 36, 22
        else:
            x, y = 36, 18

        result.paste(icon, (x, y), icon if icon.mode == "RGBA" else None)

    return result


def render_shadow(
    entity: Dict, grid, image_resolver: Callable
) -> Optional[Image.Image]:
    """Decider combinators have no shadows"""
    return None


def get_key(entity: Dict, grid) -> str:
    """Get cache key including comparator"""
    direction = entity.get("direction", 0)
    control = entity.get("control_behavior", {})
    conditions = control.get("decider_conditions", {})
    comparator = conditions.get("comparator", "")

    if comparator:
        return f"{direction}_{comparator}"
    return str(direction)


def get_size(entity: Dict) -> Tuple[float, float]:
    """Get size based on direction"""
    direction = entity.get("direction", 0)
    if direction in [2, 6]:  # East/West
        return (2, 1)
    else:  # North/South
        return (1, 2)
