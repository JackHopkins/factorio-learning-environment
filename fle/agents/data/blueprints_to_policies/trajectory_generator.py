import math
import os

from jinja2 import Template

from fle.env import Position, BoundingBox, EntityGroup
from fle.env import FactorioInstance, Direction
from fle.env.game_types import Resource, prototype_by_name

from enum import Enum
from typing import Dict, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass
import json


@dataclass
class BlueprintEntity:
    entity_number: int
    name: str
    position: Dict[str, float]
    direction: int = 0
    items: Dict[str, int] = None
    type: str = None
    neighbours: List[int] = None
    input_priority: str = None
    recipe: Optional[str] = None
    output_priority: str = None
    control_behavior: Dict = None
    connections: Dict = None
    filter: Dict = None
    dimensions: Tuple[int, int] = None  # (width, height)


class EntityPriority(Enum):
    MINER = 1
    ASSEMBLER = 2
    FURNACE = 3
    INSERTER = 4
    POWER = 5
    CHEST = 6
    BELT = 7


instance = FactorioInstance(
    address="localhost",
    bounding_box=200,
    tcp_port=27000,
    fast=True,
    cache_scripts=False,
    inventory={
        "coal": 50,
        "copper-plate": 50,
        "burner-mining-drill": 10,
        "electric-mining-drill": 15,
        "transport-belt": 50,
        "stone-furnace": 10,
        "small-electric-pole": 15,
        "small-lamp": 10,
    },
)


def determine_resource_type(entities: List[BlueprintEntity]) -> Resource:
    """
    Determine which resource type the miners are likely targeting based on their positions.
    """
    miners = [e for e in entities if "mining-drill" in e.name]
    if not miners:
        return None

    # Use the first miner's position to guess the resource type
    first_miner = miners[0]
    if first_miner.position["x"] < 0:
        return Resource.CopperOre
    elif first_miner.position["x"] > 0:
        return Resource.IronOre
    else:
        return Resource.Coal


def find_valid_origin(
    entities: List[BlueprintEntity], resource: Resource, game: FactorioInstance
) -> Position:
    """
    Find a valid origin position using nearest_buildable with bounding box.
    """
    miners = [e for e in entities if "mining-drill" in e.name]
    if not miners:
        return Position(x=0, y=0)

    # Calculate bounding box dimensions based on miner positions
    min_x = min(e.position["x"] for e in entities)
    max_x = max(e.position["x"] for e in entities)
    min_y = min(e.position["y"] for e in entities)
    max_y = max(e.position["y"] for e in entities)

    # Create bounding box relative to first entity
    base_miner = entities[0]
    left_top = Position(
        x=min_x - base_miner.position["x"], y=min_y - base_miner.position["y"]
    )
    right_bottom = Position(
        x=max_x - base_miner.position["x"], y=max_y - base_miner.position["y"]
    )
    left_bottom = Position(
        x=min_x - base_miner.position["x"], y=max_y - base_miner.position["y"]
    )
    right_top = Position(
        x=max_x - base_miner.position["x"], y=min_y - base_miner.position["y"]
    )
    # center = Position(
    #     x=(left_top.x + right_bottom.x) / 2,
    #     y=(left_top.y + right_bottom.y) / 2
    # )

    bounding_box = BoundingBox(
        left_top=left_top,
        right_bottom=right_bottom,
        left_bottom=left_bottom,
        right_top=right_top,
    )

    # Use nearest_buildable to find valid position
    return game.nearest_buildable(prototype_by_name[miners[0].name], bounding_box)


def create_origin_finding_code_trace(entities, resource):
    """
    Generate code trace for finding origin using nearest_buildable.
    """
    miners = [e for e in entities if "mining-drill" in e.name]
    if not miners:
        return []

    # Calculate bounding box dimensions
    min_x = min(e.position["x"] for e in miners)
    max_x = max(e.position["x"] for e in miners)
    min_y = min(e.position["y"] for e in miners)
    max_y = max(e.position["y"] for e in miners)

    # Create relative bounding box calculations
    base_miner = miners[0]
    trace = [
        f"# Find suitable origin position for miners on {resource[0]}",
        "",
        "# Calculate bounding box for miners",
        "left_top = Position(",
        f"    x={min_x - base_miner.position['x']},",
        f"    y={min_y - base_miner.position['y']}",
        ")",
        "right_bottom = Position(",
        f"    x={max_x - base_miner.position['x']},",
        f"    y={max_y - base_miner.position['y']}",
        ")",
        "center = Position(",
        "    x=(left_top.x + right_bottom.x) / 2,",
        "    y=(left_top.y + right_bottom.y) / 2",
        ")",
        "",
        "miner_box = BoundingBox(",
        "    left_top=left_top,",
        "    right_bottom=right_bottom,",
        "    center=center",
        ")",
        "",
        "# Find valid position for miners using nearest_buildable",
        "origin = game.nearest_buildable(",
        f"    Prototype.{prototype_by_name[base_miner.name].name},",
        "    bounding_box=miner_box",
        ")",
        "",
        "assert origin, 'Could not find valid position for miners'",
        "",
        "# Move to origin position",
        "game.move_to(origin)",
        "",
    ]

    return trace


def find_belt_segments(entities: List[BlueprintEntity]) -> List[List[BlueprintEntity]]:
    """
    Find contiguous segments of transport belts.
    Returns list of lists, where each inner list is a contiguous belt segment.
    """
    # Get all belt entities
    belt_entities = [e for e in entities if is_transport_belt(e.name)]
    if not belt_entities:
        return []

    # Create a position map for quick lookup
    pos_map = {(e.position["x"], e.position["y"]): e for e in belt_entities}

    def get_neighbors(entity: BlueprintEntity) -> List[BlueprintEntity]:
        """Get adjacent belt entities."""
        x, y = entity.position["x"], entity.position["y"]
        neighbors = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            neighbor_pos = (x + dx, y + dy)
            if neighbor_pos in pos_map:
                neighbors.append(pos_map[neighbor_pos])
        return neighbors

    # Find connected segments using DFS
    segments = []
    visited = set()

    def dfs(entity: BlueprintEntity, current_segment: List[BlueprintEntity]):
        visited.add((entity.position["x"], entity.position["y"]))
        current_segment.append(entity)
        for neighbor in get_neighbors(entity):
            pos = (neighbor.position["x"], neighbor.position["y"])
            if pos not in visited:
                dfs(neighbor, current_segment)

    for belt in belt_entities:
        pos = (belt.position["x"], belt.position["y"])
        if pos not in visited:
            current_segment = []
            dfs(belt, current_segment)
            segments.append(current_segment)

    return segments


def find_segment_endpoints(
    segment: List[BlueprintEntity],
) -> Tuple[BlueprintEntity, BlueprintEntity]:
    """
    Find the start and end points of a belt segment.
    Returns (start_entity, end_entity).
    """
    if len(segment) == 1:
        return segment[0], segment[0]

    # Create a position map
    pos_map = {(e.position["x"], e.position["y"]): e for e in segment}

    # Find entities with only one neighbor
    endpoints = []
    for entity in segment:
        x, y = entity.position["x"], entity.position["y"]
        neighbor_count = sum(
            1
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]
            if (x + dx, y + dy) in pos_map
        )
        if neighbor_count == 1:
            endpoints.append(entity)

    # If we have exactly two endpoints, use them
    if len(endpoints) == 2:
        # Sort endpoints to maintain consistent ordering
        endpoints.sort(key=lambda e: (e.position["x"], e.position["y"]))
        return endpoints[0], endpoints[1]

    # If no clear endpoints (loop) or single belt, use first and last placed
    segment.sort(key=lambda e: e.entity_number)
    return segment[0], segment[-1]


def get_entity_priority(entity_name: str) -> EntityPriority:
    """Determine placement priority for different entity types."""
    if "mining-drill" in entity_name:
        return EntityPriority.MINER
    elif "assembling-machine" in entity_name:
        return EntityPriority.ASSEMBLER
    elif "furnace" in entity_name:
        return EntityPriority.FURNACE
    elif "inserter" in entity_name:
        return EntityPriority.INSERTER
    elif "electric-pole" in entity_name or "substation" in entity_name:
        return EntityPriority.POWER
    elif "chest" in entity_name:
        return EntityPriority.CHEST
    elif "belt" in entity_name or "splitter" in entity_name:
        return EntityPriority.BELT
    return EntityPriority.CHEST  # Default priority


def is_transport_belt(entity_name: str) -> bool:
    """Check if an entity is a transport belt."""
    return (
        "transport-belt" in entity_name
    )  # or "splitter" in entity_name or "underground-belt" in entity_name


def direction_to_enum(direction: int) -> str:
    """Convert numeric direction to Direction enum name."""
    direction_map = {0: "UP", 2: "RIGHT", 4: "DOWN", 6: "LEFT"}
    return direction_map.get(direction, "UP")


class EntityPlacement(NamedTuple):
    entity: BlueprintEntity
    reference_entity: Optional[int]  # entity_number of reference entity
    relative_position: Optional[tuple]  # (x_offset, y_offset) from reference


def find_placement_references(entities: List[BlueprintEntity]) -> List[EntityPlacement]:
    """
    Determine relative positioning between entities.
    Returns list of EntityPlacement objects with reference entities and offsets.
    """
    placements = []
    placed_entities = {}  # Map of positions to entity numbers

    # Sort entities by priority
    sorted_entities = sorted(
        entities, key=lambda e: (get_entity_priority(e.name).value, e.entity_number)
    )

    for entity in sorted_entities:
        current_pos = (entity.position["x"], entity.position["y"])

        # Find closest already-placed entity
        closest_reference = None
        min_distance = float("inf")
        relative_pos = None

        for placed_pos, placed_num in placed_entities.items():
            dx = current_pos[0] - placed_pos[0]
            dy = current_pos[1] - placed_pos[1]
            distance = abs(dx) + abs(dy)  # Manhattan distance

            if distance < min_distance and (dx == 0 or dy == 0):
                min_distance = distance
                closest_reference = placed_num
                relative_pos = (dx, dy)

        placements.append(EntityPlacement(entity, closest_reference, relative_pos))
        placed_entities[current_pos] = entity.entity_number

    return placements


def get_tile_dimensions_of_all_entities(
    entities: List[BlueprintEntity],
) -> Dict[str, Tuple[int, int]]:
    tile_dimensions = {}
    # Get counts of entitiies
    entity_counts = {}
    for entity in entities:
        entity_counts[entity.name] = entity_counts.get(entity.name, 0) + 1
    instance = FactorioInstance(
        address="localhost",
        bounding_box=200,
        tcp_port=27000,
        fast=True,
        cache_scripts=False,
        inventory=entity_counts,
    )
    # get set of entities by name
    entity_names = set([entity.name for entity in entities])
    position = instance.nearest(Resource.IronOre)
    instance.move_to(position)
    # get tile dimensions of all entities
    for entity_name in entity_names:
        entity = instance.place_entity(
            prototype_by_name[entity_name], Direction.UP, position
        )
        tile_dimensions[entity_name] = (
            entity.tile_dimensions.tile_width,
            entity.tile_dimensions.tile_height,
        )
        instance.pickup_entity(entity)

    return tile_dimensions


def generate_entity_variable_name(
    entity_name: str, entities: List[BlueprintEntity], entity_number: int
) -> str:
    """
    Generate a variable name for an entity based on naming conventions:
    - Single entities use just the entity name
    - Multiple instances use name with index
    """
    # Convert entity name to snake case
    name = entity_name.replace("-", "_")

    # Count how many entities of this type exist
    count = sum(1 for e in entities if e.name == entity_name)

    if count == 1:
        return name
    else:
        # Find the index of this entity among entities of the same type
        index = sum(
            1
            for e in entities
            if e.name == entity_name and e.entity_number < entity_number
        )
        return f"{name}_{index + 1}"


def convert_blueprint_to_trace(blueprint_json: str) -> List[str]:
    """Convert a Factorio blueprint JSON to a sequence of game commands."""
    blueprint = json.loads(blueprint_json)
    entities = [BlueprintEntity(**e) for e in blueprint["entities"]]

    # Normalize positions by subtracting minimum x,y
    min_x = min(e.position["x"] for e in entities)
    min_y = min(e.position["y"] for e in entities)

    # Create new normalized entities
    normalized_entities = []
    for entity in entities:
        new_entity = BlueprintEntity(
            entity_number=entity.entity_number,
            name=entity.name,
            position={
                "x": entity.position["x"] - min_x,
                "y": entity.position["y"] - min_y,
            },
            direction=entity.direction,
            recipe=entity.recipe,
            neighbours=entity.neighbours,
            type=entity.type,
            items=entity.items,
        )
        normalized_entities.append(new_entity)

    # Use normalized entities for the rest of the processing
    entities = normalized_entities

    # Determine resource type
    resource = determine_resource_type(entities)

    miners = [p for p in entities if "mining-drill" in p.name]

    try:
        find_valid_origin(entities, resource, instance)
    except Exception as e:
        raise ValueError(f"Failed to find valid origin: {e}. Skipping blueprint.")

    trace = []
    if resource and miners:
        trace.extend(create_origin_finding_code_trace(entities, resource))
    else:
        trace.append("origin = Position(x=0, y=0)")
        trace.append("")

    # Split entities into belts and non-belts
    belt_entities = [e for e in entities if is_transport_belt(e.name)]
    non_belt_entities = [e for e in entities if not is_transport_belt(e.name)]

    # Process non-belt entities first
    placements = find_placement_references(non_belt_entities)

    # Find belt segments
    belt_segments = find_belt_segments(belt_entities)

    tile_dimensions = get_tile_dimensions_of_all_entities(entities)

    placed_entity_vars = {}  # Map of entity numbers to their variable names
    placed_entity = {}

    # Place entities
    for placement in placements:
        entity = placement.entity
        entity_var = generate_entity_variable_name(
            entity.name, entities, entity.entity_number
        )
        placed_entity_vars[entity.entity_number] = entity_var
        placed_entity[entity.entity_number] = entity

        trace.append(f"# Place {entity.name}")

        if placement.reference_entity is None:
            trace.append(
                f"game.move_to(origin+Position(x={entity.position['x']},y={entity.position['y']}))"
            )
            if "mining-drill" in entity.name:
                trace.append(
                    f"{entity_var} = game.place_entity("
                    f"Prototype.{prototype_by_name[entity.name].name}, "
                    f"direction=Direction.{direction_to_enum(entity.direction)}, "
                    f"position=origin+Position(x={entity.position['x']},y={entity.position['y']}))"
                )
            else:
                trace.append(
                    f"{entity_var} = game.place_entity("
                    f"Prototype.{prototype_by_name[entity.name].name}, "
                    f"direction=Direction.{direction_to_enum(entity.direction)}, "
                    f"position=origin+Position(x={entity.position['x']},y={entity.position['y']}))"
                )
        else:
            ref_var = placed_entity_vars[placement.reference_entity]
            ref = placed_entity[placement.reference_entity]
            dx, dy = placement.relative_position

            direction_words = []
            position_ref_modifier = [""]
            spacing = 0
            if abs(dx) != 0 and abs(dy) != 0:
                raise ValueError("Diagonal placement not supported")
            if abs(dx) > abs(dy):
                direction_words = ["RIGHT" if dx > 0 else "LEFT"]
                spacing = abs(dx)
                spacing -= (
                    tile_dimensions[entity.name][0] / 2
                    + tile_dimensions[ref.name][0] / 2
                )

                if 0 < abs(dy) < 1:
                    if (
                        dy > 0 and ref.name != "burner-mining-drill"
                    ):  # We should generalise this to all entities larger than 1x1
                        position_ref_modifier = [".above()"] * abs(dy)
                    if dy < 0:
                        position_ref_modifier = [".below()"] * abs(dy)
                elif abs(dy) > 1:
                    position_ref_modifier = [f" + Position(x=0, y={dy})"]

            else:
                direction_words = ["DOWN" if dy > 0 else "UP"]
                spacing = abs(dy)
                spacing -= (
                    tile_dimensions[entity.name][1] / 2
                    + tile_dimensions[ref.name][1] / 2
                )
                if 0 < abs(dx) < 1:
                    if (
                        dx > 0 and ref.name != "burner-mining-drill"
                    ):  # We should generalise this to all entities larger than 1x1
                        position_ref_modifier = [".right()"] * abs(dx)
                    if dx < 0:
                        position_ref_modifier = [".left()"] * abs(dx)
                elif abs(dx) > 1:
                    position_ref_modifier = [f" + Position(x={dx}, y=0)"]

            placement_cmd = (
                f"{entity_var} = game.place_entity_next_to("
                f"Prototype.{prototype_by_name[entity.name].name}, "
                f"reference_position={ref_var}.position{''.join(position_ref_modifier)}, "
                f"direction=Direction.{direction_words[0]}"
            )

            if math.floor(spacing) != 0:
                placement_cmd += f", spacing={math.floor(spacing)})"
            else:
                placement_cmd += ")"

            trace.append(placement_cmd)

            # Rotate entity if necessary
            trace.append(
                f"{entity_var} = game.rotate_entity({entity_var}, Direction.{direction_to_enum(entity.direction)})"
            )

        trace.append(f"assert {entity_var}, 'Failed to place {entity.name}'")

        if entity.recipe:
            trace.append(
                f"game.set_entity_recipe({entity_var}, "
                f"Prototype.{prototype_by_name[entity.recipe].name})"
            )

        trace.append("")

    # Place belt segments
    for segment_idx, segment in enumerate(belt_segments):
        start, end = find_segment_endpoints(segment)

        # Connection type
        connection_type = "Prototype." + prototype_by_name[start.name].name

        if start.position["x"] > end.position["x"]:
            direction = 6
        elif start.position["x"] < end.position["x"]:
            direction = 2
        elif start.position["y"] > end.position["y"]:
            direction = 0
        else:
            direction = 4
        # If the start needs to connect to a non-belt entity, reference that
        trace.append(f"# Place transport belt segment {segment_idx + 1}")

        if len(segment) == 1:
            trace.append(
                f"game.move_to(origin+Position(x={segment[0].position['x']},y={segment[0].position['y']}))"
            )
            trace.append(
                f"belt_segment_{segment_idx + 1} = game.place_entity("
                f"{connection_type}, "
                f"direction=Direction.{direction_to_enum(segment[0].direction)}, "
                f"position=origin+Position(x={segment[0].position['x']}, y={segment[0].position['y']})"
                f")"
            )
            trace.append(
                f"assert belt_segment_{segment_idx + 1}, "
                f"'Failed to place belt segment {segment_idx + 1}'"
            )
            trace.append("")
            continue

        # Find reference points for the belt segment
        start_ref = None
        end_ref = None

        # Look for non-belt entities near the start/end points to connect to
        start_closest_entity, end_closest_entity = None, None
        start_closest_var, end_closest_var = None, None
        start_closest_distance, end_closest_distance = float("inf"), float("inf")
        for entity in non_belt_entities:
            start_distance = abs(entity.position["x"] - start.position["x"]) + abs(
                entity.position["y"] - start.position["y"]
            )
            end_distance = abs(entity.position["x"] - end.position["x"]) + abs(
                entity.position["y"] - end.position["y"]
            )
            if start_distance < start_closest_distance:
                start_closest_entity = entity
                start_closest_distance = start_distance
                start_closest_var = placed_entity_vars[entity.entity_number]
            if end_distance < end_closest_distance:
                end_closest_entity = entity
                end_closest_distance = end_distance
                end_closest_var = placed_entity_vars[entity.entity_number]

            if (
                abs(entity.position["x"] - start.position["x"]) < 1
                and abs(entity.position["y"] - start.position["y"]) < 1
            ):
                start_ref = f"{placed_entity_vars[entity.entity_number]}.position"
            if (
                abs(entity.position["x"] - end.position["x"]) < 1
                and abs(entity.position["y"] - end.position["y"]) < 1
            ):
                end_ref = f"{placed_entity_vars[entity.entity_number]}.position"

        if not start_ref:
            dx = start.position["x"] - start_closest_entity.position["x"]
            dy = start.position["y"] - start_closest_entity.position["y"]
            start_ref = f"Position(x={start_closest_var}.position.x+{dx}, y={start_closest_var}.position.y+{dy})"
            # start_ref = f"Position(x={start.position['x']}, y={start.position['y']})"
        if not end_ref:
            dx = end.position["x"] - end_closest_entity.position["x"]
            dy = end.position["y"] - end_closest_entity.position["y"]
            end_ref = f"Position(x={end_closest_var}.position.x+{dx}, y={end_closest_var}.position.y+{dy})"

        # Check to see if we should swap start and end, depending on the direction of the belts.
        # If the belts are going down, but the start has a lower y value than the end, we should swap.
        # If the belts are going left, but the start has a lower x value than the end, we should swap.

        if (
            start.position["y"] < end.position["y"]
            and start.position["x"] == end.position["x"]
            and direction == 4
        ):
            start_ref, end_ref = end_ref, start_ref
        elif (
            start.position["x"] < end.position["x"]
            and start.position["y"] == end.position["y"]
            and direction == 6
        ):
            start_ref, end_ref = end_ref, start_ref
        elif (
            start.position["y"] > end.position["y"]
            and start.position["x"] == end.position["x"]
            and direction == 0
        ):
            start_ref, end_ref = end_ref, start_ref
        elif (
            start.position["x"] > end.position["x"]
            and start.position["y"] == end.position["y"]
            and direction == 2
        ):
            start_ref, end_ref = end_ref, start_ref

        # Connect the belt segment
        trace.append(
            f"belt_segment_{segment_idx + 1} = game.connect_entities("
            f"{start_ref}, {end_ref}, "
            f"connection_type={connection_type})"
        )

        # Store references to placed belts
        trace.append(
            f"assert belt_segment_{segment_idx + 1}, "
            f"'Failed to place belt segment {segment_idx + 1}'"
        )
        trace.append("")

    # Add final verification
    # trace.append("# Verify setup")
    # trace.append("entities = game.inspect_entities(resource_patch.bounding_box.center, radius=10)")
    #
    # # Use consistent entity naming in verification
    # for entity in entities:
    #     entity_var = generate_entity_variable_name(entity.name, entities, entity.entity_number)
    #     trace.append(
    #         f"assert entities.get_entity(Prototype.{prototype_by_name[entity.name].name}), "
    #         f"'{entity_var} not found in setup'"
    #     )

    trace.append("\nprint('Successfully placed all blueprint entities')")

    return trace


def generate_trace(blueprint_json: str) -> str:
    """Generate the complete trace as a string."""
    trace_lines = convert_blueprint_to_trace(blueprint_json)
    return "\n".join(trace_lines)


def get_inventory(blueprint_json):
    blueprint = json.loads(blueprint_json)
    entities = [BlueprintEntity(**e) for e in blueprint["entities"]]
    entity_counts = {}
    for entity in entities:
        entity_counts[entity.name] = entity_counts.get(entity.name, 0) + 1
    return entity_counts


def _create_more_ore(position: Position, size=20):
    """
    We need to create more ore, because some mining templates don't fit on the lab scenario ore deposits.
    :param position: Position to create ore
    :param size: Size of patch
    :return: A lua script to create more ore
    """
    return f"""
/c local surface=game.players[1].surface
local ore=nil
local size={size}
local density=10
for y=-size, size do
	for x=-size, size do
		a=(size+1-math.abs(x))*10
		b=(size+1-math.abs(y))*10
		if a<b then
			ore=math.random(a*density-a*(density-8), a*density+a*(density-8))
		end
		if b<a then
			ore=math.random(b*density-b*(density-8), b*density+b*(density-8))
		end
		if surface.get_tile({position.x}+x, {position.y}+y).collides_with("ground-tile") then
			surface.create_entity({{name="copper-ore", amount=ore, position={{{position.x}+x, {position.y}+y}}}})
		end
	end
end
""".strip()


def verify_placement(game_entities, blueprint_json):
    def _get_hash(entities) -> str:
        # we get the pairwise dx and dy between all entities
        # we then sort the pairs by dx and dy
        # we then hash the sorted pairs
        # this should give us a unique hash for each blueprint

        pairs = []
        for i in range(len(entities)):
            for j in range(len(entities)):
                dx = entities[i].position["x"] - entities[j].position["x"]
                dy = entities[i].position["y"] - entities[j].position["y"]
                pairs.append((int(dx * 2), int(dy * 2)))

        pairs.sort()
        return hash(tuple(pairs)), pairs

    blueprint = json.loads(blueprint_json)
    entities = [BlueprintEntity(**e) for e in blueprint["entities"]]
    # Blueprint hash
    hash1, blueprint_pairs = _get_hash(entities)

    # Game hash
    positions = []
    for entity in game_entities:
        if isinstance(entity, EntityGroup):
            if hasattr(entity, "belts"):
                positions.extend([(e.position.x, e.position.y) for e in entity.belts])
            elif hasattr(entity, "pipes"):
                positions.extend([(e.position.x, e.position.y) for e in entity.pipes])
        else:
            positions.append((entity.position.x, entity.position.y))

    pairs = []
    for i in range(len(positions)):
        for j in range(len(positions)):
            dx = positions[i][0] - positions[j][0]
            dy = positions[i][1] - positions[j][1]
            pairs.append((int(dx * 2), int(dy * 2)))

    pairs.sort()
    hash2 = hash(tuple(pairs))

    assert hash1 == hash2, (
        f"The difference in entities is {set(blueprint_pairs) - set(pairs)}"
    )


# get execution dir dynamically
execution_dir = os.path.dirname(os.path.realpath(__file__)) + "/blueprints/electricity/"
output_dir = os.path.dirname(os.path.realpath(__file__)) + "/full/electricity/"
# filename = "miner_cycle"

files = os.listdir(execution_dir)
# generate if python file doesn't exist
for file in files:
    filename = file.replace(".json", "").replace(".py", "")
    if not os.path.exists(output_dir + filename + ".py") and os.path.exists(
        execution_dir + filename + ".json"
    ):
        with open(execution_dir + filename + ".json", "r") as f:
            blueprint_json = f.read()
            inventory = get_inventory(blueprint_json)
            instance.set_inventory(inventory)
            # instance.add_command(_create_more_ore(Position(x=0, y=0), 30))
            instance.execute_transaction()
            instance.move_to(Position(x=0, y=0))
            trace = None
            try:
                trace = generate_trace(blueprint_json)

                score, goal, result = instance.eval_with_error(
                    trace.replace("game.", ""), timeout=60
                )
                if "error" in result:
                    raise Exception(result["error"])

                game_entities = instance.get_entities()
                verify_placement(game_entities, blueprint_json)

                # Write the code to a python file of the same name
                with open(output_dir + filename.split(".json")[0] + ".py", "w") as f1:
                    f1.write(trace)

            except Exception as e:
                print(e)
                print("Error in blueprint")

                # Load template string from file
                with open(
                    os.path.dirname(os.path.realpath(__file__))
                    + "/test_template.jinja2",
                    "r",
                ) as f:
                    template_str = f.read()
                    # Create template object
                    template = Template(template_str)

                    # Render the template
                    rendered = template.render(
                        inventory=inventory,
                        test_name=filename.replace(" ", "_"),
                        test_content=trace,
                    )

                    # Write to file
                    with open(output_dir + "test_" + filename + "_error.py", "w") as f:
                        f.write(rendered)
