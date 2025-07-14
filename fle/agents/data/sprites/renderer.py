#!/usr/bin/env python3
"""
Factorio Blueprint Renderer - Extended with Resource Support
Renders Factorio blueprints including resource patches
"""

import json
import base64
import zlib
import math
import re
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Set
import os

# Constants
DIRECTIONS = {
    0: "north",
    2: "east",
    4: "south",
    6: "west"
}

RELATIVE_DIRECTIONS = {
    0: "up",
    2: "right",
    4: "down",
    6: "left"
}

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
    "≤": "lte"
}

# Renderer mappings
RENDERERS = {
    "transport-belt": "transport-belt",
    "fast-transport-belt": "transport-belt",
    "express-transport-belt": "transport-belt",
    "underground-belt": "underground-belt",
    "fast-underground-belt": "underground-belt",
    "express-underground-belt": "underground-belt",
    "splitter": "splitter",
    "fast-splitter": "splitter",
    "express-splitter": "splitter",
    "pipe": "pipe",
    "pipe-to-ground": "pipe-to-ground",
    "stack-inserter": "inserter",
    "long-handed-inserter": "inserter",
    "fast-inserter": "inserter",
    "inserter": "inserter",
    "filter-inserter": "inserter",
    "stack-filter-inserter": "inserter",
    "burner-inserter": "inserter",
    "assembling-machine-1": "assembling-machine",
    "assembling-machine-2": "assembling-machine",
    "assembling-machine-3": "assembling-machine",
    "chemical-plant": "chemical-plant",
    "storage-tank": "storage-tank",
    "oil-refinery": "oil-refinery",
    "decider-combinator": "decider-combinator",
    "arithmetic-combinator": "arithmetic-combinator",
    "pump": "pump",
    "heat-pipe": "heat-pipe",
    "stone-wall": "stone-wall",
    "gate": "gate",
    "boiler": "boiler",
    "heat-exchanger": "heat-exchanger",
    "steam-engine": "steam-engine",
    "steam-turbine": "steam-turbine",
    "constant-combinator": "constant-combinator",
    "electric-mining-drill": "electric-mining-drill",
    "offshore-pump": "offshore-pump",
    "burner-mining-drill": "burner-mining-drill",
    "flamethrower-turret": "flamethrower-turret",
    "straight-rail": "straight-rail",
    "curved-rail": "curved-rail",
    "rail-signal": "rail-signal",
    "rail-chain-signal": "rail-signal",
    "tree-01": "tree",
    "tree-02": "tree",
    "tree-03": "tree",
    "tree-04": "tree",
    "tree-05": "tree",
    "tree-06": "tree",
    "tree-07": "tree",
    "tree-08": "tree",
    "tree-09": "tree",
    "dead-tree-desert": "tree",
    "dead-dry-hairy-tree": "tree",
    "dead-grey-trunk": "tree",
    "dry-hairy-tree": "tree",
    "dry-tree": "tree"
}


class EntityGridView:
    """View into the entity grid for relative lookups"""

    def __init__(self, grid: Dict, center_x: float, center_y: float, available_trees: Dict = None):
        self.grid = grid
        self.center_x = center_x
        self.center_y = center_y
        self.available_trees = available_trees or {}

    def get_relative(self, relative_x: float, relative_y: float) -> Optional[Dict]:
        """Get entity at relative position"""
        x = self.center_x + relative_x
        y = self.center_y + relative_y

        if x not in self.grid:
            return None
        return self.grid[x].get(y)

    def set_center(self, center_x: float, center_y: float):
        """Update center position"""
        self.center_x = center_x
        self.center_y = center_y


def entities_to_grid(entities: List[Dict]) -> Dict:
    """Convert entity list to position grid"""
    grid = {}
    for entity in entities:
        x = entity['position']['x']
        y = entity['position']['y']
        if x not in grid:
            grid[x] = {}
        grid[x][y] = entity
    return grid


def resources_to_grid(resources: List[Dict]) -> Dict:
    """Convert resource list to position grid"""
    grid = {}
    for resource in resources:
        x = resource['position']['x']
        y = resource['position']['y']
        if x not in grid:
            grid[x] = {}
        grid[x][y] = resource
    return grid


def get_resource_variant(x: float, y: float, max_variants: int = 8) -> int:
    """
    Calculate resource variant based on position using a hash-like function.
    Returns a variant number from 1 to max_variants.
    """
    # Use a simple hash-like function based on position
    # This ensures the same position always gets the same variant
    hash_value = int(x * 7 + y * 13) % max_variants
    return hash_value + 1  # Variants are 1-indexed


def get_resource_volume(amount: int, max_amount: int = 10000) -> int:
    """
    Calculate resource volume level (1-8) based on amount.
    8 = full, 1 = nearly empty
    """
    if amount <= 0:
        return 1

    # Calculate percentage and map to 1-8 scale
    percentage = min(amount / max_amount, 1.0)
    volume = max(1, min(8, int(percentage * 8)))

    return volume


def is_entity(entity: Optional[Dict], target: str) -> int:
    """Check if entity matches target name"""
    if entity is None:
        return 0
    return 1 if entity.get('name') == target else 0


def is_entity_in_direction(entity: Optional[Dict], target: str, direction: int) -> int:
    """Check if entity matches target name and direction"""
    if is_entity(entity, target):
        if entity.get('direction', 0) == direction:
            return 1
    return 0


def recipe_has_fluids(recipe: Dict) -> bool:
    """Check if recipe has fluid ingredients"""
    ingredients = recipe.get('ingredients') or recipe.get('normal', {}).get('ingredients', [])
    return any(ing.get('type') == 'fluid' for ing in ingredients)


def is_tree_entity(entity_name: str) -> bool:
    """Check if an entity is a tree"""
    return (entity_name.startswith('tree-') or
            'dead-tree' in entity_name or
            'dry-tree' in entity_name or
            'dead-grey-trunk' in entity_name)



class Renderer:
    """Factorio Blueprint representation"""

    def __init__(self, data: Dict, game_data: Dict, game_recipes: Dict, sprites_dir: Path):
        self.game_data = game_data
        self.game_recipes = game_recipes
        self.icons = []
        self.entities = data.get('entities', [])
        self.resources = data.get('resources', [])
        self.water_tiles = data.get('water_tiles', [])

        self.entity_grid = entities_to_grid(self.entities)
        self.resource_grid = resources_to_grid(self.resources)

        # Use provided sprites_dir or check common locations
        if sprites_dir is None:
            # Check for sprites in order of preference
            possible_dirs = [
                Path(".fle/sprites"),
                Path("sprites"),
                Path("images"),
            ]
            for dir_path in possible_dirs:
                if dir_path.exists():
                    sprites_dir = dir_path
                    break
            else:
                sprites_dir = Path(".fle/sprites")  # Default even if doesn't exist

        # Build available trees index - import from tree module
        from renderers.tree import build_available_trees_index
        self.available_trees = build_available_trees_index(sprites_dir)

        # Sort entities for rendering order
        self.entities.sort(key=lambda e: (
            not is_tree_entity(e['name']),  # Trees first (False < True)
            not e['name'].endswith('inserter'),
            e['position']['y'],
            e['position']['x']
        ))

    def get_size(self) -> Dict:
        """Calculate blueprint bounds including resources and trees"""
        min_width = min_height = 0
        max_width = max_height = 0

        # Check entities
        for entity in self.entities:
            pos = entity['position']
            size = get_entity_size(entity)
            min_width = min(min_width, pos['x'] - size[0] / 2)
            min_height = min(min_height, pos['y'] - size[1] / 2)
            max_width = max(max_width, pos['x'] + size[0] / 2)
            max_height = max(max_height, pos['y'] + size[1] / 2)

        # Check resources (they are 1x1)
        for resource in self.resources:
            pos = resource['position']
            min_width = min(min_width, pos['x'] - 0.5)
            min_height = min(min_height, pos['y'] - 0.5)
            max_width = max(max_width, pos['x'] + 0.5)
            max_height = max(max_height, pos['y'] + 0.5)

        return {
            'minX': min_width,
            'minY': min_height,
            'maxX': max_width,
            'maxY': max_height,
            'width': math.ceil(abs(min_width) + max_width),
            'height': math.ceil(abs(min_height) + max_height)
        }

    def render(self, width: int, height: int, image_resolver) -> Image.Image:
        """Render blueprint to image"""
        size = self.get_size()
        scaling = min(width / (size['width'] + 2), height / (size['height'] + 2))

        # Create image
        img = Image.new('RGB', (width, height), '#282828')
        draw = ImageDraw.Draw(img)

        # Draw grid
        line_width = 2
        for i in range(1, size['width'] + 2):
            x = i * scaling - line_width / 2
            draw.rectangle([x, 0, x + line_width, height], fill='#3c3c3c')

        for i in range(1, size['height'] + 2):
            y = i * scaling - line_width / 2
            draw.rectangle([0, y, width, y + line_width], fill='#3c3c3c')

        # Separate entities into trees and non-trees
        tree_entities = [e for e in self.entities if is_tree_entity(e['name'])]
        non_tree_entities = [e for e in self.entities if not is_tree_entity(e['name'])]

        # Create grid view
        grid_view = EntityGridView(self.entity_grid, 0, 0, self.available_trees)

        # First pass: render resources (they go under everything)
        for resource in self.resources:
            pos = resource['position']
            relative_x = pos['x'] + abs(size['minX']) + 0.5
            relative_y = pos['y'] + abs(size['minY']) + 0.5

            # Get variant and volume
            if resource['name'] == 'crude-oil':
                volume = 1
                variant = get_resource_variant(pos['x'], pos['y'], max_variants=4)
            else:
                volume = get_resource_volume(resource.get('amount', 10000))
                variant = get_resource_variant(pos['x'], pos['y'])

            # Get resource sprite
            resource_name = resource['name']
            sprite_name = f"{resource_name}_{variant}_{volume}"
            image = image_resolver(sprite_name, False)

            if image:
                start_x = int((relative_x * scaling + scaling / 2) - image.width / 2)
                start_y = int((relative_y * scaling + scaling / 2) - image.height / 2)
                img.paste(image, (start_x, start_y), image if image.mode == 'RGBA' else None)

        for water in self.water_tiles:
            pos = water
            relative_x = pos['x'] + abs(size['minX']) + 0.5
            relative_y = pos['y'] + abs(size['minY']) + 0.5

            # Get variant and volume
            volume = 1
            variant = get_resource_variant(pos['x'], pos['y'], max_variants=4)

            # Get resource sprite
            resource_name = water['name']
            sprite_name = f"{resource_name}_{variant}_{volume}"
            image = image_resolver(sprite_name, False)

            if image:
                start_x = int((relative_x * scaling + scaling / 2) - image.width / 2)
                start_y = int((relative_y * scaling + scaling / 2) - image.height / 2)
                img.paste(image, (start_x, start_y), image if image.mode == 'RGBA' else None)
            else:
                pass


        # Render tree shadows
        for tree in tree_entities:
            pos = tree['position']
            relative_x = pos['x'] + abs(size['minX']) + 0.5
            relative_y = pos['y'] + abs(size['minY']) + 0.5

            grid_view.set_center(pos['x'], pos['y'])

            # Use the tree renderer
            renderer = get_renderer(tree['name'])
            if renderer and hasattr(renderer, 'render_shadow'):
                shadow_image = renderer.render_shadow(tree, grid_view, image_resolver)

                if shadow_image:
                    start_x = int((relative_x * scaling + scaling / 2) - shadow_image.width / 2)
                    start_y = int((relative_y * scaling + scaling / 2) - shadow_image.height / 2)
                    img.paste(shadow_image, (start_x, start_y),
                              shadow_image if shadow_image.mode == 'RGBA' else None)

        # Render trees
        for tree in tree_entities:
            pos = tree['position']
            relative_x = pos['x'] + abs(size['minX']) + 0.5
            relative_y = pos['y'] + abs(size['minY']) + 0.5

            grid_view.set_center(pos['x'], pos['y'])

            # Use the tree renderer
            renderer = get_renderer(tree['name'])
            if renderer and hasattr(renderer, 'render'):
                tree_image = renderer.render(tree, grid_view, image_resolver)

                if tree_image:
                    start_x = int((relative_x * scaling + scaling / 2) - tree_image.width / 2)
                    start_y = int((relative_y * scaling + scaling / 2) - tree_image.height / 2)
                    img.paste(tree_image, (start_x, start_y), tree_image if tree_image.mode == 'RGBA' else None)

        # Second pass: shadows
        for entity in non_tree_entities:
            pos = entity['position']
            relative_x = pos['x'] + abs(size['minX']) + 0.5
            relative_y = pos['y'] + abs(size['minY']) + 0.5

            grid_view.set_center(pos['x'], pos['y'])

            image = None

            if entity['name'] in RENDERERS:
                renderer = get_renderer(entity['name'])
                if renderer and hasattr(renderer, 'render_shadow'):
                    image = renderer.render_shadow(entity, grid_view, image_resolver)
            else:
                image = image_resolver(entity['name'], True)

            if image:
                start_x = int((relative_x * scaling + scaling / 2) - image.width / 2)
                start_y = int((relative_y * scaling + scaling / 2) - image.height / 2)
                img.paste(image, (start_x, start_y), image if image.mode == 'RGBA' else None)
            else:
                pass

        # Third pass: rails (simplified)
        passes = [1, 2, 3, 3.5, 4, 5]
        for pass_num in passes:
            for entity in non_tree_entities:
                if entity['name'] not in ['straight-rail', 'curved-rail', 'rail-signal', 'rail-chain-signal']:
                    continue

                pos = entity['position']
                relative_x = pos['x'] + abs(size['minX']) + 0.5
                relative_y = pos['y'] + abs(size['minY']) + 0.5

                direction = entity.get('direction', 0)
                image = None

                # Handle rail rendering (simplified)
                if entity['name'] == 'straight-rail':
                    if direction in [0, 4]:
                        image = image_resolver(f"{entity['name']}_vertical_pass_{int(pass_num)}", False)
                    elif direction in [2, 6]:
                        image = image_resolver(f"{entity['name']}_horizontal_pass_{int(pass_num)}", False)
                    # Add diagonal cases as needed

                if image:
                    start_x = int((relative_x * scaling + scaling / 2) - image.width / 2)
                    start_y = int((relative_y * scaling + scaling / 2) - image.height / 2)
                    img.paste(image, (start_x, start_y), image if image.mode == 'RGBA' else None)

        # Fourth pass: entities
        for entity in non_tree_entities:
            if entity['name'] in ['straight-rail', 'curved-rail']:
                continue

            pos = entity['position']
            relative_x = pos['x'] + abs(size['minX']) + 0.5
            relative_y = pos['y'] + abs(size['minY']) + 0.5

            grid_view.set_center(pos['x'], pos['y'])

            image = None

            if entity['name'] == 'pipe-to-ground':
                pass
            if entity['name'] in RENDERERS:
                renderer = get_renderer(entity['name'])
                if renderer and hasattr(renderer, 'render'):
                    image = renderer.render(entity, grid_view, image_resolver)
            else:
                image = image_resolver(entity['name'], False)

            if image:
                start_x = int((relative_x * scaling + scaling / 2) - image.width / 2)
                start_y = int((relative_y * scaling + scaling / 2) - image.height / 2)
                img.paste(image, (start_x, start_y), image if image.mode == 'RGBA' else None)

        return img


def parse_blueprint(blueprint_string: str) -> Dict:
    """Parse blueprint string to JSON"""
    decoded = base64.b64decode(blueprint_string[1:])
    unzipped = zlib.decompress(decoded)
    return json.loads(unzipped)


def load_game_data(data_path: str) -> Tuple[Dict, Dict]:
    """Load game data from JSON file"""
    with open(data_path, 'r') as f:
        data = json.load(f)

    parsed = {}
    recipes = {}

    skip_categories = [
        'technology', 'item-subgroup', 'tutorial', 'simple-entity',
        'unit', 'simple-entity-with-force', 'rail-remnants', 'item-group',
        'particle', 'car', 'font', 'character-corpse', 'cargo-wagon',
        'ammo-category', 'ambient-sound', 'smoke', 'tree', 'corpse'
    ]

    for category, items in data.items():
        if category in skip_categories or category.endswith('achievement'):
            continue

        try:
            for entity_name, entity_data in items.items():
                if category == 'recipe':
                    recipes[entity_name] = entity_data
                else:
                    parsed[entity_name] = entity_data
        except AttributeError as e:
            pass

    return parsed, recipes


# Renderer cache
_renderer_cache = {}


def get_renderer(entity_name: str):
    """Get renderer module for entity"""
    renderer_name = RENDERERS.get(entity_name)
    if not renderer_name:
        return None

    if renderer_name not in _renderer_cache:
        # Import renderer module dynamically
        try:
            # Replace hyphens with underscores for module names
            module_name = renderer_name.replace("-", "_")
            module = __import__(f'renderers.{module_name}', fromlist=[''])
            _renderer_cache[renderer_name] = module
        except ImportError as e:
            print(f"Warning: Could not import renderer for {entity_name}: {e}")
            return None

    return _renderer_cache[renderer_name]


def get_entity_size(entity: Dict) -> Tuple[float, float]:
    """Get entity size"""
    renderer = get_renderer(entity['name'])
    if renderer and hasattr(renderer, 'get_size'):
        return renderer.get_size(entity)
    return (1, 1)


class ImageResolver:
    """Resolve image paths and load images (simple PNG-based resolver)"""

    def __init__(self, images_dir: str = "images"):
        self.images_dir = Path(images_dir)
        self.cache = {}

    def __call__(self, name: str, shadow: bool = False) -> Optional[Image.Image]:
        filename = f"{name}_shadow" if shadow else name

        if filename in self.cache:
            return self.cache[filename]

        path = self.images_dir / f"{filename}.png"
        if not path.exists():
            return None

        try:
            image = Image.open(path).convert('RGBA')
            self.cache[filename] = image
            return image
        except Exception:
            return None


def main():
    """Example usage"""
    # Set up paths
    sprites_dir = Path(".fle/spritemaps")

    # Try to import the enhanced resolver
    try:
        from basis_image_resolver import BasisImageResolver
        print("Using BasisImageResolver for .basis file support")
        # Load game data
        game_data, game_recipes = load_game_data(f".fle/spritemaps/data.json")

        image_resolver = ImageResolver(
            ".fle/spritemaps")

    except ImportError:
        print("BasisImageResolver not found, using simple PNG resolver")

        # Fallback to simple resolver
        game_data, game_recipes = load_game_data("data.json")
        image_resolver = ImageResolver(str(sprites_dir))

    with open("/sample_blueprint.json", "r") as f:
        blueprint_json = json.loads(f.read().strip())

    with open("/sample_blueprint.txt", "r") as f:
        blueprint_str = f.read().strip()

    blueprint = parse_blueprint(blueprint_str)['blueprint']
    # Parse blueprint - pass sprites_dir to Blueprint
    blueprint = Renderer(blueprint, game_data, game_recipes, sprites_dir)

    # Render blueprint
    size = blueprint.get_size()
    scaling = 32
    width = (size['width'] + 2) * scaling
    height = (size['height'] + 2) * scaling

    image = blueprint.render(width, height, image_resolver)
    image.save("output.png")
    image.show()
    print(f"Blueprint rendered to output.png ({width}x{height})")


if __name__ == "__main__":
    main()