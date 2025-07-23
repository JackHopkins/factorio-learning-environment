#!/usr/bin/env python3
"""
Icon sprite extractor for Factorio icons
Handles the layout where each successive icon is 50% the size of the previous
"""

import os
from pathlib import Path
from PIL import Image
from typing import Dict, List, Optional, Tuple


class IconSpriteExtractor:
    """Extract icon sprites from halving-size layout spritesheets"""

    def __init__(self, icons_path: str, output_dir: str = "images"):
        self.icons_path = Path(icons_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)

        self.output_dir_hr = Path(output_dir + "-hr")
        self.output_dir_hr.mkdir(exist_ok=True, parents=True)

    def extract_icon_from_spritesheet(self, icon_name: str):
        """
        Extract the primary (leftmost) icon from a halving-size layout spritesheet

        The layout is:
        - Left pane: Primary icon (full height)
        - Right pane upper half: Second icon (50% size)
        - Right pane upper-right quarter: Third icon (25% size)
        - And so on...
        """
        icon_file = self.icons_path / f"{icon_name}.png"
        icon_file_hr = self.icons_path / f"hr-{icon_name}.png"

        # Process both normal and high-res versions
        for is_hr, file_path in [(False, icon_file), (True, icon_file_hr)]:
            if not file_path.exists():
                continue

            try:
                spritesheet = Image.open(file_path).convert('RGBA')

                # The primary icon width can be determined by finding where
                # the halving pattern starts in the right side
                primary_width = self._find_primary_icon_width(spritesheet)

                if primary_width is None:
                    # Fallback: assume the primary icon is square (width = height)
                    primary_width = spritesheet.height

                # Extract the leftmost sprite (primary icon)
                primary_icon = spritesheet.crop((0, 0, primary_width, spritesheet.height))

                # Save the icon with 'icon_' prefix
                output_name = f"{'hr-' if is_hr else ''}icon_{icon_name}.png"
                if is_hr:
                    output_path = self.output_dir_hr / output_name
                else:
                    output_path = self.output_dir / output_name

                primary_icon.save(output_path)
                print(f"Saved icon: {output_path} (size: {primary_icon.width}x{primary_icon.height})")

            except Exception as e:
                print(f"Error processing {file_path}: {e}")

    def _find_primary_icon_width(self, image: Image.Image) -> Optional[int]:
        """
        Find the width of the primary icon by analyzing the image structure
        """
        width, height = image.size

        # Method 1: Look for a clear vertical division
        division = self._find_vertical_division(image)
        if division is not None:
            return division

        # Method 2: Check if the image follows the halving pattern
        # If total width = height + height/2, then primary width = height
        if abs(width - (height + height / 2)) < 5:  # Allow small tolerance
            return height

        # Method 3: Check for common icon sizes (powers of 2)
        common_sizes = [16, 32, 64, 128, 256, 512]
        for size in common_sizes:
            if height == size:
                # Check if remaining width could contain the halving pattern
                remaining = width - size
                if remaining >= size / 2:
                    return size

        return None

    def _find_vertical_division(self, image: Image.Image) -> Optional[int]:
        """
        Try to find a vertical division line in the image
        """
        width, height = image.size
        pixels = image.load()

        # Look for vertical lines that might be divisions
        # Start from expected positions based on square primary icon
        candidates = [height, int(height * 0.75), int(height * 1.25)]

        for x in candidates:
            if x < 10 or x >= width - 10:
                continue

            # Check if this x-coordinate forms a clear division
            is_division = True
            transparent_count = 0

            for y in range(0, height, 5):  # Sample every 5th pixel
                pixel = pixels[x, y]

                # Count transparent pixels
                if len(pixel) == 4 and pixel[3] < 10:
                    transparent_count += 1

            # If most pixels in this column are transparent, it's likely a division
            if transparent_count > height / 10:
                return x

        return None

    def extract_icon_from_single_file(self, icon_name: str):
        """
        Extract icon from a single file (not a spritesheet)
        Just copy it with the icon_ prefix
        """
        for prefix in ['', 'hr-']:
            input_file = self.icons_path / f"{prefix}{icon_name}.png"

            if not input_file.exists():
                continue

            try:
                # Just copy the file with icon_ prefix
                output_name = f"{prefix}icon_{icon_name}.png"
                if prefix == 'hr-':
                    output_path = self.output_dir_hr / output_name
                else:
                    output_path = self.output_dir / output_name

                # Copy the image
                image = Image.open(input_file).convert('RGBA')
                image.save(output_path)
                print(f"Saved icon: {output_path} (size: {image.width}x{image.height})")

            except Exception as e:
                print(f"Error processing {input_file}: {e}")

    def is_likely_spritesheet(self, file_path: Path) -> bool:
        """
        Determine if an icon file is likely a spritesheet based on its dimensions
        """
        try:
            image = Image.open(file_path)
            width, height = image.size

            # A spritesheet would be wider than tall
            if width <= height:
                return False

            # Check if width follows the pattern: height + height/2 + height/4 + ...
            # The minimum spritesheet would be height + height/2 = 1.5 * height
            if width >= height * 1.4:
                return True

            return False

        except Exception as e:
            print(f"Error checking {file_path}: {e}")
            return False

    def extract_all_icons(self):
        """Extract all icon sprites from the icons directory"""
        print("=== Extracting Icon Sprites ===")

        if not self.icons_path.exists():
            print(f"Icons directory not found: {self.icons_path}")
            return

        # Find all unique icon names (without hr- prefix and .png extension)
        icon_files = {}

        for file_path in self.icons_path.glob("*.png"):
            # Skip if it's not a PNG file
            if not file_path.suffix.lower() == '.png':
                continue

            # Get base name without hr- prefix
            base_name = file_path.stem
            is_hr = base_name.startswith('hr-')
            if is_hr:
                base_name = base_name[3:]  # Remove 'hr-' prefix

            if base_name not in icon_files:
                icon_files[base_name] = {'normal': None, 'hr': None}

            if is_hr:
                icon_files[base_name]['hr'] = file_path
            else:
                icon_files[base_name]['normal'] = file_path

        print(f"Found {len(icon_files)} unique icons to process")

        # Process each icon
        for icon_name, files in sorted(icon_files.items()):
            print(f"\nProcessing icon: {icon_name}")

            # Check if any version is a spritesheet
            is_spritesheet = False

            if files['normal'] and self.is_likely_spritesheet(files['normal']):
                is_spritesheet = True
            elif files['hr'] and self.is_likely_spritesheet(files['hr']):
                is_spritesheet = True

            if is_spritesheet:
                print(f"  Detected as spritesheet")
                self.extract_icon_from_spritesheet(icon_name)
            else:
                print(f"  Detected as single icon")
                self.extract_icon_from_single_file(icon_name)

    def create_icon_mappings(self):
        """
        Create a mapping file that lists all extracted icons
        Useful for referencing icons in the game
        """
        mapping = {}

        # Scan output directory for all icon files
        for file_path in self.output_dir.glob("icon_*.png"):
            icon_name = file_path.stem.replace('icon_', '')
            mapping[icon_name] = {
                'normal': str(file_path.name),
                'hr': None
            }

            # Check for HR version
            hr_path = self.output_dir_hr / f"hr-icon_{icon_name}.png"
            if hr_path.exists():
                mapping[icon_name]['hr'] = str(hr_path.name)

        # Save mapping as JSON
        import json
        mapping_path = self.output_dir / "icon_mapping.json"
        with open(mapping_path, 'w') as f:
            json.dump(mapping, f, indent=2, sort_keys=True)

        print(f"\nCreated icon mapping: {mapping_path}")
        print(f"Total icons extracted: {len(mapping)}")

    def debug_spritesheet_layout(self, icon_name: str):
        """
        Debug function to analyze and visualize the layout of a spritesheet
        """
        icon_file = self.icons_path / f"{icon_name}.png"

        if not icon_file.exists():
            print(f"Icon file not found: {icon_file}")
            return

        try:
            image = Image.open(icon_file)
            width, height = image.size

            print(f"\nAnalyzing spritesheet: {icon_name}")
            print(f"  Total dimensions: {width}x{height}")
            print(f"  Aspect ratio: {width / height:.2f}")

            # Check various possible primary icon widths
            print("\nPossible primary icon widths:")

            # Square primary icon
            if width >= height:
                print(f"  - Square icon: {height}x{height}")
                remaining = width - height
                print(f"    Remaining width: {remaining}")

                # Check if remaining follows halving pattern
                expected_remaining = height / 2 + height / 4 + height / 8
                print(f"    Expected remaining for halving pattern: {expected_remaining:.1f}")

            # Check common sizes
            for size in [16, 32, 64, 128, 256]:
                if height == size:
                    print(f"  - If primary is {size}x{size}:")
                    print(f"    Remaining: {width - size}")
                    print(f"    Could fit: {(width - size) / (size / 2):.1f} half-size icons")

        except Exception as e:
            print(f"Error analyzing {icon_file}: {e}")