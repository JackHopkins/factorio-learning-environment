"""Blueprint transformation utilities for data augmentation using flips instead of rotations."""

import copy
from typing import Dict, Any, List, Tuple, Set, Optional
from enum import Enum


class FlipType(Enum):
    """Types of flips for blueprint transformations."""

    NONE = "none"  # Original orientation
    HORIZONTAL = "horizontal"  # Flip along Y-axis (X = -X)
    VERTICAL = "vertical"  # Flip along X-axis (Y = -Y)
    BOTH = "both"  # Flip both axes (X = -X, Y = -Y)


class DirectionSystem(Enum):
    """Factorio direction systems."""

    OLD_SYSTEM = "old"  # 8-direction system (0-7)
    NEW_SYSTEM = "new"  # 16-direction system (0-15)


def detect_direction_system(blueprint: Dict[str, Any]) -> DirectionSystem:
    """
    Detect which direction system a blueprint uses by analyzing entity directions.

    The old system uses values 0-7, while the new system uses 0-15.

    Args:
        blueprint: Blueprint dictionary

    Returns:
        DirectionSystem enum indicating which system is in use
    """
    if "entities" not in blueprint:
        return DirectionSystem.OLD_SYSTEM  # Default to old system if no entities

    directions_found: Set[int] = set()

    for entity in blueprint["entities"]:
        if "direction" in entity and entity["direction"] is not None:
            direction = int(entity["direction"])
            directions_found.add(direction)

    # If any direction >= 8, it's definitely the new system
    if any(d >= 8 for d in directions_found):
        return DirectionSystem.NEW_SYSTEM

    # If all directions are 0-7, assume old system
    return DirectionSystem.OLD_SYSTEM


def flip_direction_old_system(direction: int, flip_type: FlipType) -> int:
    """
    Flip a direction in the old 8-direction system.

    Old system directions:
    - 0: North
    - 1: Northeast
    - 2: East
    - 3: Southeast
    - 4: South
    - 5: Southwest
    - 6: West
    - 7: Northwest
    """
    if direction is None or flip_type == FlipType.NONE:
        return direction

    # Map directions for different flip types
    horizontal_flip_map = {
        0: 0,  # North -> North
        1: 7,  # Northeast -> Northwest
        2: 6,  # East -> West
        3: 5,  # Southeast -> Southwest
        4: 4,  # South -> South
        5: 3,  # Southwest -> Southeast
        6: 2,  # West -> East
        7: 1,  # Northwest -> Northeast
    }

    vertical_flip_map = {
        0: 4,  # North -> South
        1: 3,  # Northeast -> Southeast
        2: 2,  # East -> East
        3: 1,  # Southeast -> Northeast
        4: 0,  # South -> North
        5: 7,  # Southwest -> Northwest
        6: 6,  # West -> West
        7: 5,  # Northwest -> Southwest
    }

    both_flip_map = {
        0: 4,  # North -> South
        1: 5,  # Northeast -> Southwest
        2: 6,  # East -> West
        3: 7,  # Southeast -> Northwest
        4: 0,  # South -> North
        5: 1,  # Southwest -> Northeast
        6: 2,  # West -> East
        7: 3,  # Northwest -> Southeast
    }

    if flip_type == FlipType.HORIZONTAL:
        return horizontal_flip_map.get(direction, direction)
    elif flip_type == FlipType.VERTICAL:
        return vertical_flip_map.get(direction, direction)
    elif flip_type == FlipType.BOTH:
        return both_flip_map.get(direction, direction)

    return direction


def flip_direction_new_system(direction: int, flip_type: FlipType) -> int:
    """
    Flip a direction in the new 16-direction system.

    New system uses 16 directions (0-15) representing 22.5° increments.
    """
    if direction is None or flip_type == FlipType.NONE:
        return direction

    # For horizontal flip (X = -X), we mirror across the Y-axis
    # For vertical flip (Y = -Y), we mirror across the X-axis

    if flip_type == FlipType.HORIZONTAL:
        # Mirror across Y-axis: East <-> West
        horizontal_flip_map = {
            0: 0,  # N -> N
            1: 15,  # NNE -> NNW
            2: 14,  # NE -> NW
            3: 13,  # ENE -> WNW
            4: 12,  # E -> W
            5: 11,  # ESE -> WSW
            6: 10,  # SE -> SW
            7: 9,  # SSE -> SSW
            8: 8,  # S -> S
            9: 7,  # SSW -> SSE
            10: 6,  # SW -> SE
            11: 5,  # WSW -> ESE
            12: 4,  # W -> E
            13: 3,  # WNW -> ENE
            14: 2,  # NW -> NE
            15: 1,  # NNW -> NNE
        }
        return horizontal_flip_map.get(direction, direction)

    elif flip_type == FlipType.VERTICAL:
        # Mirror across X-axis: North <-> South
        vertical_flip_map = {
            0: 8,  # N -> S
            1: 7,  # NNE -> SSE
            2: 6,  # NE -> SE
            3: 5,  # ENE -> ESE
            4: 4,  # E -> E
            5: 3,  # ESE -> ENE
            6: 2,  # SE -> NE
            7: 1,  # SSE -> NNE
            8: 0,  # S -> N
            9: 15,  # SSW -> NNW
            10: 14,  # SW -> NW
            11: 13,  # WSW -> WNW
            12: 12,  # W -> W
            13: 11,  # WNW -> WSW
            14: 10,  # NW -> SW
            15: 9,  # NNW -> SSW
        }
        return vertical_flip_map.get(direction, direction)

    elif flip_type == FlipType.BOTH:
        # 180-degree rotation equivalent
        vertical_flip_direction = flip_direction_new_system(
            direction, FlipType.VERTICAL
        )
        final_direction = flip_direction_new_system(
            vertical_flip_direction, FlipType.HORIZONTAL
        )
        return final_direction

    return direction


def flip_direction(
    direction: Optional[int], flip_type: FlipType, direction_system: DirectionSystem
) -> Optional[int]:
    """
    Flip a Factorio direction value using the appropriate system.

    Args:
        direction: Original direction value
        flip_type: Type of flip to apply
        direction_system: Which direction system to use

    Returns:
        New direction value
    """
    if direction is None:
        return None

    # Handle both int and float directions
    original_type = type(direction)
    direction_int = int(direction)

    if direction_system == DirectionSystem.OLD_SYSTEM:
        new_direction = flip_direction_old_system(direction_int, flip_type)
    else:
        new_direction = flip_direction_new_system(direction_int, flip_type)

    # Return in original type
    return original_type(new_direction) if original_type is float else new_direction


def get_blueprint_bounds(
    entities: List[Dict[str, Any]],
) -> Tuple[float, float, float, float]:
    """
    Get the bounding box of all entities in the blueprint.

    Args:
        entities: List of blueprint entities

    Returns:
        Tuple of (min_x, min_y, max_x, max_y)
    """
    if not entities:
        return 0, 0, 0, 0

    positions = []
    for entity in entities:
        pos = entity.get("position", {})
        x, y = pos.get("x", 0), pos.get("y", 0)
        positions.append((x, y))

    xs, ys = zip(*positions)
    return min(xs), min(ys), max(xs), max(ys)


def normalize_blueprint_positions(
    entities: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Normalize blueprint positions so the bounding box starts near (0, 0).

    Args:
        entities: List of blueprint entities

    Returns:
        List of entities with normalized positions
    """
    if not entities:
        return entities

    # Get current bounds
    min_x, min_y, max_x, max_y = get_blueprint_bounds(entities)

    # Calculate offset to move blueprint close to origin
    offset_x = -min_x
    offset_y = -min_y

    # Apply offset to all entities
    normalized_entities = []
    for entity in entities:
        new_entity = copy.deepcopy(entity)
        pos = new_entity.get("position", {})

        new_entity["position"] = {
            "x": pos.get("x", 0) + offset_x,
            "y": pos.get("y", 0) + offset_y,
        }

        normalized_entities.append(new_entity)

    return normalized_entities


def should_swap_underground_belt_type(
    entity: Dict[str, Any], flip_type: FlipType, direction_system: DirectionSystem
) -> bool:
    """
    Determine if an underground belt's type should be swapped based on flip type and direction.

    Underground belts need their type swapped when:
    1. BOTH flip (always swap - 180 degree rotation)
    2. Flipping along the axis the belt pair extends along

    Args:
        entity: The underground belt entity
        flip_type: Type of flip being applied
        direction_system: Which direction system is in use

    Returns:
        True if the belt type should be swapped
    """
    if flip_type == FlipType.BOTH:
        # Always swap for 180-degree equivalent
        return True

    if flip_type == FlipType.NONE:
        return False

    direction = entity.get("direction", 0)
    if direction is None:
        direction = 0
    direction = int(direction)

    # Determine which axis the belt extends along based on direction
    if direction_system == DirectionSystem.OLD_SYSTEM:
        # In old system: 0=N, 2=E, 4=S, 6=W
        north_south = direction in [0, 4]  # Belt extends vertically
        east_west = direction in [2, 6]  # Belt extends horizontally
    else:
        # In new system: 0=N, 4=E, 8=S, 12=W
        north_south = direction in [0, 8]  # Belt extends vertically
        east_west = direction in [4, 12]  # Belt extends horizontally

    # Swap if:
    # - Horizontal flip and belt extends horizontally (E-W)
    # - Vertical flip and belt extends vertically (N-S)
    if flip_type == FlipType.HORIZONTAL and east_west:
        return True
    elif flip_type == FlipType.VERTICAL and north_south:
        return True

    return False


def flip_entity(
    entity: Dict[str, Any],
    flip_type: FlipType,
    center_x: float,
    center_y: float,
    direction_system: DirectionSystem,
) -> Dict[str, Any]:
    """Flip a single entity with special handling for different entity types."""
    new_entity = copy.deepcopy(entity)
    entity_name = entity.get("name", "")

    # Get original position
    pos = entity.get("position", {})
    x = pos.get("x", 0)
    y = pos.get("y", 0)

    # Apply flip transformation
    if flip_type == FlipType.HORIZONTAL:
        # Flip X coordinate around center
        new_x = center_x - (x - center_x)
        new_y = y
    elif flip_type == FlipType.VERTICAL:
        # Flip Y coordinate around center
        new_x = x
        new_y = center_y - (y - center_y)
    elif flip_type == FlipType.BOTH:
        # Flip both coordinates
        new_x = center_x - (x - center_x)
        new_y = center_y - (y - center_y)
    else:
        new_x = x
        new_y = y

    new_entity["position"] = {"x": new_x, "y": new_y}

    # Handle direction flipping
    if "direction" in entity and entity["direction"] is not None:
        new_entity["direction"] = flip_direction(
            entity["direction"], flip_type, direction_system
        )

    # Special handling for underground belts
    if "underground-belt" in entity_name:
        if should_swap_underground_belt_type(entity, flip_type, direction_system):
            # new_entity["type"] = "output" if belt_type == "input" else "input"
            pass

    return new_entity


def flip_blueprint(
    input_blueprint: Dict[str, Any],
    flip_type: FlipType,
    direction_system: Optional[DirectionSystem] = None,
) -> Dict[str, Any]:
    """
    Flip a blueprint by the specified type.

    Args:
        input_blueprint: Original blueprint
        flip_type: Type of flip to apply
        direction_system: Direction system to use (auto-detected if None)

    Returns:
        Flipped blueprint
    """
    blueprint = copy.deepcopy(input_blueprint)

    # Auto-detect direction system if not specified
    if direction_system is None:
        direction_system = detect_direction_system(blueprint)

    # Fill in empty directions with default (0)
    if "entities" in blueprint:
        for entity in blueprint["entities"]:
            if "direction" not in entity:
                entity["direction"] = 0

    if flip_type == FlipType.NONE:
        flipped_blueprint = copy.deepcopy(blueprint)
        if "entities" in flipped_blueprint:
            flipped_blueprint["entities"] = normalize_blueprint_positions(
                flipped_blueprint["entities"]
            )
        return flipped_blueprint

    flipped_blueprint = copy.deepcopy(blueprint)

    if "entities" not in flipped_blueprint:
        return flipped_blueprint

    entities = flipped_blueprint["entities"]

    # Get center of blueprint for flipping
    min_x, min_y, max_x, max_y = get_blueprint_bounds(entities)
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    # Flip each entity
    flipped_entities = []
    for entity in entities:
        flipped_entity = flip_entity(
            entity, flip_type, center_x, center_y, direction_system
        )
        flipped_entities.append(flipped_entity)

    # Normalize positions to keep blueprint near origin
    flipped_entities = normalize_blueprint_positions(flipped_entities)
    flipped_blueprint["entities"] = flipped_entities

    # Add metadata about the flip and direction system used
    if "metadata" not in flipped_blueprint:
        flipped_blueprint["metadata"] = {}
    flipped_blueprint["metadata"]["flip_type"] = flip_type.value
    flipped_blueprint["metadata"]["direction_system"] = direction_system.value

    if direction_system == DirectionSystem.NEW_SYSTEM:
        n_entities = []
        for entity in flipped_entities:
            if entity["direction"] == 12:
                entity["direction"] = 6
            elif entity["direction"] == 8:
                entity["direction"] = 4
            elif entity["direction"] == 4:
                entity["direction"] = 2
            else:
                entity["direction"] = 0
            n_entities.append(entity)
        flipped_blueprint["entities"] = n_entities

    return flipped_blueprint


def generate_flipped_blueprints(
    blueprint: Dict[str, Any], direction_system: Optional[DirectionSystem] = None
) -> Dict[FlipType, Dict[str, Any]]:
    """
    Generate all 4 flipped variations of a blueprint.

    Args:
        blueprint: Original blueprint dictionary
        direction_system: Direction system to use (auto-detected if None)

    Returns:
        Dictionary mapping flip type to flipped blueprint
    """
    # Auto-detect direction system if not specified
    if direction_system is None:
        direction_system = detect_direction_system(blueprint)

    flipped_blueprints = {}

    for flip_type in FlipType:
        flipped_blueprints[flip_type] = flip_blueprint(
            blueprint, flip_type, direction_system
        )

    return flipped_blueprints


def get_flip_suffix(flip_type: FlipType) -> str:
    """
    Get a string suffix for the flip type.

    Args:
        flip_type: FlipType enum value

    Returns:
        String suffix like "original", "h_flip", etc.
    """
    suffix_map = {
        FlipType.NONE: "original",
        FlipType.HORIZONTAL: "h_flip",
        FlipType.VERTICAL: "v_flip",
        FlipType.BOTH: "hv_flip",
    }
    return suffix_map[flip_type]


def update_metadata_for_flip(
    metadata: Dict[str, Any], flip_type: FlipType, direction_system: DirectionSystem
) -> Dict[str, Any]:
    """
    Update metadata to reflect the flip applied.

    Args:
        metadata: Original metadata dictionary
        flip_type: Applied flip type
        direction_system: Direction system used

    Returns:
        Updated metadata dictionary
    """
    updated_metadata = copy.deepcopy(metadata)

    # Add flip information
    updated_metadata["flip_type"] = flip_type.value
    updated_metadata["flip_suffix"] = get_flip_suffix(flip_type)
    updated_metadata["direction_system"] = direction_system.value

    # Update filename to include flip type
    if "filename" in updated_metadata:
        base_filename = updated_metadata["filename"]
        # Remove extension and add flip suffix
        if "." in base_filename:
            name, ext = base_filename.rsplit(".", 1)
            updated_metadata["filename"] = f"{name}_{get_flip_suffix(flip_type)}.{ext}"
        else:
            updated_metadata["filename"] = (
                f"{base_filename}_{get_flip_suffix(flip_type)}"
            )

    return updated_metadata


# Example usage and testing
if __name__ == "__main__":
    # Test with underground belts in different orientations
    underground_belt_test = {
        "entities": [
            # Horizontal underground belt pair (East-West)
            {
                "name": "underground-belt",
                "position": {"x": 0, "y": 0},
                "direction": 2,
                "type": "input",
            },  # East
            {
                "name": "underground-belt",
                "position": {"x": 5, "y": 0},
                "direction": 2,
                "type": "output",
            },  # East
            # Vertical underground belt pair (North-South)
            {
                "name": "underground-belt",
                "position": {"x": 0, "y": 2},
                "direction": 0,
                "type": "input",
            },  # North
            {
                "name": "underground-belt",
                "position": {"x": 0, "y": 7},
                "direction": 0,
                "type": "output",
            },  # North
        ]
    }

    print("Underground Belt Flip Test (Old System):")
    print("Original configuration:")
    for i, entity in enumerate(underground_belt_test["entities"]):
        print(
            f"  Entity {i}: pos=({entity['position']['x']}, {entity['position']['y']}), "
            f"dir={entity['direction']}, type={entity['type']}"
        )

    # Test each flip type
    for flip_type in FlipType:
        print(f"\n{flip_type.value} flip:")
        flipped = flip_blueprint(
            underground_belt_test, flip_type, DirectionSystem.OLD_SYSTEM
        )
        for i, entity in enumerate(flipped["entities"]):
            if "underground-belt" in entity["name"]:
                print(
                    f"  Entity {i}: pos=({entity['position']['x']:.1f}, {entity['position']['y']:.1f}), "
                    f"dir={entity['direction']}, type={entity['type']}"
                )

    # Test with new system directions
    print("\n" + "=" * 50 + "\n")
    underground_belt_test_new = {
        "entities": [
            # Horizontal underground belt pair (East-West)
            {
                "name": "underground-belt",
                "position": {"x": 0, "y": 0},
                "direction": 4,
                "type": "input",
            },  # East
            {
                "name": "underground-belt",
                "position": {"x": 5, "y": 0},
                "direction": 4,
                "type": "output",
            },  # East
            # Vertical underground belt pair (North-South)
            {
                "name": "underground-belt",
                "position": {"x": 0, "y": 2},
                "direction": 0,
                "type": "input",
            },  # North
            {
                "name": "underground-belt",
                "position": {"x": 0, "y": 7},
                "direction": 0,
                "type": "output",
            },  # North
        ]
    }

    print("Underground Belt Flip Test (New System):")
    print("Original configuration:")
    for i, entity in enumerate(underground_belt_test_new["entities"]):
        print(
            f"  Entity {i}: pos=({entity['position']['x']}, {entity['position']['y']}), "
            f"dir={entity['direction']}, type={entity['type']}"
        )

    # Test horizontal flip specifically
    print("\nHorizontal flip (should swap E-W belt types):")
    h_flipped = flip_blueprint(
        underground_belt_test_new, FlipType.HORIZONTAL, DirectionSystem.NEW_SYSTEM
    )
    for i, entity in enumerate(h_flipped["entities"]):
        if "underground-belt" in entity["name"]:
            print(
                f"  Entity {i}: pos=({entity['position']['x']:.1f}, {entity['position']['y']:.1f}), "
                f"dir={entity['direction']}, type={entity['type']}"
            )
