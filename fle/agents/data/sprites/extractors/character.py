#!/usr/bin/env python3
"""
Character sprite extractor for Factorio character animations
Extracts individual character sprites from spritemaps with varying dimensions
Saves as: name_{variant}_{direction}.png where variant=column, direction=row
"""

from pathlib import Path
from PIL import Image
from typing import Tuple


class CharacterSpriteExtractor:
    """Extract character sprites from spritemaps"""

    def __init__(self, character_path: str, output_dir: str = "images"):
        self.character_path = Path(character_path)
        self.output_dir = Path(output_dir) / "character"
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # Create hr subdirectory
        self.output_dir_hr = Path(output_dir + "-hr") / "character"
        self.output_dir_hr.mkdir(exist_ok=True, parents=True)

        # Define the dimensions for each sprite sheet type
        # Format: (columns, rows)
        self.sprite_dimensions = {
            "level1_dead": (2, 1),
            "level2addon_dead": (2, 1),
            "level3addon_dead": (2, 1),
            "level1_idle": (22, 8),
            "level2addon_idle": (22, 8),
            "level3addon_idle": (22, 8),
            "level1_idle_gun": (22, 8),
            "level2addon_idle_gun": (22, 8),
            "level3addon_idle_gun": (22, 8),
            "level1_mining_tool": (13, 8),
            "level2addon_mining_tool": (13, 8),
            "level3addon_mining_tool": (13, 8),
            "level1_running": (22, 8),
            "level2addon_running": (22, 8),
            "level3addon_running": (22, 8),
            "level1_running_gun": (22, 18),
            "level2addon_running_gun": (22, 18),
            "level3addon_running_gun": (22, 18),
            "level1_running_mask": (22, 18),
            "level2addon_running_mask": (22, 18),
            "level3addon_running_mask": (22, 18),
            "level1_running_gun_mask": (22, 18),
            "level2addon_running_gun_mask": (22, 18),
            "level3addon_running_gun_mask": (22, 18),
            "level1_running_shadow": (10, 7),
            "level2addon_running_shadow": (10, 7),
            "level3addon_running_shadow": (10, 7),
            "level1_running_gun_shadow": (10, 7),
            "level2addon_running_gun_shadow": (10, 7),
            "level3addon_running_gun_shadow": (10, 7),
        }

        # Track detected sprite sizes for each type
        self.detected_sprite_sizes = {}

    def get_sprite_dimensions(self, sprite_name: str) -> Tuple[int, int]:
        """
        Get the expected dimensions for a sprite sheet.

        Args:
            sprite_name: Name of the sprite sheet (without hr- prefix and .png)

        Returns:
            Tuple of (columns, rows)
        """
        # Remove hr- prefix if present
        clean_name = sprite_name.replace("hr-", "")

        # Check direct match first
        if clean_name in self.sprite_dimensions:
            return self.sprite_dimensions[clean_name]

        # Check for base name without suffixes like -1, -2
        base_name = clean_name
        if base_name.endswith("-1") or base_name.endswith("-2"):
            base_name = base_name[:-2]

        if base_name in self.sprite_dimensions:
            return self.sprite_dimensions[base_name]

        # Handle mask/shadow variants
        for suffix in ["_mask", "_shadow", "_shadow-1", "_shadow-2"]:
            if base_name.endswith(suffix):
                check_name = base_name.replace(suffix, "")
                # For shadows/masks, check if we have a running variant
                if "running" in check_name and check_name in self.sprite_dimensions:
                    return self.sprite_dimensions[check_name]
                # Otherwise use the base sprite dimensions
                if check_name in self.sprite_dimensions:
                    return self.sprite_dimensions[check_name]

        # Default fallback for standard sprites
        if "running" in clean_name and ("gun" in clean_name or "mask" in clean_name):
            return (22, 18)  # Running with gun has more frames
        elif "running" in clean_name and "shadow" in clean_name:
            return (10, 7)  # Running shadows have fewer frames
        elif "dead" in clean_name:
            return (2, 1)  # Dead sprites are minimal
        elif "mining" in clean_name:
            return (13, 8)  # Mining has fewer directions
        else:
            return (22, 8)  # Default for most sprites

    def extract_sprites_from_sheet(self, sheet_path: Path, output_prefix: str):
        """
        Extract all sprites from a character sprite sheet.
        Saves as: name_{variant}_{direction}.png

        Args:
            sheet_path: Path to the sprite sheet
            output_prefix: Prefix for output files (e.g., "level1_idle")
        """
        if not sheet_path.exists():
            print(f"Sprite sheet not found: {sheet_path}")
            return

        try:
            sheet = Image.open(sheet_path).convert("RGBA")

            # Determine if this is an HR sprite
            is_hr = output_prefix.startswith("hr-")

            # Get expected dimensions for this sprite type
            sprite_name = sheet_path.stem  # filename without extension
            cols, rows = self.get_sprite_dimensions(sprite_name)

            # Calculate individual sprite dimensions
            sprite_width = sheet.width // cols
            sprite_height = sheet.height // rows

            # Store detected size
            self.detected_sprite_sizes[sprite_name] = {
                "sprite_size": (sprite_width, sprite_height),
                "grid_size": (cols, rows),
                "sheet_size": (sheet.width, sheet.height),
            }

            print(
                f"  {sprite_name}: {cols}x{rows} grid, sprite size {sprite_width}x{sprite_height}"
            )

            # Extract each sprite
            extracted_count = 0
            for row in range(rows):
                for col in range(cols):
                    # Calculate sprite position
                    x = col * sprite_width
                    y = row * sprite_height

                    # Extract sprite
                    sprite = sheet.crop((x, y, x + sprite_width, y + sprite_height))

                    # Create filename with variant_direction format
                    # Remove hr- prefix from output name if present
                    clean_prefix = output_prefix.replace("hr-", "")
                    output_name = f"{clean_prefix}_{col}_{row}.png"

                    # Save to appropriate directory
                    if is_hr:
                        output_path = self.output_dir_hr / output_name
                    else:
                        output_path = self.output_dir / output_name

                    sprite.save(output_path)
                    extracted_count += 1

            print(
                f"    Extracted {extracted_count} sprites to {'hr' if is_hr else 'normal'} directory"
            )

        except Exception as e:
            print(f"Error processing {sheet_path}: {e}")
            import traceback

            traceback.print_exc()

    def extract_all_character_sprites(self):
        """Extract all character sprites from the character directory"""
        print("=== Extracting Character Sprites ===")

        if not self.character_path.exists():
            print(f"Character directory not found: {self.character_path}")
            return

        # Process all PNG files in the character directory
        png_files = list(self.character_path.glob("*.png"))

        # Group files by type for reporting
        file_groups = {
            "idle": [],
            "idle_gun": [],
            "running": [],
            "running_gun": [],
            "mining_tool": [],
            "dead": [],
            "masks": [],
            "shadows": [],
            "other": [],
        }

        # Categorize files
        for file_path in png_files:
            filename = file_path.name
            file_path.stem.replace("hr-", "")

            if "_mask" in filename:
                file_groups["masks"].append(file_path)
            elif "_shadow" in filename:
                file_groups["shadows"].append(file_path)
            elif "dead" in filename:
                file_groups["dead"].append(file_path)
            elif "mining_tool" in filename:
                file_groups["mining_tool"].append(file_path)
            elif "running_gun" in filename:
                file_groups["running_gun"].append(file_path)
            elif "running" in filename:
                file_groups["running"].append(file_path)
            elif "idle_gun" in filename:
                file_groups["idle_gun"].append(file_path)
            elif "idle" in filename:
                file_groups["idle"].append(file_path)
            else:
                file_groups["other"].append(file_path)

        # Process each group
        for group_name, files in file_groups.items():
            if files:
                print(f"\nProcessing {group_name} sprites ({len(files)} files)...")
                for file_path in sorted(files):
                    output_prefix = (
                        file_path.stem
                    )  # Keep the full name including hr- prefix
                    self.extract_sprites_from_sheet(file_path, output_prefix)

    def create_character_mapping(self):
        """
        Create a JSON mapping file for character sprites.
        Includes the varying dimensions for different sprite types.
        """
        import json

        # Direction mappings vary by sprite type
        standard_directions = {
            0: 0,  # North
            1: 1,  # North-East
            2: 2,  # East
            3: 3,  # South-East
            4: 4,  # South
            5: 5,  # South-West
            6: 6,  # West
            7: 7,  # North-West
        }

        # Mining tool has fewer directions (no diagonals)
        mining_directions = {
            0: 0,  # North
            2: 3,  # East (maps to column 3)
            4: 6,  # South (maps to column 6)
            6: 9,  # West (maps to column 9)
        }

        # Dead has only 2 directions
        dead_directions = {
            0: 0,  # North/South
            2: 1,  # East/West
            4: 0,  # South (same as North)
            6: 1,  # West (same as East)
        }

        mapping = {
            "sprite_dimensions": self.sprite_dimensions,
            "detected_sizes": self.detected_sprite_sizes,
            "direction_mappings": {
                "standard": standard_directions,
                "mining": mining_directions,
                "dead": dead_directions,
            },
            "sprite_types": {
                "idle": {
                    "sheets": ["level1_idle", "level2addon_idle", "level3addon_idle"],
                    "grid": (22, 8),
                    "directions": "standard",
                },
                "idle_gun": {
                    "sheets": [
                        "level1_idle_gun",
                        "level2addon_idle_gun",
                        "level3addon_idle_gun",
                    ],
                    "grid": (22, 8),
                    "directions": "standard",
                },
                "running": {
                    "sheets": [
                        "level1_running",
                        "level2addon_running",
                        "level3addon_running",
                    ],
                    "grid": (22, 8),
                    "directions": "standard",
                },
                "running_gun": {
                    "sheets": [
                        "level1_running_gun",
                        "level2addon_running_gun",
                        "level3addon_running_gun",
                    ],
                    "grid": (22, 18),
                    "directions": "standard",
                },
                "mining_tool": {
                    "sheets": [
                        "level1_mining_tool",
                        "level2addon_mining_tool",
                        "level3addon_mining_tool",
                    ],
                    "grid": (13, 8),
                    "directions": "mining",
                },
                "dead": {
                    "sheets": ["level1_dead", "level2addon_dead", "level3addon_dead"],
                    "grid": (2, 1),
                    "directions": "dead",
                },
            },
            "naming_format": "name_{variant}_{direction}.png where variant=column, direction=row",
        }

        # Save mapping in both directories
        for output_dir in [self.output_dir, self.output_dir_hr]:
            mapping_path = output_dir / "character_mapping.json"
            with open(mapping_path, "w") as f:
                json.dump(mapping, f, indent=2)
            print(f"Created character mapping: {mapping_path}")

    def extract_single_sprites(self):
        """
        Extract single sprites that aren't in sheets (like footprints).
        """
        single_sprites = ["footprints", "character-reflection"]

        print("\nExtracting single sprites...")
        for sprite_name in single_sprites:
            for prefix in ["", "hr-"]:
                filename = f"{prefix}{sprite_name}.png"
                file_path = self.character_path / filename

                if file_path.exists():
                    try:
                        sprite = Image.open(file_path).convert("RGBA")

                        # Save to appropriate directory
                        if prefix == "hr-":
                            output_path = self.output_dir_hr / f"{sprite_name}.png"
                        else:
                            output_path = self.output_dir / f"{sprite_name}.png"

                        sprite.save(output_path)
                        print(
                            f"  Copied {filename} to {'hr' if prefix else 'normal'} directory"
                        )
                    except Exception as e:
                        print(f"  Error copying {filename}: {e}")


def main():
    """Main entry point for character extraction"""
    import sys

    # Default paths
    character_path = "/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/.fle/spritemaps/__base__/graphics/entity/character"
    output_dir = "/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/.fle/sprites"

    # Allow command line overrides
    if len(sys.argv) > 1:
        character_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]

    print(f"Character path: {character_path}")
    print(f"Output path: {output_dir}")

    # Create extractor and run
    extractor = CharacterSpriteExtractor(character_path, output_dir)

    # Extract all sprites
    extractor.extract_all_character_sprites()

    # Extract single sprites
    extractor.extract_single_sprites()

    # Create mapping file
    extractor.create_character_mapping()

    print("\n=== Character Extraction Complete ===")


if __name__ == "__main__":
    main()
