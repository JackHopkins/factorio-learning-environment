#!/usr/bin/env python3
"""
Download specific entity sprites needed for rendering
"""

import shutil
from pathlib import Path
from huggingface_hub import hf_hub_download, list_repo_files
from tqdm import tqdm


def download_entity_sprites():
    """Download entity sprites needed for rendering"""

    # Entity sprites we need for our test blueprints
    needed_sprites = [
        "transport-belt",
        "electric-mining-drill",
        "inserter",
        "assembling-machine-1",
        "burner-mining-drill",
        "fast-inserter",
        "express-transport-belt",
        "fast-transport-belt",
        "filter-inserter",
        "tree-01",  # From sample blueprint
        "small-electric-pole",
        "character",
        "coal",  # Resource
        "iron-chest",
        "underground-belt",
    ]

    output_dir = Path(".fle/sprites")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("🎮 Downloading entity sprites...")

    # Get all available PNG files
    files = list_repo_files("Noddybear/fle_images", repo_type="dataset")
    png_files = [f for f in files if f.endswith(".png")]

    downloaded = 0

    for sprite_name in tqdm(needed_sprites, desc="Downloading sprites"):
        # Look for matching sprite files
        matching_files = [f for f in png_files if sprite_name in f.lower()]

        if matching_files:
            # Download the first matching file
            try:
                local_file = hf_hub_download(
                    repo_id="Noddybear/fle_images",
                    filename=matching_files[0],
                    repo_type="dataset",
                )

                # Copy to our sprites directory with simple name
                dest_path = output_dir / f"{sprite_name}.png"
                shutil.copy2(local_file, dest_path)
                downloaded += 1

            except Exception as e:
                print(f"❌ Failed to download {sprite_name}: {e}")
        else:
            print(f"⚠️  No sprite found for {sprite_name}")

    print(f"✅ Downloaded {downloaded}/{len(needed_sprites)} sprites")

    # Also download some basic sprites that might be needed
    basic_sprites = [
        "__base__/graphics/icons/transport-belt.png",
        "__base__/graphics/icons/electric-mining-drill.png",
        "__base__/graphics/icons/inserter.png",
    ]

    print("🔧 Downloading basic sprites...")
    for sprite_path in tqdm(basic_sprites, desc="Downloading basic sprites"):
        try:
            local_file = hf_hub_download(
                repo_id="Noddybear/fle_images",
                filename=sprite_path,
                repo_type="dataset",
            )

            # Extract simple name from path
            sprite_name = sprite_path.split("/")[-1].replace(".png", "")
            dest_path = output_dir / f"{sprite_name}.png"
            shutil.copy2(local_file, dest_path)

        except Exception as e:
            print(f"❌ Failed to download {sprite_path}: {e}")


if __name__ == "__main__":
    download_entity_sprites()
