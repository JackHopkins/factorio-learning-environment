# renderers/pipe.py
"""
Pipe renderer with connection logic
"""

from typing import Dict, Tuple, Optional, Callable, List
from PIL import Image

# Direction constants (Factorio 8-way direction system: 0=N, 2=E, 4=S, 6=W)
NORTH = 0
EAST = 2
SOUTH = 4
WEST = 6

# Entities that have fluid connection points
FLUID_HANDLER_ENTITIES = {
    "boiler",
    "heat-exchanger",
    "steam-engine",
    "steam-turbine",
    "chemical-plant",
    "oil-refinery",
    "pumpjack",
    "storage-tank",
    "pump",
    "assembling-machine-2",
    "assembling-machine-3",
}


def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render pipe based on connections"""
    around = get_around(entity, grid)
    count = sum(around)

    image_name = None

    if count == 0:
        image_name = "pipe_straight_horizontal"
    elif count == 1:
        if around[0] == 1:
            image_name = "pipe_ending_up"
        elif around[1] == 1:
            image_name = "pipe_ending_right"
        elif around[2] == 1:
            image_name = "pipe_ending_down"
        else:
            image_name = "pipe_ending_left"
    elif count == 2:
        if around[0] == 1:
            if around[1] == 1:
                image_name = "pipe_corner_up_right"
            elif around[2] == 1:
                image_name = "pipe_straight_vertical"
            elif around[3] == 1:
                image_name = "pipe_corner_up_left"
        elif around[1] == 1:
            if around[2] == 1:
                image_name = "pipe_corner_down_right"
            elif around[3] == 1:
                image_name = "pipe_straight_horizontal"
        else:
            image_name = "pipe_corner_down_left"
    elif count == 3:
        if around[0] == 0:
            image_name = "pipe_t_down"
        elif around[1] == 0:
            image_name = "pipe_t_left"
        elif around[2] == 0:
            image_name = "pipe_t_up"
        elif around[3] == 0:
            image_name = "pipe_t_right"
    else:
        image_name = "pipe_cross"

    return image_resolver(image_name)


def render_shadow(
    entity: Dict, grid, image_resolver: Callable
) -> Optional[Image.Image]:
    """Pipes have no shadows"""
    return None


def get_key(entity: Dict, grid) -> str:
    """Get cache key based on connections"""
    around = get_around(entity, grid)
    return "_".join(map(str, around))


def get_around(entity: Dict, grid) -> list:
    """Check surrounding pipe connections"""
    pipe_x = grid.center_x
    pipe_y = grid.center_y

    return [
        # North
        is_pipe(grid.get_relative(0, -1), SOUTH)
        or is_entity_in_direction(grid.get_relative(0, -1), "offshore-pump", NORTH)
        or has_fluid_connection_at(grid, pipe_x, pipe_y, 0, -1),
        # East
        is_pipe(grid.get_relative(1, 0), WEST)
        or is_entity_in_direction(grid.get_relative(1, 0), "offshore-pump", EAST)
        or has_fluid_connection_at(grid, pipe_x, pipe_y, 1, 0),
        # South
        is_pipe(grid.get_relative(0, 1), NORTH)
        or is_entity_in_direction(grid.get_relative(0, 1), "offshore-pump", SOUTH)
        or has_fluid_connection_at(grid, pipe_x, pipe_y, 0, 1),
        # West
        is_pipe(grid.get_relative(-1, 0), EAST)
        or is_entity_in_direction(grid.get_relative(-1, 0), "offshore-pump", WEST)
        or has_fluid_connection_at(grid, pipe_x, pipe_y, -1, 0),
    ]


def has_fluid_connection_at(
    grid, pipe_x: float, pipe_y: float, dx: int, dy: int
) -> int:
    """
    Check if there's a fluid handler entity with a connection point at the pipe's position.

    We need to search in a wider area because fluid handlers like boilers span multiple tiles.
    The connection point of a boiler might be adjacent to our pipe, but the boiler's center
    position could be several tiles away.
    """
    # Search in a wider area to find multi-tile entities
    search_radius = 4
    for search_dy in range(-search_radius, search_radius + 1):
        for search_dx in range(-search_radius, search_radius + 1):
            nearby_entity = grid.get_relative(search_dx, search_dy)
            if nearby_entity is None:
                continue

            entity_name = nearby_entity.get("name", "")
            if entity_name not in FLUID_HANDLER_ENTITIES:
                continue

            # Get connection points for this entity
            connection_points = get_entity_connection_points(nearby_entity)

            # Check if the pipe position matches any connection point
            for conn_point in connection_points:
                # Connection points are relative to entity position, need to convert
                conn_x = conn_point[0]
                conn_y = conn_point[1]

                # Check if this connection point is adjacent to our pipe in the direction we're checking
                if abs(conn_x - pipe_x) < 0.6 and abs(conn_y - pipe_y) < 0.6:
                    # The connection point is at or very close to the pipe position
                    # Now check if the direction from pipe to connection point matches dx, dy
                    # This means the pipe should show a connection in that direction
                    return 1

    return 0


def get_entity_connection_points(entity: Dict) -> List[Tuple[float, float]]:
    """
    Get the fluid connection points for a fluid handler entity.
    Returns a list of (x, y) absolute positions where pipes can connect.
    """
    name = entity.get("name", "")
    pos = entity.get("position", {})
    x = pos.get("x", 0)
    y = pos.get("y", 0)
    direction = entity.get("direction", 0)

    # Handle connection_points from entity data if available
    if "connection_points" in entity and entity["connection_points"]:
        conn_points = entity["connection_points"]
        result = []
        for cp in conn_points:
            if isinstance(cp, dict):
                result.append((cp.get("x", 0), cp.get("y", 0)))
            elif isinstance(cp, (list, tuple)) and len(cp) >= 2:
                result.append((cp[0], cp[1]))
        if result:
            return result

    # Fall back to calculated connection points based on entity type and direction
    if name == "boiler" or name == "heat-exchanger":
        return get_boiler_connection_points(x, y, direction)
    elif name == "steam-engine":
        return get_steam_engine_connection_points(x, y, direction)
    elif name == "steam-turbine":
        return get_steam_turbine_connection_points(x, y, direction)
    elif name == "chemical-plant":
        return get_chemical_plant_connection_points(x, y, direction)
    elif name == "oil-refinery":
        return get_refinery_connection_points(x, y, direction)
    elif name == "pumpjack":
        return get_pumpjack_connection_points(x, y, direction)
    elif name == "storage-tank":
        return get_storage_tank_connection_points(x, y, direction)
    elif name == "pump":
        return get_pump_connection_points(x, y, direction)
    elif name in ("assembling-machine-2", "assembling-machine-3"):
        return get_assembling_machine_connection_points(x, y, direction)

    return []


def get_boiler_connection_points(
    x: float, y: float, direction: int
) -> List[Tuple[float, float]]:
    """Get boiler connection points based on direction."""
    # Boiler is 3x2 when facing N/S, 2x3 when facing E/W
    # Has 2 water inputs and 1 steam output
    if direction == NORTH:
        return [
            (x + 1.5, y + 0.5),  # Water input right
            (x - 1.5, y + 0.5),  # Water input left
            (x, y - 0.5),  # Steam output top
        ]
    elif direction == SOUTH:
        return [
            (x + 1.5, y - 0.5),  # Water input right
            (x - 1.5, y - 0.5),  # Water input left
            (x, y + 0.5),  # Steam output bottom
        ]
    elif direction == EAST:
        return [
            (x - 0.5, y + 1.5),  # Water input bottom
            (x - 0.5, y - 1.5),  # Water input top
            (x + 0.5, y),  # Steam output right
        ]
    elif direction == WEST:
        return [
            (x + 0.5, y + 1.5),  # Water input bottom
            (x + 0.5, y - 1.5),  # Water input top
            (x - 0.5, y),  # Steam output left
        ]
    return []


def get_steam_engine_connection_points(
    x: float, y: float, direction: int
) -> List[Tuple[float, float]]:
    """Get steam engine connection points based on direction."""
    # Steam engine is 3x5 when vertical, 5x3 when horizontal
    # Has 2 fluid connections on opposite ends
    if direction == NORTH or direction == SOUTH:
        # Vertical orientation
        return [
            (x, y - 2),  # Top connection
            (x, y + 2),  # Bottom connection
        ]
    else:
        # Horizontal orientation (EAST or WEST)
        return [
            (x - 2, y),  # Left connection
            (x + 2, y),  # Right connection
        ]


def get_steam_turbine_connection_points(
    x: float, y: float, direction: int
) -> List[Tuple[float, float]]:
    """Get steam turbine connection points based on direction."""
    # Steam turbine is similar to steam engine but larger (3x5)
    if direction == NORTH or direction == SOUTH:
        return [
            (x, y - 2.5),
            (x, y + 2.5),
        ]
    else:
        return [
            (x - 2.5, y),
            (x + 2.5, y),
        ]


def get_chemical_plant_connection_points(
    x: float, y: float, direction: int
) -> List[Tuple[float, float]]:
    """Get chemical plant connection points based on direction."""
    # Chemical plant is 3x3 with 4 connection points
    if direction == NORTH:
        return [
            (x - 1, y + 1.5),  # Input left
            (x + 1, y + 1.5),  # Input right
            (x - 1, y - 1.5),  # Output left
            (x + 1, y - 1.5),  # Output right
        ]
    elif direction == SOUTH:
        return [
            (x - 1, y - 1.5),
            (x + 1, y - 1.5),
            (x - 1, y + 1.5),
            (x + 1, y + 1.5),
        ]
    elif direction == EAST:
        return [
            (x - 1.5, y - 1),
            (x - 1.5, y + 1),
            (x + 1.5, y - 1),
            (x + 1.5, y + 1),
        ]
    elif direction == WEST:
        return [
            (x + 1.5, y - 1),
            (x + 1.5, y + 1),
            (x - 1.5, y - 1),
            (x - 1.5, y + 1),
        ]
    return []


def get_refinery_connection_points(
    x: float, y: float, direction: int
) -> List[Tuple[float, float]]:
    """Get oil refinery connection points based on direction."""
    # Oil refinery is 5x5 with multiple connection points
    if direction == NORTH:
        return [
            (x + 1, y + 3),
            (x - 1, y + 3),
            (x, y + 3),  # Inputs
            (x - 2, y - 3),
            (x - 1, y - 3),
            (x, y - 3),
            (x + 1, y - 3),
            (x + 2, y - 3),  # Outputs
        ]
    elif direction == SOUTH:
        return [
            (x + 1, y - 3),
            (x - 1, y - 3),
            (x, y - 3),
            (x - 2, y + 3),
            (x - 1, y + 3),
            (x, y + 3),
            (x + 1, y + 3),
            (x + 2, y + 3),
        ]
    elif direction == EAST:
        return [
            (x - 3, y + 1),
            (x - 3, y),
            (x - 3, y - 1),
            (x + 3, y - 2),
            (x + 3, y - 1),
            (x + 3, y),
            (x + 3, y + 1),
            (x + 3, y + 2),
        ]
    elif direction == WEST:
        return [
            (x + 3, y + 1),
            (x + 3, y),
            (x + 3, y - 1),
            (x - 3, y - 2),
            (x - 3, y - 1),
            (x - 3, y),
            (x - 3, y + 1),
            (x - 3, y + 2),
        ]
    return []


def get_pumpjack_connection_points(
    x: float, y: float, direction: int
) -> List[Tuple[float, float]]:
    """Get pumpjack connection point based on direction."""
    if direction == NORTH:
        return [(x + 1, y - 2)]
    elif direction == EAST:
        return [(x + 2, y - 1)]
    elif direction == SOUTH:
        return [(x - 1, y + 2)]
    elif direction == WEST:
        return [(x - 2, y + 1)]
    return []


def get_storage_tank_connection_points(
    x: float, y: float, direction: int
) -> List[Tuple[float, float]]:
    """Get storage tank connection points based on direction."""
    # Storage tank is 3x3 with 4 connection points
    if direction == EAST or direction == WEST:
        return [
            (x + 1, y - 2),
            (x + 2, y - 1),  # Top right
            (x - 1, y + 2),
            (x - 2, y + 1),  # Bottom left
        ]
    else:
        return [
            (x - 1, y - 2),
            (x - 2, y - 1),  # Top left
            (x + 1, y + 2),
            (x + 2, y + 1),  # Bottom right
        ]


def get_pump_connection_points(
    x: float, y: float, direction: int
) -> List[Tuple[float, float]]:
    """Get pump connection points based on direction."""
    # Pump is 1x2 with connections on both ends
    if direction == NORTH:
        return [(x, y - 1), (x, y + 1)]
    elif direction == SOUTH:
        return [(x, y + 1), (x, y - 1)]
    elif direction == EAST:
        return [(x + 1, y), (x - 1, y)]
    elif direction == WEST:
        return [(x - 1, y), (x + 1, y)]
    return []


def get_assembling_machine_connection_points(
    x: float, y: float, direction: int
) -> List[Tuple[float, float]]:
    """Get assembling machine 2/3 fluid connection points."""
    # Assembling machines with fluid inputs have a single fluid input
    # The position depends on the recipe, but typically on the left/bottom side
    if direction == NORTH:
        return [(x - 1.5, y)]
    elif direction == SOUTH:
        return [(x + 1.5, y)]
    elif direction == EAST:
        return [(x, y - 1.5)]
    elif direction == WEST:
        return [(x, y + 1.5)]
    return []


def is_pipe(entity: Optional[Dict], direction: int) -> int:
    """Check if entity is pipe or pipe-to-ground"""
    if entity is None:
        return 0

    if entity["name"] == "pipe":
        return 1
    elif entity["name"] == "pipe-to-ground":
        if entity.get("direction", 0) == direction:
            return 1

    return 0


def is_entity_in_direction(entity: Optional[Dict], target: str, direction: int) -> int:
    """Check if entity matches target and direction"""
    if entity is None:
        return 0

    if entity["name"] == target and entity.get("direction", 0) == direction:
        return 1

    return 0


def get_size(entity: Dict) -> Tuple[float, float]:
    """Pipe is 1x1"""
    return (1, 1)
