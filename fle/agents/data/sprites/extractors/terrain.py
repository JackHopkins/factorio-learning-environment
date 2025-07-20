#!/usr/bin/env python3
"""
Extended sprite extractor for Factorio resources and trees
Handles both sprite sheet extraction for resources and layer merging for trees
"""

import json
import os
import shutil
from pathlib import Path
from PIL import Image
from typing import Dict, List, Optional, Tuple, Any


class TerrainSpriteExtractor:
    """Extract and process resource sprites and tree layers"""

    def __init__(self, resources_path: str, output_dir: str = "images"):
        self.resources_path = Path(resources_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.output_dir_hr = Path(output_dir+"-hr")
        self.output_dir_hr.mkdir(exist_ok=True, parents=True)

        # Resource sprite sheet configurations
        self.resource_configs = {
            'water': {'columns': 4, 'rows': 1, 'width': 64, 'height': 64},
            'water-mud': {'columns': 4, 'rows': 1, 'width': 64, 'height': 64},
            'water-green': {'columns': 4, 'rows': 1, 'width': 64, 'height': 64},
            'water-shallow': {'columns': 4, 'rows': 1, 'width': 64, 'height': 64},
            'cliff-inner': {'columns': 8, 'rows': 2, 'width': 128, 'height': 256},
            'cliff-outer': {'columns': 8, 'rows': 2, 'width': 128, 'height': 256},
            'cliff-entrance': {'columns': 4, 'rows': 4, 'width': 128, 'height': 128},
            'cliff-sides': {'columns': 8, 'rows': 4, 'width': 128, 'height': 128},
        }

    def extract_resource_sprites(self, resource_name: str):
        """Extract individual sprites from a resource sprite sheet"""
        resource_dir = self.resources_path / resource_name

        if not resource_dir.exists():
            print(f"Resource directory not found: {resource_dir}")
            return

        config = self.resource_configs.get(resource_name, {
            'columns': 8, 'rows': 8, 'width': 64, 'height': 64
        })

        # Process both normal and high-res versions
        for prefix in ['', 'hr-']:
            sprite_sheet_path = resource_dir / f"{prefix}{resource_name}.png"

            if not sprite_sheet_path.exists():
                sprite_sheet_path = resource_dir / f"{prefix}{resource_name}1.png"
                if not sprite_sheet_path.exists():
                    continue

            try:
                sprite_sheet = Image.open(sprite_sheet_path).convert('RGBA')

                # Extract each sprite
                for row in range(config['rows']):
                    for col in range(config['columns']):
                        # Calculate position in sprite sheet
                        x = col * config['width']
                        y = row * config['height']

                        # Extract sprite
                        sprite = sprite_sheet.crop((
                            x, y,
                            x + config['width'],
                            y + config['height']
                        ))

                        # Save with naming convention: resource_variant_volume
                        # Row 0 = full volume (8), Row 7 = minimal volume (1)
                        volume = config['rows'] - row
                        variant = col + 1

                        output_name = f"{prefix}{resource_name}_{variant}_{volume}.png"
                        if prefix == 'hr-':
                            output_path = self.output_dir_hr / output_name
                        else:
                            output_path = self.output_dir / output_name
                        sprite.save(output_path)
                        print(f"Saved: {output_path}")

                # Also handle glow sprites for uranium
                if resource_name == 'uranium-ore':
                    glow_path = resource_dir / f"{prefix}uranium-ore-glow.png"
                    if glow_path.exists():
                        glow_sheet = Image.open(glow_path).convert('RGBA')

                        for row in range(config['rows']):
                            for col in range(config['columns']):
                                x = col * config['width']
                                y = row * config['height']

                                glow_sprite = glow_sheet.crop((
                                    x, y,
                                    x + config['width'],
                                    y + config['height']
                                ))

                                volume = config['rows'] - row
                                variant = col + 1

                                output_name = f"{prefix}uranium-ore-glow_{variant}_{volume}.png"
                                if prefix == 'hr-':
                                    output_path = self.output_dir_hr / output_name
                                else:
                                    output_path = self.output_dir / output_name
                                glow_sprite.save(output_path)
                                print(f"Saved glow: {output_path}")

            except Exception as e:
                print(f"Error processing {sprite_sheet_path}: {e}")

    def extract_all_resources(self):
        """Extract all resource sprites"""
        print("=== Extracting Resource Sprites ===")

        # Extract sprite sheets for mineral resources
        for resource_name in self.resource_configs.keys():
            print(f"\nProcessing resource: {resource_name}")
            self.extract_resource_sprites(resource_name)

        print("\n=== Extracting Tree Sprites ===")

    def create_resource_icon(self, resource_name: str):
        """Create a representative icon for each resource type using the first full variant"""
        try:
            # Use the first variant at full volume as the icon
            source_path = self.output_dir / f"{resource_name}_1_8.png"
            if source_path.exists():
                icon_path = self.output_dir / f"icon_{resource_name}.png"
                shutil.copy2(source_path, icon_path)
                print(f"Created icon: {icon_path}")

            # Also create HR version if available
            hr_source_path = self.output_dir / f"hr-{resource_name}_1_8.png"
            if hr_source_path.exists():
                hr_icon_path = self.output_dir / f"icon_hr-{resource_name}.png"
                shutil.copy2(hr_source_path, hr_icon_path)
                print(f"Created HR icon: {hr_icon_path}")

        except Exception as e:
            print(f"Error creating icon for {resource_name}: {e}")

    def create_all_icons(self):
        """Create icons for all resources"""
        print("\n=== Creating Resource Icons ===")
        for resource_name in self.resource_configs.keys():
            self.create_resource_icon(resource_name)
