"""Utility functions for the rendering system."""

import json
import base64
import zlib
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from .constants import (
    DEFAULT_MAX_RESOURCE_AMOUNT, MIN_RESOURCE_VOLUME, MAX_RESOURCE_VOLUME,
    DEFAULT_RESOURCE_VARIANTS, OIL_RESOURCE_VARIANTS
)


def entities_to_grid(entities: List[Dict]) -> Dict:
    """Convert entity list to position grid."""
    grid = {}
    for entity in entities:
        x = entity['position']['x']
        y = entity['position']['y']
        if x not in grid:
            grid[x] = {}
        grid[x][y] = entity
    return grid


def resources_to_grid(resources: List[Dict]) -> Dict:
    """Convert resource list to position grid."""
    grid = {}
    for resource in resources:
        x = resource['position']['x']
        y = resource['position']['y']
        if x not in grid:
            grid[x] = {}
        grid[x][y] = resource
    return grid


def get_resource_variant(x: float, y: float, max_variants: int = DEFAULT_RESOURCE_VARIANTS) -> int:
    """
    Calculate resource variant based on position using a hash-like function.
    Returns a variant number from 1 to max_variants.
    """
    hash_value = int(x * 7 + y * 13) % max_variants
    return hash_value + 1  # Variants are 1-indexed


def get_resource_volume(amount: int, max_amount: int = DEFAULT_MAX_RESOURCE_AMOUNT) -> int:
    """
    Calculate resource volume level (1-8) based on amount.
    8 = full, 1 = nearly empty
    """
    if amount <= 0:
        return MIN_RESOURCE_VOLUME

    percentage = min(amount / max_amount, 1.0)
    volume = max(MIN_RESOURCE_VOLUME, min(MAX_RESOURCE_VOLUME, int(percentage * MAX_RESOURCE_VOLUME)))
    return volume


def is_entity(entity: Optional[Dict], target: str) -> bool:
    """Check if entity matches target name."""
    if entity is None:
        return False
    return entity.get('name') == target


def is_entity_in_direction(entity: Optional[Dict], target: str, direction: int) -> bool:
    """Check if entity matches target name and direction."""
    if not is_entity(entity, target):
        return False
    return entity.get('direction', 0) == direction


def recipe_has_fluids(recipe: Dict) -> bool:
    """Check if recipe has fluid ingredients."""
    ingredients = recipe.get('ingredients') or recipe.get('normal', {}).get('ingredients', [])
    return any(ing.get('type') == 'fluid' for ing in ingredients)


def is_tree_entity(entity_name: str) -> bool:
    """Check if an entity is a tree."""
    return (
        entity_name.startswith('tree-') or
        'dead-tree' in entity_name or
        'dry-tree' in entity_name or
        'dead-grey-trunk' in entity_name
    )


def parse_blueprint(blueprint_string: str) -> Dict:
    """Parse blueprint string to JSON."""
    decoded = base64.b64decode(blueprint_string[1:])
    unzipped = zlib.decompress(decoded)
    return json.loads(unzipped)


def load_game_data(data_path: str) -> Tuple[Dict, Dict]:
    """Load game data from JSON file."""
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
        except AttributeError:
            pass

    return parsed, recipes


def find_fle_sprites_dir() -> Path:
    """Walk up the directory tree until we find .fle directory."""
    current = Path.cwd()

    while current != current.parent:
        fle_dir = current / ".fle"
        if fle_dir.exists() and fle_dir.is_dir():
            return fle_dir / "sprites"
        current = current.parent

    # Fallback - return the path even if it doesn't exist
    return Path.cwd() / ".fle" / "sprites"