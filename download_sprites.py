#!/usr/bin/env python3
"""
Simple script to download Factorio sprites
"""

import sys
from pathlib import Path

# Add the sprites directory to the path
sys.path.append(str(Path(__file__).parent / "fle" / "agents" / "data" / "sprites"))

try:
    from download import download_sprites_from_hf, generate_sprites

    print("🎮 Downloading Factorio sprites...")

    # Download sprites from Hugging Face
    success = download_sprites_from_hf(
        repo_id="Noddybear/fle_images",
        output_dir=".fle/spritemaps",
        force=False,
        num_workers=5,
    )

    if success:
        print("✅ Sprites downloaded successfully!")

        # Generate individual sprites from spritemaps
        print("🔧 Generating individual sprites...")
        generate_success = generate_sprites(
            input_dir=".fle/spritemaps", output_dir=".fle/sprites"
        )

        if generate_success:
            print("✅ Individual sprites generated successfully!")
        else:
            print("❌ Failed to generate individual sprites")
    else:
        print("❌ Failed to download sprites")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you have the required dependencies installed:")
    print("  pip install huggingface_hub tqdm requests")
except Exception as e:
    print(f"❌ Error: {e}")
