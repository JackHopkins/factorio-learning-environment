#!/usr/bin/env python3
"""
Utility to transcode .basis files to PNG images for Factorio entities.
Handles entity name lookups and sprite path resolution.
"""

import os
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from PIL import Image
from typing import Optional, Dict, Any


class BasisTranscoder:
    """Transcodes .basis files to PNG images for Factorio entities"""
    
    def __init__(self, data_dir: str = None):
        """
        Initialize the transcoder
        
        Args:
            data_dir: Path to the data/rendering directory
        """
        if data_dir is None:
            data_dir = Path(__file__).parent
        
        self.data_dir = Path(data_dir)
        self.cache_dir = self.data_dir / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        # Load Factorio data for entity lookups
        self.factorio_data = self._load_factorio_data()
        
    def _load_factorio_data(self) -> Dict[str, Any]:
        """Load the data.json file containing entity information"""
        data_file = self.data_dir / "data.json"
        if not data_file.exists():
            raise FileNotFoundError(f"data.json not found at {data_file}")
            
        with open(data_file, 'r') as f:
            return json.load(f)
    
    def _find_basis_file(self, entity_name: str) -> Optional[Path]:
        """
        Find the .basis file for a given entity name
        
        Args:
            entity_name: Name of the entity (e.g., 'stone-furnace')
            
        Returns:
            Path to the .basis file, or None if not found
        """
        # Try icons first (most common for entities)
        icon_path = self.data_dir / "__base__" / "graphics" / "icons" / f"{entity_name}.basis"
        if icon_path.exists():
            return icon_path
            
        # Try entity graphics directory
        entity_path = self.data_dir / "__base__" / "graphics" / "entity" / entity_name / f"{entity_name}.basis"
        if entity_path.exists():
            return entity_path
            
        # Try HR version
        hr_entity_path = self.data_dir / "__base__" / "graphics" / "entity" / entity_name / f"hr-{entity_name}.basis"
        if hr_entity_path.exists():
            return hr_entity_path
            
        return None
    
    def _get_cached_png_path(self, entity_name: str) -> Path:
        """Get the path where the cached PNG should be stored"""
        return self.cache_dir / f"{entity_name}.png"
    
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
            # Create temporary directory for basisu output
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
                    print(f"basisu failed: {result.stderr}")
                    return False
                
                # Find the generated RGBA PNG (best quality)
                # Look for BC7_RGBA format first (high quality), then fallback to others
                possible_patterns = [
                    f"*_unpacked_rgba_BC7_RGBA_0_0000.png",
                    f"*_unpacked_rgba_BC3_RGBA_0_0000.png", 
                    f"*_unpacked_rgba_ETC2_RGBA_0_0000.png",
                    f"*_unpacked_rgba_*_0_0000.png",
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
    
    def get_entity_sprite(self, entity_name: str, force_refresh: bool = False) -> Optional[Image.Image]:
        """
        Get the PNG sprite for an entity, transcoding from .basis if needed
        
        Args:
            entity_name: Name of the entity (e.g., 'stone-furnace')
            force_refresh: If True, re-transcode even if cached version exists
            
        Returns:
            PIL Image object, or None if sprite not found
        """
        # Check cache first
        cached_png = self._get_cached_png_path(entity_name)
        
        if not force_refresh and cached_png.exists():
            try:
                return Image.open(cached_png).convert("RGBA")
            except Exception as e:
                print(f"Error loading cached sprite for {entity_name}: {e}")
                # Continue to re-transcode
        
        # Find the .basis file
        basis_path = self._find_basis_file(entity_name)
        if not basis_path:
            print(f"No .basis file found for entity: {entity_name}")
            return None
        
        # Transcode to PNG
        if not self._transcode_basis_to_png(basis_path, cached_png):
            print(f"Failed to transcode {entity_name}")
            return None
        
        # Load and return the image
        try:
            return Image.open(cached_png).convert("RGBA")
        except Exception as e:
            print(f"Error loading transcoded sprite for {entity_name}: {e}")
            return None
    
    def preload_common_entities(self):
        """Preload sprites for common entities to speed up rendering"""
        common_entities = [
            "stone-furnace", "iron-chest", "wooden-chest", "transport-belt",
            "inserter", "burner-inserter", "small-electric-pole", "pipe",
            "assembling-machine-1", "boiler", "steam-engine", "offshore-pump",
            "burner-mining-drill", "electric-mining-drill", "iron-ore",
            "copper-ore", "coal", "stone"
        ]
        
        print("Preloading common entity sprites...")
        for entity_name in common_entities:
            sprite = self.get_entity_sprite(entity_name)
            if sprite:
                print(f"  ✓ {entity_name}")
            else:
                print(f"  ✗ {entity_name}")


def main():
    """Test the transcoder"""
    transcoder = BasisTranscoder()
    
    # Test with stone furnace
    sprite = transcoder.get_entity_sprite("stone-furnace")
    if sprite:
        print(f"Successfully loaded stone-furnace sprite: {sprite.size}")
        sprite.save("test_stone_furnace.png")
        print("Saved test_stone_furnace.png")
    else:
        print("Failed to load stone-furnace sprite")


if __name__ == "__main__":
    main()