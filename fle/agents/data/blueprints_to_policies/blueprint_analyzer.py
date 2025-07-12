import json
import os
from collections import defaultdict
from typing import List, Dict
from typing import Union

from fle.env import EntityGroup
from fle.env import FactorioInstance
from fle.env.game_types import prototype_by_name
from data.blueprints_to_policies.models.blueprint_entity import BlueprintEntity


class BlueprintAnalyzer:
    def __init__(self, blueprint: Dict):
        self.blueprint = blueprint
        self.entities = [
            BlueprintEntity(**entity) for entity in self.blueprint["entities"]
        ]

        # Calculate true bounding box
        self.min_x = min(e.position["x"] for e in self.entities)
        self.min_y = min(e.position["y"] for e in self.entities)
        self.max_x = max(e.position["x"] for e in self.entities)
        self.max_y = max(e.position["y"] for e in self.entities)

        # scale the positions of the entities
        for entity in self.entities:
            entity.position["x"] = entity.position["x"] - self.min_x
            entity.position["y"] = entity.position["y"] - self.min_y

    def find_patterns(self):
        # Group entities by type and x-coordinate for vertical patterns
        vertical_groups = defaultdict(list)
        horizontal_groups = defaultdict(list)

        for entity in self.entities:
            key = (entity.name, entity.direction)
            x = round(entity.position["x"] * 2) / 2  # Round to nearest 0.5
            y = round(entity.position["y"] * 2) / 2

            # Group by x-coordinate for vertical patterns
            vertical_groups[(key, x)].append(entity)

            # Group by y-coordinate for horizontal patterns
            horizontal_groups[(key, y)].append(entity)

        vertical_patterns = []
        horizontal_patterns = []
        used_entities = set()

        # Find vertical patterns (3 or more entities with same x and consistent y spacing)
        for (name_dir, x), entities in vertical_groups.items():
            if len(entities) >= 3:
                entities.sort(key=lambda e: e.position["y"])
                step = (
                    round((entities[1].position["y"] - entities[0].position["y"]) * 2)
                    / 2
                )

                if all(
                    round(
                        (entities[i + 1].position["y"] - entities[i].position["y"]) * 2
                    )
                    / 2
                    == step
                    for i in range(len(entities) - 1)
                ):
                    vertical_patterns.append(
                        {
                            "type": "vertical",
                            "name": name_dir[0],
                            "direction": name_dir[1],
                            "x": x,
                            "start_y": entities[0].position["y"],
                            "step": step,
                            "count": len(entities),
                        }
                    )
                    used_entities.update(e.entity_number for e in entities)

        # Find horizontal patterns
        for (name_dir, y), entities in horizontal_groups.items():
            if len(entities) >= 3:
                entities.sort(key=lambda e: e.position["x"])
                step = (
                    round((entities[1].position["x"] - entities[0].position["x"]) * 2)
                    / 2
                )

                if all(
                    round(
                        (entities[i + 1].position["x"] - entities[i].position["x"]) * 2
                    )
                    / 2
                    == step
                    for i in range(len(entities) - 1)
                ):
                    horizontal_patterns.append(
                        {
                            "type": "horizontal",
                            "name": name_dir[0],
                            "direction": name_dir[1],
                            "y": y,
                            "start_x": entities[0].position["x"],
                            "step": step,
                            "count": len(entities),
                        }
                    )
                    used_entities.update(e.entity_number for e in entities)

        # Collect remaining entities
        singles = [e for e in self.entities if e.entity_number not in used_entities]

        return vertical_patterns, horizontal_patterns, singles

    def get_inventory(self):
        entity_counts = {}
        for entity in self.entities:
            entity_counts[entity.name] = entity_counts.get(entity.name, 0) + 1
        return entity_counts

    def _get_hash(self) -> str:
        # we get the pairwise dx and dy between all entities
        # we then sort the pairs by dx and dy
        # we then hash the sorted pairs
        # this should give us a unique hash for each blueprint

        pairs = []
        for i in range(len(self.entities)):
            for j in range(len(self.entities)):
                dx = self.entities[i].position["x"] - self.entities[j].position["x"]
                dy = self.entities[i].position["y"] - self.entities[j].position["y"]
                pairs.append((int(dx * 2), int(dy * 2)))

        pairs.sort()
        return hash(tuple(pairs)), pairs

    def verify_placement(
        self, game_entities: List[Union[BlueprintEntity, EntityGroup]]
    ) -> bool:
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

    def generate_program(self) -> str:
        vertical_patterns, horizontal_patterns, singles = self.find_patterns()
        miners = [e for e in self.entities if "mining-drill" in e.name]
        if miners:
            origin_calc = f"game.nearest_buildable({self._name_to_prototype_string(miners[0].name)}, bounding_box=miner_box)"
        else:
            origin_calc = f"game.nearest_buildable({self._name_to_prototype_string(self.entities[0].name)}, bounding_box=miner_box)"

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
            f"origin = {origin_calc}",
            "",
            "assert origin, 'Could not find valid position'",
            "origin = origin + left_top + Position(x=0.5, y=0.5)",
            "game.move_to(origin)",
            "",
        ]

        # Track entity counters for variable names
        entity_counters = defaultdict(int)
        entity_vars = []

        def get_entity_var_name(entity_name: str) -> str:
            """Generate a unique variable name for an entity"""
            clean_name = entity_name.replace("-", "_")
            entity_counters[clean_name] += 1
            return f"{clean_name}_{entity_counters[clean_name]}"

        # Generate vertical patterns
        for pattern in vertical_patterns:
            array_name = f"{pattern['name'].replace('-', '_')}_vertical"
            lines.extend(
                [
                    f"# Place {pattern['name']} vertically at x={pattern['x']:.1f}",
                    f"{array_name} = []",
                    f"for i in range({pattern['count']}):",
                    f"    world_y = {pattern['start_y']:.1f} + ({pattern['step']:.1f} * i) + origin.y",
                    f"    world_x = {pattern['x']:.1f} + origin.x",
                    "    game.move_to(Position(x=world_x+1, y=world_y))",
                    f"    entity = game.place_entity({self._name_to_prototype_string(pattern['name'])}, "
                    f"position=Position(x=world_x, y=world_y), "
                    f"direction={self._direction_to_enum(pattern['direction'])}, "
                    f"exact=True)",
                    f"    {array_name}.append(entity)",
                    "",
                ]
            )
            entity_vars.append(array_name)

        # Generate horizontal patterns
        for pattern in horizontal_patterns:
            array_name = f"{pattern['name'].replace('-', '_')}_horizontal"
            lines.extend(
                [
                    f"# Place {pattern['name']} horizontally at y={pattern['y']:.1f}",
                    f"{array_name} = []",
                    f"for i in range({pattern['count']}):",
                    f"    world_x = {pattern['start_x']:.1f} + ({pattern['step']:.1f} * i) + origin.x",
                    f"    world_y = {pattern['y']:.1f} + origin.y",
                    "    game.move_to(Position(x=world_x, y=world_y+1))",
                    f"    entity = game.place_entity({self._name_to_prototype_string(pattern['name'])}, "
                    f"position=Position(x=world_x, y=world_y), "
                    f"direction={self._direction_to_enum(pattern['direction'])}, "
                    f"exact=True)",
                    f"    {array_name}.append(entity)",
                    "",
                ]
            )
            entity_vars.append(array_name)

        # Order placement of entities by left to right
        singles.sort(key=lambda e: e.position["x"])

        # Generate individual placements
        for entity in singles:
            var_name = get_entity_var_name(entity.name)
            lines.extend(
                [
                    f"# Place individual {entity.name}",
                    f"game.move_to(Position(x=origin.x + {entity.position['x']:.1f}+1, "
                    f"y=origin.y + {entity.position['y']:.1f}))",
                    f"{var_name} = game.place_entity({self._name_to_prototype_string(entity.name)}, "
                    f"position=Position(x=origin.x + {entity.position['x']:.1f}, "
                    f"y=origin.y + {entity.position['y']:.1f}), "
                    f"direction={self._direction_to_enum(entity.direction)}, "
                    f"exact=True)",
                    "",
                ]
            )
            entity_vars.append(var_name)

            # Add recipe setting if recipe exists
            if entity.recipe:
                lines.append(
                    f"game.set_entity_recipe({var_name}, "
                    f"Prototype.{prototype_by_name[entity.recipe].name})"
                )
                lines.append("")

        return "\n".join(lines)

    def _direction_to_enum(self, direction: int) -> str:
        direction_map = {0: "UP", 2: "RIGHT", 4: "DOWN", 6: "LEFT"}
        return f"Direction.{direction_map.get(direction, 'UP')}"

    def _name_to_prototype_string(self, name: str) -> str:
        return f"Prototype.{name.title().replace('-', '')}"


def analyze_blueprint(blueprint_json: str) -> str:
    analyzer = BlueprintAnalyzer(blueprint_json)
    return analyzer.generate_program(), analyzer.get_inventory()


execution_dir = os.path.dirname(os.path.realpath(__file__)) + "/blueprints/misc/"
filename = "1a. Mining"  # Early Mining"

# iterate over all json files in the directory
for filename in os.listdir(execution_dir):
    if filename.endswith(".json"):
        # skip if the python file exists
        if os.path.exists(execution_dir + filename.replace(".json", ".py")):
            continue
        with open(execution_dir + filename, "r") as f:
            print(filename)
            blueprint_json = f.read()
            blueprint = json.loads(blueprint_json)
            if len(blueprint["entities"]) > 200:
                print("Skipping large blueprint")
                continue
            analyzer = BlueprintAnalyzer(blueprint)
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
            with open(execution_dir + filename.replace(".json", ".py"), "w") as f1:
                f1.write(code)
