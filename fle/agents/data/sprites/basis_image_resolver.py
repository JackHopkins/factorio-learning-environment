#!/usr/bin/env python3
"""
Enhanced Image Resolver that handles .basis files for Factorio sprites
"""

import os
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from PIL import Image
from typing import Optional, Dict, Any, Tuple


class BasisImageResolver:
    """Image resolver that handles both PNG and .basis files"""

    def __init__(self, data_dir: str, cache_dir: str = None):
        """
        Initialize the image resolver

        Args:
            data_dir: Path to the data/rendering directory
            cache_dir: Directory for cached PNG files (default: data_dir/cache)
        """
        self.data_dir = Path(data_dir)
        self.base_graphics_dir = self.data_dir / "__base__" / "graphics"

        if cache_dir is None:
            self.cache_dir = self.data_dir / "cache"
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(exist_ok=True)
        self.image_cache = {}

        # Load entity data for sprite lookups
        self.entity_data = self._load_entity_data()

    def _load_entity_data(self) -> Dict[str, Any]:
        """Load data.json for entity information"""
        data_file = self.data_dir / "data.json"
        if data_file.exists():
            with open(data_file, 'r') as f:
                return json.load(f)
        return {}

    def _find_sprite_file(self, sprite_name: str) -> Optional[Path]:
        """
        Find the sprite file for a given name, checking various locations

        Args:
            sprite_name: Name of the sprite (e.g., 'stone-furnace', 'boiler_north')

        Returns:
            Path to the sprite file (.basis or .png), or None if not found
        """
        # Clean up sprite name
        clean_name = sprite_name.replace("_shadow", "")
        is_shadow = "_shadow" in sprite_name

        # Handle different sprite naming patterns
        search_patterns = []

        # Entity-specific sprites (e.g., boiler_north -> boiler-N-idle)
        if "_" in clean_name:
            parts = clean_name.split("_")
            entity_name = parts[0]
            direction = parts[1] if len(parts) > 1 else ""

            # Direction mapping
            dir_map = {
                "north": "N",
                "east": "E",
                "south": "S",
                "west": "W",
                "up": "N",
                "right": "E",
                "down": "S",
                "left": "W"
            }

            dir_letter = dir_map.get(direction, direction.upper()[:1])

            # Common entity sprite patterns
            if is_shadow:
                search_patterns.extend([
                    f"entity/{entity_name}/{entity_name}-{dir_letter}-shadow",
                    f"entity/{entity_name}/hr-{entity_name}-{dir_letter}-shadow",
                ])
            else:
                search_patterns.extend([
                    f"entity/{entity_name}/{entity_name}-{dir_letter}-idle",
                    f"entity/{entity_name}/{entity_name}-{dir_letter}",
                    f"entity/{entity_name}/hr-{entity_name}-{dir_letter}-idle",
                    f"entity/{entity_name}/hr-{entity_name}-{dir_letter}",
                ])

        # Icon sprites (e.g., icon_stone-furnace)
        if clean_name.startswith("icon_"):
            icon_name = clean_name[5:]  # Remove 'icon_' prefix
            search_patterns.extend([
                f"icons/{icon_name}",
                f"icons/hr-{icon_name}",
            ])

        # Pipe sprites
        if clean_name.startswith("pipe_"):
            pipe_type = clean_name[5:]  # Remove 'pipe_' prefix
            search_patterns.extend([
                f"entity/pipe/{pipe_type}",
                f"entity/pipe/hr-{pipe_type}",
                f"entity/pipe-covers/{pipe_type}",
                f"entity/pipe-covers/hr-{pipe_type}",
            ])

        # Heat pipe sprites
        if "heat-pipe" in clean_name:
            heat_pipe_type = clean_name.replace("heat-pipe_", "")
            search_patterns.extend([
                f"entity/heat-pipe/{heat_pipe_type}",
                f"entity/heat-pipe/hr-{heat_pipe_type}",
            ])

        # Transport belt sprites
        if any(belt in clean_name for belt in ["transport-belt", "fast-transport-belt", "express-transport-belt"]):
            belt_parts = clean_name.split("_")
            if len(belt_parts) >= 2:
                belt_name = belt_parts[0]
                belt_type = belt_parts[1] if len(belt_parts) > 1 else ""
                search_patterns.extend([
                    f"entity/{belt_name}/{belt_name}",
                    f"entity/{belt_name}/hr-{belt_name}",
                    f"entity/{belt_name}/{belt_type}",
                    f"entity/{belt_name}/hr-{belt_type}",
                ])

        # Generic entity pattern
        search_patterns.extend([
            f"entity/{clean_name}/{clean_name}",
            f"entity/{clean_name}/hr-{clean_name}",
            f"icons/{clean_name}",
            f"icons/hr-{clean_name}",
        ])

        # Check each pattern for .basis and .png files
        for pattern in search_patterns:
            for ext in [".basis", ".png"]:
                file_path = self.base_graphics_dir / (pattern + ext)
                if file_path.exists():
                    return file_path

        return None

    def _get_cached_png_path(self, sprite_name: str) -> Path:
        """Get the path where the cached PNG should be stored"""
        return self.cache_dir / f"{sprite_name}.png"

    def _transcode_basis_to_png(self, basis_path: Path, output_path: Path) -> bool:
        """
        Transcode a .basis file to PNG using basisu

        Args:
            basis_path: Path to the .basis file
            output_path: Path where PNG should be saved

        Returns:
            True if successful, False otherwise
        """
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Run basisu transcoder
                cmd = ["basisu", "-unpack", str(basis_path)]
                result = subprocess.run(
                    cmd,
                    cwd=temp_path,
                    capture_output=True,
                    text=True
                )

                if result.returncode != 0:
                    print(f"basisu failed for {basis_path.name}: {result.stderr}")
                    return False

                # Find the generated PNG
                possible_patterns = [
                    "*_unpacked_rgba_BC7_RGBA_0_0000.png",
                    "*_unpacked_rgba_BC3_RGBA_0_0000.png",
                    "*_unpacked_rgba_ETC2_RGBA_0_0000.png",
                    "*_unpacked_rgba_*_0_0000.png",
                ]

                generated_png = None
                for pattern in possible_patterns:
                    matches = list(temp_path.glob(pattern))
                    if matches:
                        generated_png = matches[0]
                        break

                if not generated_png or not generated_png.exists():
                    print(f"No suitable PNG generated from {basis_path}")
                    return False

                # Copy to output location
                shutil.copy2(generated_png, output_path)
                return True

        except Exception as e:
            print(f"Error transcoding {basis_path}: {e}")
            return False

    def __call__(self, sprite_name: str, shadow: bool = False) -> Optional[Image.Image]:
        """
        Resolve sprite by name, handling .basis transcoding if needed

        Args:
            sprite_name: Name of the sprite
            shadow: Whether this is a shadow sprite

        Returns:
            PIL Image object, or None if not found
        """
        # Adjust name for shadow
        if shadow and not sprite_name.endswith("_shadow"):
            sprite_name = f"{sprite_name}_shadow"

        # Check memory cache first
        if sprite_name in self.image_cache:
            return self.image_cache[sprite_name]

        # Check file cache
        cached_png = self._get_cached_png_path(sprite_name)
        if cached_png.exists():
            try:
                image = Image.open(cached_png).convert("RGBA")
                self.image_cache[sprite_name] = image
                return image
            except Exception as e:
                print(f"Error loading cached sprite {sprite_name}: {e}")

        # Find the sprite file
        sprite_path = self._find_sprite_file(sprite_name)
        if not sprite_path:
            print(f"Sprite not found: {sprite_name}")
            return None

        # Handle based on file type
        if sprite_path.suffix == ".png":
            try:
                image = Image.open(sprite_path).convert("RGBA")
                self.image_cache[sprite_name] = image
                return image
            except Exception as e:
                print(f"Error loading PNG {sprite_path}: {e}")
                return None

        elif sprite_path.suffix == ".basis":
            # Transcode to PNG
            if self._transcode_basis_to_png(sprite_path, cached_png):
                try:
                    image = Image.open(cached_png).convert("RGBA")
                    self.image_cache[sprite_name] = image
                    return image
                except Exception as e:
                    print(f"Error loading transcoded sprite {sprite_name}: {e}")

        return None

    def preload_entity_sprites(self, entity_names: list):
        """Preload sprites for a list of entities"""
        print("Preloading entity sprites...")
        for entity_name in entity_names:
            # Try common variations
            variations = [
                entity_name,
                f"{entity_name}-north",
                f"{entity_name}-east",
                f"{entity_name}-south",
                f"{entity_name}-west",
                f"icon_{entity_name}",
            ]

            for variant in variations:
                sprite = self(variant, False)
                if sprite:
                    print(f"  ✓ {variant}")
                    # Also try shadow
                    shadow = self(variant, True)
                    if shadow:
                        print(f"  ✓ {variant}_shadow")

    def _find_sprite_file_tree_extension(self, sprite_name: str) -> Optional[Path]:
        """
        Extension to handle tree sprite patterns.
        Add this logic to the existing _find_sprite_file method.
        """
        search_patterns = []

        # Tree sprites (e.g., tree-01-a-full, tree-01-a-full-shadow)
        if sprite_name.startswith("tree-"):
            parts = sprite_name.split("-")
            if len(parts) >= 4:
                tree_type = parts[1]  # 01, 02, etc.
                variation = parts[2]  # a, b, c, etc.
                state = "-".join(parts[3:])  # full, medium, minimal, trunk_only, or full-shadow

                # Handle shadow sprites
                if state.endswith("-shadow"):
                    base_state = state[:-7]  # Remove -shadow
                    # Shadows are in the tree type folder
                    search_patterns.extend([
                        f"tree/{tree_type}/tree-{tree_type}-{variation}-{base_state}-shadow",
                        f"tree/{tree_type}/hr-tree-{tree_type}-{variation}-{base_state}-shadow",
                        f"tree/{tree_type}/tree-{tree_type}-{variation}-shadow",  # Fallback
                        f"tree/{tree_type}/hr-tree-{tree_type}-{variation}-shadow",
                    ])
                else:
                    # Regular tree sprites
                    search_patterns.extend([
                        f"tree/{tree_type}/tree-{tree_type}-{variation}-{state}",
                        f"tree/{tree_type}/hr-tree-{tree_type}-{variation}-{state}",
                    ])

        # Dead tree sprites (e.g., dead-tree-desert-01)
        elif "dead-tree" in sprite_name or "dry-tree" in sprite_name or "dead-dry-hairy-tree" in sprite_name:
            # These are stored in their specific folders
            tree_type = "-".join(sprite_name.split("-")[:-1])  # Everything except the number
            variant_num = sprite_name.split("-")[-1] if sprite_name[-1].isdigit() else "00"

            search_patterns.extend([
                f"tree/{tree_type}/{sprite_name}",
                f"tree/{tree_type}/hr-{sprite_name}",
            ])

        # Dead grey trunk sprites
        elif "dead-grey-trunk" in sprite_name:
            search_patterns.extend([
                f"tree/dead-grey-trunk/{sprite_name}",
                f"tree/dead-grey-trunk/hr-{sprite_name}",
            ])

        # Dry hairy tree sprites
        elif "dry-hairy-tree" in sprite_name:
            search_patterns.extend([
                f"tree/dry-hairy-tree/{sprite_name}",
                f"tree/dry-hairy-tree/hr-{sprite_name}",
            ])

        # Resource sprites (e.g., coal_1_8, iron-ore_3_5)
        elif "_" in sprite_name and any(resource in sprite_name for resource in
                                        ["coal", "copper-ore", "iron-ore", "stone", "uranium-ore", "crude-oil"]):
            parts = sprite_name.split("_")
            if len(parts) == 3:
                resource_name = parts[0]
                variant = parts[1]
                volume = parts[2]

                # Resources are in the resources folder, not base graphics
                resource_patterns = [
                    f"../../resources/{resource_name}/{resource_name}_{variant}_{volume}",
                    f"../../resources/{resource_name}/hr-{resource_name}_{variant}_{volume}",
                ]

                # Check resource patterns with data_dir as base
                for pattern in resource_patterns:
                    for ext in [".png"]:  # Resources are typically PNG after extraction
                        file_path = self.data_dir / pattern.lstrip("../../") / ext
                        if file_path.exists():
                            return file_path

        return search_patterns

    # Also add this helper method to handle the new sprite locations
    def _check_sprite_locations_extended(self, search_patterns: list) -> Optional[Path]:
        """
        Check additional locations for sprites beyond base graphics.
        This handles sprites that might be in the extracted spritemaps directory.
        """
        # First check the standard locations
        for pattern in search_patterns:
            for ext in [".png"]:  # Extracted sprites are PNG
                # Check in the spritemaps directory (where extracted sprites are saved)
                if hasattr(self, 'spritemaps_dir'):
                    file_path = self.spritemaps_dir / (pattern + ext)
                    if file_path.exists():
                        return file_path

                # Check relative to data directory
                file_path = self.data_dir / (pattern + ext)
                if file_path.exists():
                    return file_path

        return None