"""Bounding box utilities for VQA tasks."""

from typing import Dict, Tuple, Any


def calculate_blueprint_bounding_box(blueprint: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate the bounding box of a blueprint from its entities.

    Args:
        blueprint: Blueprint dictionary containing entities

    Returns:
        Dictionary with min_x, min_y, max_x, max_y, width, height
    """
    entities = blueprint.get("entities", [])

    if not entities:
        return {
            "min_x": 0.0,
            "min_y": 0.0,
            "max_x": 0.0,
            "max_y": 0.0,
            "width": 0.0,
            "height": 0.0,
        }

    # Extract all positions
    x_coords = []
    y_coords = []

    for entity in entities:
        position = entity.get("position", {})
        x = position.get("x", 0)
        y = position.get("y", 0)
        x_coords.append(x)
        y_coords.append(y)

    # Calculate bounding box
    min_x = min(x_coords)
    max_x = max(x_coords)
    min_y = min(y_coords)
    max_y = max(y_coords)

    # Calculate dimensions
    width = max_x - min_x
    height = max_y - min_y

    return {
        "min_x": min_x,
        "min_y": min_y,
        "max_x": max_x,
        "max_y": max_y,
        "width": width,
        "height": height,
    }


def get_blueprint_center(bounding_box: Dict[str, float]) -> Tuple[float, float]:
    """
    Get the center point of a bounding box.

    Args:
        bounding_box: Bounding box dictionary

    Returns:
        Tuple of (center_x, center_y)
    """
    center_x = (bounding_box["min_x"] + bounding_box["max_x"]) / 2
    center_y = (bounding_box["min_y"] + bounding_box["max_y"]) / 2
    return (center_x, center_y)


def is_position_in_bounds(
    x: float, y: float, bounding_box: Dict[str, float], margin: float = 0.0
) -> bool:
    """
    Check if a position is within the bounding box (with optional margin).

    Args:
        x: X coordinate
        y: Y coordinate
        bounding_box: Bounding box dictionary
        margin: Optional margin to expand the bounding box

    Returns:
        True if position is within bounds
    """
    return (
        bounding_box["min_x"] - margin <= x <= bounding_box["max_x"] + margin
        and bounding_box["min_y"] - margin <= y <= bounding_box["max_y"] + margin
    )


def get_relative_position_description(
    x: float, y: float, bounding_box: Dict[str, float]
) -> str:
    """
    Get a relative position description within the bounding box.

    Args:
        x: X coordinate
        y: Y coordinate
        bounding_box: Bounding box dictionary

    Returns:
        String description like "northwest", "center", "southeast", etc.
    """
    center_x, center_y = get_blueprint_center(bounding_box)

    # Determine horizontal position
    if x < center_x - bounding_box["width"] * 0.1:
        horizontal = "west"
    elif x > center_x + bounding_box["width"] * 0.1:
        horizontal = "east"
    else:
        horizontal = "center"

    # Determine vertical position
    if y < center_y - bounding_box["height"] * 0.1:
        vertical = "north"
    elif y > center_y + bounding_box["height"] * 0.1:
        vertical = "south"
    else:
        vertical = "center"

    # Combine descriptions
    if horizontal == "center" and vertical == "center":
        return "center"
    elif horizontal == "center":
        return vertical
    elif vertical == "center":
        return horizontal
    else:
        return f"{vertical}{horizontal}"


def format_bounding_box_info(bounding_box: Dict[str, float]) -> str:
    """
    Format bounding box information as a readable string.

    Args:
        bounding_box: Bounding box dictionary

    Returns:
        Formatted string with bounding box information
    """
    return (
        f"Bounds: ({bounding_box['min_x']:.1f}, {bounding_box['min_y']:.1f}) to "
        f"({bounding_box['max_x']:.1f}, {bounding_box['max_y']:.1f}), "
        f"Size: {bounding_box['width']:.1f}×{bounding_box['height']:.1f}"
    )
