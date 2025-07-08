import os

import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple, Set
import json
from fle.env.game_types import prototype_by_name


@dataclass
class Entity:
    entity_number: int
    name: str
    position: Dict[str, float]
    direction: int = 0
    items: Dict[str, int] = None
    type: str = None
    neighbours: List[int] = None


class BlueprintAnalyzer:
    def __init__(self, blueprint_json: str):
        data = json.loads(blueprint_json)
        self.entities = [Entity(**entity) for entity in data["entities"]]
        self.entities_by_id = {e.entity_number: e for e in self.entities}
        self.grid_size = self._calculate_grid_size()
        self.entity_grid = self._create_entity_grid()
        self.used_entities: Set[int] = set()
        # Store world offsets for coordinate conversion
        self.min_x = min(e.position["x"] for e in self.entities)
        self.min_y = min(e.position["y"] for e in self.entities)

        self.max_x = max(e.position["x"] for e in self.entities)
        self.max_y = max(e.position["y"] for e in self.entities)

        self.offset_to_origin_x = self.min_x  # *-1
        self.offset_to_origin_y = self.min_y  # *-1

        # Offsets
        self.offset_x = abs(self.min_x) if self.min_x < 0 else -abs(self.min_x)
        self.offset_y = abs(self.min_y) if self.min_y < 0 else -abs(self.min_y)

    def _direction_to_enum(self, direction: int) -> str:
        """Convert numeric direction to Direction enum name."""
        direction_map = {0: "UP", 2: "RIGHT", 4: "DOWN", 6: "LEFT"}
        return "Direction." + direction_map.get(direction, "UP")

    def _name_to_prototype_string(self, name: str) -> str:
        return f"Prototype.{name.title().replace('-', '')}"

    def _world_to_grid_coords(self, x: float, y: float) -> Tuple[int, int]:
        """Convert world coordinates to grid coordinates"""
        return (
            int(x + self.min_x + self.grid_size[0] // 2),
            int(y + self.min_y + self.grid_size[1] // 2),
        )

    def _grid_to_world_coords(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        """Convert grid coordinates back to world coordinates"""
        return (
            float(grid_x + self.min_x - self.grid_size[0] // 2),
            float(grid_y + self.min_y - self.grid_size[1] // 2),
        )

    def _calculate_grid_size(self) -> Tuple[int, int]:
        """Calculate the size of the grid needed to contain all entities"""
        min_x = min(e.position["x"] for e in self.entities)
        max_x = max(e.position["x"] for e in self.entities)
        min_y = min(e.position["y"] for e in self.entities)
        max_y = max(e.position["y"] for e in self.entities)

        # Add padding and convert to integer grid coordinates
        width = int(max_x * 2 - min_x * 2) + 4
        height = int(max_y * 2 - min_y * 2) + 4

        return width, height

    def _create_entity_grid(self) -> Dict[str, np.ndarray]:
        """Create a grid representation of entities by type"""
        width, height = self.grid_size
        grids = {}

        # Get unique entity types
        entity_types = set(e.name for e in self.entities)

        # Create a grid for each entity type
        for entity_type in entity_types:
            grid = np.zeros((height, width), dtype=int)
            type_entities = [e for e in self.entities if e.name == entity_type]

            for entity in type_entities:
                # Convert world coordinates to grid coordinates
                x = int(entity.position["x"] * 2 + width // 2)
                y = int(entity.position["y"] * 2 + height // 2)
                grid[y, x] = entity.entity_number

            grids[entity_type] = grid

        return grids

    def find_patterns(self) -> List[Dict]:
        """Find patterns of entities that can be placed in loops"""
        self.used_entities = set()  # Reset used entities
        patterns = []

        # For each entity type
        for entity_type, grid in self.entity_grid.items():
            # Look for horizontal lines
            horizontal_patterns = self._find_lines(grid, "horizontal")
            for pattern in horizontal_patterns:
                if self._is_valid_pattern(pattern["entities"]):
                    self._mark_entities_used(pattern["entities"])
                    patterns.append(
                        {
                            "type": entity_type,
                            "direction": "horizontal",
                            "orientation": self.entities_by_id[
                                pattern["entities"][0]
                            ].direction,
                            "start": pattern["start"],
                            "end": pattern["end"],
                            "y": pattern["y"],
                            "step": pattern["step"],
                            "entities": pattern["entities"],
                        }
                    )

            # Look for vertical lines
            vertical_patterns = self._find_lines(grid, "vertical")
            for pattern in vertical_patterns:
                if self._is_valid_pattern(pattern["entities"]):
                    self._mark_entities_used(pattern["entities"])
                    patterns.append(
                        {
                            "type": entity_type,
                            "direction": "vertical",
                            "start": pattern["start"],
                            "end": pattern["end"],
                            "x": pattern["x"],
                            "step": pattern["step"],
                            "entities": pattern["entities"],
                        }
                    )

        # Add remaining entities as individual placements
        self._add_remaining_entities(patterns)
        return patterns

    def _is_valid_pattern(self, entities: List[int]) -> bool:
        """Check if all entities in pattern are unused"""
        return not any(entity in self.used_entities for entity in entities)

    def _mark_entities_used(self, entities: List[int]):
        """Mark entities as used"""
        self.used_entities.update(entities)

    def _add_remaining_entities(self, patterns: List[Dict]):
        """Add any unused entities as individual placements"""
        for entity in self.entities:
            if entity.entity_number not in self.used_entities:
                # Get entity world coordinates
                patterns.append(
                    {
                        "type": entity.name,
                        "direction": "single",
                        "x": entity.position["x"],
                        "y": entity.position["y"],
                        "entities": [entity.entity_number],
                    }
                )
                self.used_entities.add(entity.entity_number)

    def _find_lines(self, grid: np.ndarray, direction: str) -> List[Dict]:
        """Find lines of entities in the specified direction"""
        patterns = []
        if direction == "horizontal":
            for y in range(grid.shape[0]):
                row = grid[y, :]
                pattern = self._find_consecutive_entities(row)
                if pattern:
                    for p in pattern:
                        p["y"] = y / 2  # - self.grid_size[0] // 2
                    patterns.extend(pattern)
        else:  # vertical
            for x in range(grid.shape[1]):
                col = grid[:, x]
                pattern = self._find_consecutive_entities(col)
                if pattern:
                    for p in pattern:
                        p["x"] = x / 2  # - self.grid_size[1] // 2
                    patterns.extend(pattern)
        return patterns

    def _find_consecutive_entities(self, arr: np.ndarray) -> List[Dict]:
        """Find sequences of entities with consistent spacing"""
        patterns = []
        entity_positions = np.nonzero(arr)[0]

        if len(entity_positions) < 2:
            return patterns

        i = 0
        while i < len(entity_positions):
            # Start a new potential pattern
            start_pos = entity_positions[i]
            entities = [arr[start_pos]]

            # If there's at least one more entity to check
            if i + 1 < len(entity_positions):
                # Calculate initial step size
                step = entity_positions[i + 1] - entity_positions[i]
                j = i + 1

                # Continue while we find entities with the same step size
                while j < len(entity_positions):
                    if entity_positions[j] - entity_positions[j - 1] == step:
                        entities.append(arr[entity_positions[j]])
                        j += 1
                    else:
                        break

                # If we found a pattern of at least 2 entities
                if len(entities) >= 2:
                    patterns.append(
                        {
                            "start": start_pos - self.grid_size[0] // 2,
                            "end": entity_positions[j - 1] - self.grid_size[0] // 2,
                            "step": step,
                            "entities": entities,
                        }
                    )
                    i = j - 1  # Start next search after this pattern

            i += 1

        return patterns

    def create_origin_finding_code_trace(self):
        """
        Generate code trace for finding origin using nearest_buildable.
        """
        miners = [e for e in self.entities if "mining-drill" in e.name]
        if not miners:
            return ["origin = Position(x=0, y=0)"]

        # Create relative bounding box calculations
        base_miner = miners[0]
        trace = [
            "# Find suitable origin position for miners on ore",
            "",
            "# Calculate bounding box for miners",
            "left_top = Position(",
            f"    x={self.min_x - base_miner.position['x']},",
            f"    y={self.min_y - base_miner.position['y']}",
            ")",
            "right_bottom = Position(",
            f"    x={self.max_x - base_miner.position['x']},",
            f"    y={self.max_y - base_miner.position['y']}",
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
            "origin = origin + left_top",
            "# Move to origin position",
            "game.move_to(origin)",
            "",
        ]

        return trace

    def generate_placement_code(self) -> str:
        """Generate Python code for placing entities in patterns"""
        patterns = self.find_patterns()
        code_lines = []

        code_lines.extend(self.create_origin_finding_code_trace())
        for pattern in patterns:
            if pattern["direction"] == "horizontal":
                world_y = self._grid_to_world_coords(0, pattern["y"])[1]
                # world_y = pattern['y'] - abs(self.min_y)
                code_lines.append(
                    f"# Place {pattern['type']} horizontally at y={world_y}"
                )
                code_lines.append(
                    f"for x in range({pattern['start']}, {pattern['end'] + 1}, {pattern['step']}):"
                )
                code_lines.append(f"    world_x = x/2 + {-abs(self.min_x)} + origin.x")
                code_lines.append(f"    world_y = {world_y} + origin.y")
                code_lines.append("    game.move_to(Position(x=world_x, y=world_y))")
                code_lines.append(
                    f"    game.place_entity({self._name_to_prototype_string(pattern['type'])}, "
                    f"position=Position(x=world_x, y=world_y), "
                    f"direction={self._direction_to_enum(pattern['orientation'] if 'orientation' in pattern else 0)})"
                )
            elif pattern["direction"] == "vertical":
                world_x = self._grid_to_world_coords(pattern["x"], 0)[0]
                # world_x = pattern['x'] - abs(self.min_x)
                code_lines.append(
                    f"# Place {pattern['type']} vertically at x={world_x}"
                )
                code_lines.append(
                    f"for y in range({pattern['start']}, {pattern['end'] + 1}, {pattern['step']}):"
                )
                code_lines.append(f"    world_y = y/2 + {-abs(self.min_x)} + origin.y")
                code_lines.append(f"    world_x = {world_x} + origin.x")
                code_lines.append("    game.move_to(Position(x=world_x, y=world_y))")
                code_lines.append(
                    f"    game.place_entity({self._name_to_prototype_string(pattern['type'])}, "
                    f"position=Position(x=world_x, y=world_y), "
                    f"direction={self._direction_to_enum(pattern['orientation'] if 'orientation' in pattern else 0)})"
                )
            else:  # single placement
                entity = self.entities_by_id[pattern["entities"][0]]
                code_lines.append(f"# Place individual {pattern['type']}")
                code_lines.append(
                    f"game.move_to(Position(x=origin.x+{entity.position['x']}, y=origin.y+{entity.position['y']}))"
                )
                code_lines.append(
                    f"game.place_entity({self._name_to_prototype_string(pattern['type'])}, "
                    f"position=Position(x=origin.x+{entity.position['x']}, y=origin.y+{entity.position['y']}), "
                    f"direction={self._direction_to_enum(entity.direction)})"
                )
            code_lines.append("")

        return "\n".join(code_lines)


# get execution dir dynamically
execution_dir = os.path.dirname(os.path.realpath(__file__)) + "/blueprints/mining/"
filename = "1a. Mining"

with open(execution_dir + filename + ".json", "r") as f:
    blueprint_json = f.read()
    analyzer = BlueprintAnalyzer(blueprint_json)
    code = analyzer.generate_placement_code()
    print(code)
