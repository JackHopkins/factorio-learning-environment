
#!/usr/bin/env python3
"""
Extended sprite extractor for Factorio decoratives
"""

import json
import os
import shutil
from pathlib import Path
from PIL import Image
from typing import Dict, List, Optional, Tuple, Any


class DecorativeSpriteExtractor:
    """Extract and process resource sprites and tree layers"""

    def __init__(self, decoratives_path: str, output_dir: str = "images"):
        self.decoratives_path = Path(decoratives_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)

        self.output_dir_hr = Path(output_dir+"-hr")
        self.output_dir_hr.mkdir(exist_ok=True, parents=True)

    def extract_decorative_sprite(self, decorative_name: str):
        """Extract individual sprites from a resource sprite sheet"""
        decorative_dir = self.decoratives_path / decorative_name

        if not decorative_dir.exists():
            print(f"Decorative directory not found: {decorative_dir}")
            return


        # Process both normal and high-res versions
        for variant in range(99):
            for prefix in ['', 'hr-']:
                sprite_path = decorative_dir / f"{prefix}{decorative_name}-{str(variant).zfill(2)}.png"

                if not sprite_path.exists():
                    continue

                try:
                    sprite = Image.open(sprite_path).convert('RGBA')
                    if prefix == 'hr-':
                        output_path = self.output_dir_hr / f"{decorative_name}_{variant}.png"
                    else:
                        output_path = self.output_dir / f"{decorative_name}_{variant}.png"

                    sprite.save(output_path)
                    print(f"Saved: {output_path}")

                except Exception as e:
                    print(f"Error processing {sprite}: {e}")

    def extract_all_decoratives(self):
        """Extract all resource sprites"""
        print("=== Extracting Decorative Sprites ===")

        # Extract sprite sheets for mineral resources
        for _, decorative_names, _ in os.walk(self.decoratives_path):
            for decorative_name in decorative_names:
                print(f"\nProcessing decoratives: {decorative_names}")
                self.extract_decorative_sprite(decorative_name)

        print("\n=== Extracting Tree Sprites ===")

