# renderers/tree.py
"""
Tree renderer for various tree types including dead trees
"""

from typing import Dict, Tuple, Optional, Callable, Set
from PIL import Image
import re


def render(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render tree based on type and position"""
    tree_name = entity['name']
    x = entity['position']['x']
    y = entity['position']['y']

    # Get available trees from grid (passed from main renderer)
    available_trees = getattr(grid, 'available_trees', {})

    # Handle dead trees differently (they don't have variations)
    if 'dead' in tree_name or 'dry' in tree_name:
        # Dead trees use numbered sprites
        tree_parts = tree_name.split('-')
        if len(tree_parts) >= 3:
            # e.g., "dead-tree-desert" -> use position to pick 00-09
            num_variants = 10  # Adjust based on actual dead tree variants
            variant_num = abs(int(x + y * 7)) % num_variants
            sprite_name = f"{tree_name}-{variant_num:02d}"
        else:
            sprite_name = tree_name
    else:
        # Regular trees with foliage states
        # Extract tree type number from name (e.g., "tree-01" -> "01")
        tree_type = tree_name.split('-')[-1] if '-' in tree_name else '01'

        variation, foliage_state = get_tree_variant(x, y, tree_type, available_trees)

        sprite_name = f"tree-{tree_type}-{variation}-{foliage_state}"

    return image_resolver(sprite_name, False)


def render_shadow(entity: Dict, grid, image_resolver: Callable) -> Optional[Image.Image]:
    """Render tree shadow"""
    tree_name = entity['name']
    x = entity['position']['x']
    y = entity['position']['y']

    # Get available trees from grid (passed from main renderer)
    available_trees = getattr(grid, 'available_trees', {})

    # Dead trees might have different shadow naming
    if 'dead' in tree_name or 'dry' in tree_name:
        tree_parts = tree_name.split('-')
        if len(tree_parts) >= 3:
            num_variants = 10
            variant_num = abs(int(x + y * 7)) % num_variants
            shadow_name = f"{tree_name}-{variant_num:02d}_shadow"
        else:
            shadow_name = f"{tree_name}_shadow"
    else:
        # Regular trees
        tree_type = tree_name.split('-')[-1] if '-' in tree_name else '01'
        variation, foliage_state = get_tree_variant(x, y, tree_type, available_trees)

        # Regular trees append -shadow to the full sprite name
        shadow_name = f"tree-{tree_type}-{variation}-{foliage_state}-shadow"

    return image_resolver(shadow_name, False)


def get_key(entity: Dict, grid) -> str:
    """Get cache key for tree based on position"""
    x = entity['position']['x']
    y = entity['position']['y']

    # Use position to generate consistent key
    return f"{entity['name']}_{x}_{y}"


def get_size(entity: Dict) -> Tuple[float, float]:
    """Trees are typically larger than 1x1"""
    # Most trees are effectively 3x3 or 4x4 in terms of collision
    # But for rendering purposes, we use 1x1 positioning
    return (1, 1)


def get_tree_variant(x: float, y: float, tree_type: str, available_trees: Dict[str, Set[str]]) -> Tuple[str, str]:
    """
    Calculate tree variant and foliage state based on position.
    Returns (variation_letter, foliage_state)

    Args:
        x, y: Position coordinates
        tree_type: Type of tree (e.g., '03', '04', '05')
        available_trees: Dict mapping tree_type to set of available variation-state combinations
                        e.g., {'03': {'a-full', 'a-medium', 'a-minimal', 'b-full', ...}}
    """
    # Use position-based hash for deterministic randomness
    seed = int((x * 113 + y * 157) * (x - y) * 31 + x * y * 73 + hash(tree_type) * 17)

    # Add fine-grained position sensitivity
    position_hash = int((x * 1000) % 97 + (y * 1000) % 89 + ((x + y) * 1000) % 83)
    seed = seed * 29 + position_hash

    # Common tree variations (assuming a-l based on file structure)
    variations = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l']

    # Get available variations for this tree type
    available_for_type = available_trees.get(tree_type, set())

    # Extract unique variations that are available (have any states)
    valid_variations = []
    for var in variations:
        # Check if this variation has any states available
        has_any_state = any(f"{var}-" in combo for combo in available_for_type)
        if has_any_state:
            valid_variations.append(var)

    # If no valid variations, use default
    if not valid_variations:
        valid_variations = ['a']  # Default fallback

    # Select variation using deterministic randomness
    variation_index = seed % len(valid_variations)
    variation = valid_variations[variation_index]

    # Foliage states with weighted probability (more full trees)
    foliage_weights = [
        ('full', 70),  # 70% chance
        ('medium', 25),  # 25% chance
        ('minimal', 5),  # 5% chance
        ('trunk_only', 0)  # 0% chance (adjusted from original)
    ]

    # Calculate weighted random choice
    total_weight = sum(w for _, w in foliage_weights)
    choice = (seed // len(variations)) % total_weight

    cumulative = 0
    foliage_state = 'full'
    for state, weight in foliage_weights:
        cumulative += weight
        if choice < cumulative:
            foliage_state = state
            break

    # Verify the selected combination exists
    if f"{variation}-{foliage_state}" not in available_for_type:
        # Fall back to any available state for this variation
        for state in ['full', 'medium', 'minimal', 'trunk_only']:
            if f"{variation}-{state}" in available_for_type:
                foliage_state = state
                break
        else:
            # If still no valid state, pick the first available state for this variation
            for combo in available_for_type:
                if combo.startswith(f"{variation}-"):
                    foliage_state = combo.split('-', 1)[1]
                    break

    return variation, foliage_state


def is_tree_entity(entity_name: str) -> bool:
    """Check if an entity is a tree"""
    return (entity_name.startswith('tree-') or
            'dead-tree' in entity_name or
            'dry-tree' in entity_name or
            'dead-grey-trunk' in entity_name)


def build_available_trees_index(sprites_dir) -> Dict[str, Set[str]]:
    """
    Build an index of available tree sprites.

    Returns a dict mapping tree type to available variation-state combinations.
    Only includes variations that have exactly 10 files (complete set).
    e.g., {'03': {'a-full', 'a-medium', 'a-minimal', 'b-full', ...}}
    """
    from pathlib import Path

    # First pass: count files for each tree type and variation
    file_counts = {}
    all_files = {}

    # Pattern to match tree sprite files
    # Matches: tree-03-a-full.png, hr-tree-03-a-full.png, etc.
    tree_pattern = re.compile(r'^(?:hr-)?tree-(\d+)-([a-l])-(\w+)\.png$')

    sprites_dir = Path(sprites_dir)
    for sprite_file in sprites_dir.glob('*.png'):
        match = tree_pattern.match(sprite_file.name)
        if match:
            tree_type = match.group(1)
            variation = match.group(2)
            state = match.group(3)

            # Skip shadow files in our count
            if state.endswith('-shadow'):
                continue

            # Count files per tree type and variation
            key = (tree_type, variation)
            if key not in file_counts:
                file_counts[key] = 0
                all_files[key] = []

            file_counts[key] += 1
            all_files[key].append((state, sprite_file.name))

    # Second pass: only include variations with exactly 10 files
    available_trees = {}

    for (tree_type, variation), count in file_counts.items():
        if count == 10:  # Only complete sets with exactly 10 files
            if tree_type not in available_trees:
                available_trees[tree_type] = set()

            # Add all states for this variation
            for state, _ in all_files[(tree_type, variation)]:
                available_trees[tree_type].add(f"{variation}-{state}")
        else:
            print(f"Skipping tree-{tree_type}-{variation}: has {count} files instead of 10")

    return available_trees