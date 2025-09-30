#!/usr/bin/env python3
"""
Tree sprite extractor that handles composite sprites with foliage states
and shadow quadriptychs
"""

import shutil
from pathlib import Path
from typing import Optional

from PIL import Image


class TreeSpriteExtractor:
    """Extract tree sprites from composite images showing different foliage states"""

    def __init__(self, resources_path: str, output_dir: str = "images"):
        self.resources_path = Path(resources_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.output_dir_hr = Path(output_dir + "-hr")
        self.output_dir_hr.mkdir(exist_ok=True, parents=True)

    def extract_tree_states(self, tree_type: str):
        """Extract different foliage states from tree composites"""
        tree_dir = self.resources_path / "tree" / tree_type

        if not tree_dir.exists():
            print(f"Tree directory not found: {tree_dir}")
            return

        # Group files by variation and resolution
        tree_files = {}

        for file_path in tree_dir.glob("*.png"):
            filename = file_path.name

            # Parse filename to extract variation and layer type
            parts = filename.replace("hr-", "").replace(".png", "").split("-")

            if len(parts) >= 4:
                tree_num = parts[1]  # 01, 02, etc.
                variation = parts[2]  # a, b, c, etc.
                layer_type = parts[3]  # trunk, leaves, shadow, normal, stump

                is_hr = filename.startswith("hr-")
                key = (tree_num, variation, is_hr)

                if key not in tree_files:
                    tree_files[key] = {}

                tree_files[key][layer_type] = file_path

        # Process each tree variation
        for (tree_num, variation, is_hr), layers in tree_files.items():
            try:
                prefix = "hr-" if is_hr else ""

                # Process leaves if available
                if "leaves" in layers:
                    leaves_img = Image.open(layers["leaves"]).convert("RGBA")
                    aspect_ratio = leaves_img.width / leaves_img.height

                    # Check if leaves is a triptych (3x wide)
                    if aspect_ratio > 2:
                        print(
                            f"Processing triptych leaves for tree {tree_num}-{variation}"
                        )

                        # Load trunk if available (trunk is always single sprite)
                        trunk_img = None
                        if "trunk" in layers:
                            trunk_img = Image.open(layers["trunk"]).convert("RGBA")

                        extraction_successful = self._process_triptych_leaves(
                            leaves_img, trunk_img, tree_num, variation, prefix
                        )

                        # Skip shadows and stumps if extraction failed
                        if extraction_successful is False:
                            continue
                    else:
                        # Single leaves image
                        print(
                            f"Processing single leaves for tree {tree_num}-{variation}"
                        )
                        if "trunk" in layers:
                            trunk_img = Image.open(layers["trunk"]).convert("RGBA")
                            self._process_single_leaves(
                                leaves_img, trunk_img, tree_num, variation, prefix
                            )
                        else:
                            # Just save the leaves as full state
                            output_name = (
                                f"{prefix}tree-{tree_num}-{variation}-full.png"
                            )
                            if prefix == "hr-":
                                output_path = self.output_dir_hr / output_name
                            else:
                                output_path = self.output_dir / output_name
                            leaves_img.save(output_path)
                            print(f"Saved tree state: {output_path}")

                elif "trunk" in layers:
                    # Trunk only, no leaves
                    trunk_img = Image.open(layers["trunk"]).convert("RGBA")
                    output_name = f"{prefix}tree-{tree_num}-{variation}-trunk_only.png"
                    output_path = self.output_dir / output_name
                    trunk_img.save(output_path)
                    print(f"Saved trunk-only tree: {output_path}")

                # Extract shadow quadriptych if available
                if "shadow" in layers:
                    self._extract_shadow_states(
                        layers["shadow"], tree_num, variation, prefix
                    )

                # Save stump if available
                if "stump" in layers:
                    stump = Image.open(layers["stump"]).convert("RGBA")
                    output_name = f"{prefix}tree-{tree_num}-{variation}-stump.png"
                    if prefix == "hr-":
                        output_path = self.output_dir_hr / output_name
                    else:
                        output_path = self.output_dir / output_name
                    stump.save(output_path)
                    print(f"Saved stump: {output_path}")

            except Exception as e:
                print(f"Error processing tree {tree_num}-{variation}: {e}")

    def _process_triptych_leaves(
        self,
        leaves_triptych: Image.Image,
        trunk_img: Optional[Image.Image],
        tree_num: str,
        variation: str,
        prefix: str,
    ):
        """Process leaves that are in triptych format"""
        try:
            # Calculate dimensions for individual sprites
            triptych_width = leaves_triptych.width
            triptych_height = leaves_triptych.height
            sprite_width = triptych_width // 3
            sprite_height = triptych_height

            print(f"  Triptych dimensions: {triptych_width}x{triptych_height}")
            print(f"  Individual sprite dimensions: {sprite_width}x{sprite_height}")

            # Extract each foliage state
            foliage_states = ["full", "medium", "minimal"]

            # Determine final composite dimensions based on trunk and single sprite
            if trunk_img:
                composite_width = max(trunk_img.width, sprite_width)
                composite_height = max(trunk_img.height, sprite_height)
            else:
                composite_width = sprite_width
                composite_height = sprite_height

            # Store results temporarily
            temp_results = {}
            extraction_failed = False

            for i, state in enumerate(foliage_states):
                # Calculate region boundaries
                left = i * sprite_width
                upper = 0
                right = left + sprite_width
                lower = sprite_height

                print(
                    f"  Extracting {state} from region: ({left}, {upper}, {right}, {lower})"
                )

                # Use crop with explicit box tuple
                box = (left, upper, right, lower)
                sprite_region = leaves_triptych.crop(box)

                # Force a copy to ensure we have a separate image
                sprite_img = sprite_region.copy()

                # Verify the extraction worked
                if sprite_img.width == triptych_width:
                    print(
                        "  ERROR: Sprite still has triptych width! Trying alternative method..."
                    )
                    # Alternative: Create new image and paste the region
                    sprite_img = Image.new(
                        "RGBA", (sprite_width, sprite_height), (0, 0, 0, 0)
                    )
                    # Use the region as a paste source
                    sprite_img.paste(leaves_triptych, (-left, 0))

                print(
                    f"  Extracted {state} sprite: {sprite_img.width}x{sprite_img.height}"
                )

                # Double-check the extraction really worked
                if sprite_img.width >= triptych_width * 0.9:  # Allow 10% margin
                    print(
                        f"  CRITICAL ERROR: {state} sprite width {sprite_img.width} is too close to triptych width {triptych_width}"
                    )
                    extraction_failed = True
                    break

                if trunk_img:
                    # Create final composite
                    final_composite = Image.new(
                        "RGBA", (composite_width, composite_height), (0, 0, 0, 0)
                    )

                    # Center trunk
                    trunk_x = (composite_width - trunk_img.width) // 2
                    trunk_y = (composite_height - trunk_img.height) // 2
                    final_composite.paste(trunk_img, (trunk_x, trunk_y), trunk_img)

                    # Center foliage on top
                    foliage_x = (composite_width - sprite_width) // 2
                    foliage_y = (composite_height - sprite_height) // 2
                    final_composite.paste(
                        sprite_img, (foliage_x, foliage_y), sprite_img
                    )

                    result = final_composite
                else:
                    result = sprite_img

                # Store temporarily
                output_name = f"{prefix}tree-{tree_num}-{variation}-{state}.png"
                temp_results[state] = (output_name, result)

                # Final check on the composite
                if result.width >= triptych_width * 0.9:
                    print(
                        f"  CRITICAL ERROR: Final composite for {state} has width {result.width}, too close to triptych width {triptych_width}"
                    )
                    extraction_failed = True
                    break

            # Only save if extraction was successful
            if not extraction_failed:
                print("  All extractions successful, saving files...")

                # Save all sprites
                for state, (output_name, img) in temp_results.items():
                    if prefix == "hr-":
                        output_path = self.output_dir_hr / output_name
                    else:
                        output_path = self.output_dir / output_name
                    img.save(output_path)
                    print(
                        f"  Saved tree state: {output_path} (size: {img.width}x{img.height})"
                    )

                # Add trunk-only state if we have trunk
                if trunk_img:
                    # Create image with same dimensions as other sprites
                    trunk_only = Image.new(
                        "RGBA", (composite_width, composite_height), (0, 0, 0, 0)
                    )
                    trunk_x = (composite_width - trunk_img.width) // 2
                    trunk_y = (composite_height - trunk_img.height) // 2
                    trunk_only.paste(trunk_img, (trunk_x, trunk_y), trunk_img)

                    output_name = f"{prefix}tree-{tree_num}-{variation}-trunk_only.png"
                    if prefix == "hr-":
                        output_path = self.output_dir_hr / output_name
                    else:
                        output_path = self.output_dir / output_name
                    trunk_only.save(output_path)
                    print(
                        f"  Saved trunk-only state: {output_path} (size: {trunk_only.width}x{trunk_only.height})"
                    )
            else:
                print(
                    f"  WARNING: Skipping tree {tree_num}-{variation} due to extraction failure"
                )
                # Don't process shadows or stumps for failed extractions
                return

        except Exception as e:
            print(f"Error processing triptych leaves: {e}")
            import traceback

            traceback.print_exc()
            return

    def _process_single_leaves(
        self,
        leaves_img: Image.Image,
        trunk_img: Image.Image,
        tree_num: str,
        variation: str,
        prefix: str,
    ):
        """Process single leaves image with trunk"""
        try:
            # Create full state (trunk + leaves)
            width = max(trunk_img.width, leaves_img.width)
            height = max(trunk_img.height, leaves_img.height)

            full_state = Image.new("RGBA", (width, height), (0, 0, 0, 0))

            # Center trunk
            trunk_x = (width - trunk_img.width) // 2
            trunk_y = (height - trunk_img.height) // 2
            full_state.paste(trunk_img, (trunk_x, trunk_y), trunk_img)

            # Center leaves
            leaves_x = (width - leaves_img.width) // 2
            leaves_y = (height - leaves_img.height) // 2
            full_state.paste(leaves_img, (leaves_x, leaves_y), leaves_img)

            output_name = f"{prefix}tree-{tree_num}-{variation}-full.png"
            if prefix == "hr-":
                output_path = self.output_dir_hr / output_name
            else:
                output_path = self.output_dir / output_name
            full_state.save(output_path)
            print(f"  Saved tree state: {output_path}")

            # Create trunk-only state
            trunk_only = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            trunk_only.paste(trunk_img, (trunk_x, trunk_y), trunk_img)

            output_name = f"{prefix}tree-{tree_num}-{variation}-trunk_only.png"
            if prefix == "hr-":
                output_path = self.output_dir_hr / output_name
            else:
                output_path = self.output_dir / output_name
            trunk_only.save(output_path)
            print(f"  Saved trunk-only state: {output_path}")

        except Exception as e:
            print(f"Error processing single leaves: {e}")

    def _extract_shadow_states(
        self, shadow_path: Path, tree_num: str, variation: str, prefix: str
    ):
        """Extract shadow states from quadriptych (4 states, rotated 90° clockwise)"""
        try:
            shadow_quad = Image.open(shadow_path).convert("RGBA")

            quad_width = shadow_quad.width
            quad_height = shadow_quad.height
            shadow_width = quad_width // 4
            shadow_height = quad_height

            shadow_states = ["full", "medium", "minimal", "trunk_only"]

            for i, state in enumerate(shadow_states):
                # Extract shadow state
                x_offset = i * shadow_width
                shadow = shadow_quad.crop(
                    (x_offset, 0, x_offset + shadow_width, shadow_height)
                )

                output_name = f"{prefix}tree-{tree_num}-{variation}-{state}-shadow.png"

                if prefix == "hr-":
                    output_path = self.output_dir_hr / output_name
                else:
                    output_path = self.output_dir / output_name

                shadow.save(output_path)
                print(f"  Saved shadow state: {output_path}")

        except Exception as e:
            print(f"Error extracting shadow states: {e}")

    def extract_all_trees(self):
        """Extract all tree types"""
        print("=== Extracting Tree Sprites ===")

        tree_dir = self.resources_path / "tree"
        if tree_dir.exists():
            for tree_type_dir in tree_dir.iterdir():
                if tree_type_dir.is_dir():
                    tree_type = tree_type_dir.name
                    print(f"\nProcessing tree type: {tree_type}")

                    # Dead trees are handled differently
                    if "dead" in tree_type or "dry" in tree_type:
                        self._extract_dead_trees(tree_type)
                    else:
                        self.extract_tree_states(tree_type)

    def _extract_dead_trees(self, tree_type: str):
        """Extract dead tree sprites (these are typically single files)"""
        tree_dir = self.resources_path / "tree" / tree_type

        if not tree_dir.exists():
            print(f"Dead tree directory not found: {tree_dir}")
            return

        # Dead trees are usually single sprites, just copy them
        for file_path in tree_dir.glob("*.png"):
            try:
                if "hr-" in file_path.name:
                    output_path = self.output_dir_hr / file_path.name
                else:
                    output_path = self.output_dir / file_path.name
                shutil.copy2(file_path, output_path)
                print(f"  Copied dead tree: {output_path}")
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
