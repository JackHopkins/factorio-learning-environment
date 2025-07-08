import json
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from typing import Union

from fle.env import EntityGroup
from fle.env import FactorioInstance, Direction
from fle.env.game_types import prototype_by_name, Resource


@dataclass
class Entity:
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


class BlueprintAnalyzerWithPlaceNextTo:
    def __init__(self, blueprint: Dict):
        self.blueprint = blueprint
        self.entities = [Entity(**entity) for entity in self.blueprint["entities"]]

        # Get dimensions for all entities
        dimensions = self.get_tile_dimensions_of_all_entities(self.entities)
        for entity in self.entities:
            entity.dimensions = dimensions[entity.name]

        # Calculate true bounding box
        self.min_x = min(e.position["x"] for e in self.entities)
        self.min_y = min(e.position["y"] for e in self.entities)
        self.max_x = max(e.position["x"] for e in self.entities)
        self.max_y = max(e.position["y"] for e in self.entities)

        # Normalize positions
        for entity in self.entities:
            entity.position["x"] = entity.position["x"] - self.min_x
            entity.position["y"] = entity.position["y"] - self.min_y

    def get_tile_dimensions_of_all_entities(
        self, entities: List[Entity]
    ) -> Dict[str, Tuple[int, int]]:
        """Get the tile dimensions of all entities in the blueprint."""
        tile_dimensions = {}
        # Get counts of entities
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

        # Get set of entities by name
        entity_names = set([entity.name for entity in entities])
        position = instance.nearest(Resource.IronOre)
        instance.move_to(position)

        # Get tile dimensions of all entities
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

    def get_entity_size(self, entity: Entity) -> Tuple[float, float]:
        """Get the effective size of an entity considering its direction."""
        width, height = entity.dimensions
        if entity.direction in [2, 6]:  # LEFT or RIGHT
            width, height = height, width
        return width, height

    def find_adjacent_entities(self) -> List[Tuple[Entity, Entity, str, float]]:
        """Find pairs of adjacent entities and their relative positions."""
        adjacent_pairs = []
        processed = set()

        def get_relative_direction(e1: Entity, e2: Entity) -> Tuple[str, float]:
            """Determine relative direction and spacing between entities."""
            dx = round((e2.position["x"] - e1.position["x"]) * 2) / 2
            dy = round((e2.position["y"] - e1.position["y"]) * 2) / 2

            e1_width, e1_height = self.get_entity_size(e1)
            e2_width, e2_height = self.get_entity_size(e2)

            # Calculate both possible spacings
            h_spacing = abs(dx) - (e1_width + e2_width) / 2
            v_spacing = abs(dy) - (e1_height + e2_height) / 2

            # If spacings are similar, prefer the direction that maintains grid alignment
            if abs(h_spacing - v_spacing) < 0.1:
                # Check if entities are aligned horizontally or vertically
                h_aligned = abs(e1.position["y"] - e2.position["y"]) < 0.1
                v_aligned = abs(e1.position["x"] - e2.position["x"]) < 0.1

                if h_aligned:
                    direction = "Direction.RIGHT" if dx > 0 else "Direction.LEFT"
                    spacing = h_spacing
                elif v_aligned:
                    direction = "Direction.DOWN" if dy > 0 else "Direction.UP"
                    spacing = v_spacing
                else:
                    # If not aligned, choose based on which spacing is slightly better
                    if h_spacing <= v_spacing:
                        direction = "Direction.RIGHT" if dx > 0 else "Direction.LEFT"
                        spacing = h_spacing
                    else:
                        direction = "Direction.DOWN" if dy > 0 else "Direction.UP"
                        spacing = v_spacing
            else:
                # If spacings are significantly different, choose the smaller one
                if abs(h_spacing) < v_spacing:
                    direction = "Direction.RIGHT" if dx > 0 else "Direction.LEFT"
                    spacing = h_spacing
                else:
                    direction = "Direction.DOWN" if dy > 0 else "Direction.UP"
                    spacing = v_spacing

            return direction, max(0, spacing)

        # Create a grid for spatial partitioning
        grid_size = 2  # Adjust based on typical entity sizes
        grid = defaultdict(list)

        for entity in self.entities:
            grid_x = int(entity.position["x"] // grid_size)
            grid_y = int(entity.position["y"] // grid_size)
            grid[(grid_x, grid_y)].append(entity)

        # Check adjacent grid cells for nearby entities
        for entity in self.entities:
            grid_x = int(entity.position["x"] // grid_size)
            grid_y = int(entity.position["y"] // grid_size)

            # Check neighboring cells
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    for other_entity in grid[(grid_x + dx, grid_y + dy)]:
                        if entity.entity_number >= other_entity.entity_number:
                            continue

                        dx = abs(entity.position["x"] - other_entity.position["x"])
                        dy = abs(entity.position["y"] - other_entity.position["y"])

                        # Check if entities are within reasonable distance
                        max_distance = max(
                            sum(entity.dimensions), sum(other_entity.dimensions)
                        )
                        if max(dx, dy) <= max_distance:
                            direction, spacing = get_relative_direction(
                                entity, other_entity
                            )
                            pair_key = (
                                min(entity.entity_number, other_entity.entity_number),
                                max(entity.entity_number, other_entity.entity_number),
                            )

                            if (
                                pair_key not in processed and spacing <= 1
                            ):  # Only consider reasonably close entities
                                adjacent_pairs.append(
                                    (entity, other_entity, direction, spacing)
                                )
                                processed.add(pair_key)

        return adjacent_pairs

    def verify_placement(self, game_entities: List[Union[Entity, EntityGroup]]) -> bool:
        # Blueprint hash
        hash1, blueprint_pairs = self._get_hash()

        # Game hash
        positions = []
        for entity in game_entities:
            if isinstance(entity, EntityGroup):
                if hasattr(entity, "belts"):
                    positions.extend(
                        [(e.position.x, e.position.y) for e in entity.belts]
                    )
                elif hasattr(entity, "pipes"):
                    positions.extend(
                        [(e.position.x, e.position.y) for e in entity.pipes]
                    )
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

    def generate_placement_sequence(
        self,
    ) -> List[Tuple[Entity, Optional[Entity], str, float]]:
        """Generate an optimal sequence of entity placements."""
        adjacent_pairs = self.find_adjacent_entities()
        placement_sequence = []
        placed_entities = set()

        # Create adjacency graph
        graph = defaultdict(list)
        for e1, e2, direction, spacing in adjacent_pairs:
            graph[e1.entity_number].append((e2, direction, spacing))
            graph[e2.entity_number].append((e1, direction, spacing))

        # Start with the leftmost entity that has the most connections
        anchor = max(
            self.entities, key=lambda e: (len(graph[e.entity_number]), -e.position["x"])
        )

        placement_sequence.append((anchor, None, None, 0))
        placed_entities.add(anchor.entity_number)

        # Use priority queue to process entities based on number of connections to placed entities
        def get_connection_score(entity):
            return sum(
                1
                for e in graph[entity.entity_number]
                if e[0].entity_number in placed_entities
            )

        while True:
            # Find entity with most connections to placed entities
            candidates = []
            for entity_num in graph:
                if entity_num not in placed_entities:
                    entity = next(
                        e for e in self.entities if e.entity_number == entity_num
                    )
                    score = get_connection_score(entity)
                    if score > 0:
                        candidates.append((score, entity))

            if not candidates:
                break

            # Place entity with highest score
            _, next_entity = max(candidates, key=lambda x: x[0])

            # Find best reference entity among placed entities
            best_ref = None
            best_spacing = float("inf")
            best_direction = None

            for ref_entity, direction, spacing in graph[next_entity.entity_number]:
                if (
                    ref_entity.entity_number in placed_entities
                    and spacing < best_spacing
                ):
                    best_ref = ref_entity
                    best_spacing = spacing
                    best_direction = direction

            placement_sequence.append(
                (next_entity, best_ref, best_direction, best_spacing)
            )
            placed_entities.add(next_entity.entity_number)

        # Add any remaining entities
        for entity in self.entities:
            if entity.entity_number not in placed_entities:
                nearest = min(
                    (e[0] for e in placement_sequence),
                    key=lambda e: abs(e.position["x"] - entity.position["x"])
                    + abs(e.position["y"] - entity.position["y"]),
                )
                direction, spacing = self.get_relative_position(nearest, entity)
                placement_sequence.append((entity, nearest, direction, spacing))
                placed_entities.add(entity.entity_number)

        return placement_sequence

    # def _get_relative_position(self, ref: Entity, target: Entity) -> Tuple[str, float]:
    #     """Calculate relative position between two entities considering their dimensions."""
    #     dx = target.position['x'] - ref.position['x']
    #     dy = target.position['y'] - ref.position['y']
    #
    #     ref_width, ref_height = self.get_entity_size(ref)
    #     target_width, target_height = self.get_entity_size(target)
    #
    #     if abs(dx) > abs(dy):
    #         direction = "Direction.RIGHT" if dx > 0 else "Direction.LEFT"
    #         spacing = abs(dx) - (ref_width + target_width) / 2
    #     else:
    #         direction = "Direction.DOWN" if dy > 0 else "Direction.UP"
    #         spacing = abs(dy) - (ref_height + target_height) / 2
    #
    #     return direction, max(0, spacing)

    def generate_program(self) -> str:
        placement_sequence = self.generate_placement_sequence()

        # Start with standard bounding box calculation
        lines = [
            "# Calculate bounding box",
            "left_top = Position(",
            "    x=0,",
            "    y=0",
            ")",
            "right_bottom = Position(",
            f"    x={self.max_x - self.min_x},",
            f"    y={self.max_y - self.min_y}",
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
            "# Find valid position using nearest_buildable",
            f"origin = game.nearest_buildable({self._name_to_prototype_string(placement_sequence[0][0].name)}, "
            f"miner_box)",
            "",
            "assert origin, 'Could not find valid position'",
            "origin = origin + left_top + Position(x=0.5, y=0.5)",
            "game.move_to(origin)",
            "",
        ]

        # Generate placements
        entity_vars = {}
        for idx, (entity, ref_entity, direction, spacing) in enumerate(
            placement_sequence
        ):
            var_name = f"entity_{entity.entity_number}"
            entity_vars[entity.entity_number] = var_name

            if ref_entity is None:
                # First entity placement
                lines.extend(
                    [
                        f"# Place initial {entity.name}",
                        f"{var_name} = game.place_entity({self._name_to_prototype_string(entity.name)}, ",
                        f"    position=Position(x=origin.x + {entity.position['x']:.1f}, "
                        f"y=origin.y + {entity.position['y']:.1f}),",
                        f"    direction={self._direction_to_enum(entity.direction)},",
                        "    exact=True)",
                        "",
                    ]
                )
            else:
                # Place relative to reference entity
                ref_var = entity_vars[ref_entity.entity_number]
                lines.extend(
                    [
                        f"# Place {entity.name} relative to {ref_entity.name}",
                        f"{var_name} = game.place_entity_next_to(",
                        f"    {self._name_to_prototype_string(entity.name)},",
                        f"    {ref_var}.position,",
                        f"    direction={direction},",
                        f"    spacing={spacing:.1f})",
                        "",
                        f"{var_name} = game.rotate_entity({var_name}, {self._direction_to_enum(entity.direction)})",
                        "",
                    ]
                )

            # Add recipe if needed
            if entity.recipe:
                lines.append(
                    f"game.set_entity_recipe({var_name}, "
                    f"Prototype.{prototype_by_name[entity.recipe].name})"
                )
                lines.append("")

        return "\n".join(lines)

    def get_inventory(self):
        entity_counts = {}
        for entity in self.entities:
            entity_counts[entity.name] = entity_counts.get(entity.name, 0) + 1
        return entity_counts

    def _direction_to_enum(self, direction: int) -> str:
        direction_map = {
            0: "Direction.UP",
            2: "Direction.RIGHT",
            4: "Direction.DOWN",
            6: "Direction.LEFT",
        }
        return direction_map.get(direction, "Direction.UP")

    def _name_to_prototype_string(self, name: str) -> str:
        return f"Prototype.{name.title().replace('-', '')}"


if __name__ == "__main__":
    execution_dir = os.path.dirname(os.path.realpath(__file__)) + "/blueprints/example/"
    filename = "1a. Mining"  # Early Mining"

    # iterate over all json files in the directory
    for filename in os.listdir(execution_dir):
        if filename.endswith(".json"):
            # skip if the python file exists
            # if os.path.exists(execution_dir + filename.replace(".json", ".py")):
            #    continue
            with open(execution_dir + filename, "r") as f:
                print(filename)
                blueprint_json = f.read()
                blueprint = json.loads(blueprint_json)
                if len(blueprint["entities"]) > 200:
                    print("Skipping large blueprint")
                    continue
                analyzer = BlueprintAnalyzerWithPlaceNextTo(blueprint)
                code = analyzer.generate_program()

                inventory = analyzer.get_inventory()
                instance = FactorioInstance(
                    address="localhost",
                    bounding_box=200,
                    tcp_port=27000,
                    fast=True,
                    cache_scripts=False,
                    inventory=inventory,
                )
                try:
                    score, goal, result = instance.eval_with_error(
                        code.replace("game.", ""), timeout=60
                    )
                    if "error" in result:
                        raise Exception(result["error"])
                except Exception as e:
                    print(e)
                    print("Error in blueprint")
                    continue

                print(code)
                game_entities = instance.get_entities()
                try:
                    analyzer.verify_placement(game_entities)
                except AssertionError as e:
                    print(e)
                    print("Error in blueprint")
                    continue
                # Write the code to a python file of the same name
                with open(
                    execution_dir
                    + filename.split(".json")[0]
                    + " with connect"
                    + ".py",
                    "w",
                ) as f1:
                    f1.write(code)
