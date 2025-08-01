#!/usr/bin/env python3
"""
Factorio Blueprint Renderer - Standalone Test Script
Renders Factorio blueprints and game states
"""

import json
from pathlib import Path

# Import the rendering components
from fle.env.tools.admin.render.renderer import Renderer
from fle.env.tools.admin.render.image_resolver import ImageResolver


def test_blueprint_rendering():
    """Test rendering existing blueprints from the repo"""

    # Test with the miner cycle blueprint
    blueprint_path = Path(
        "fle/agents/data/blueprints_to_policies/blueprints/example/miner_cycle.json"
    )

    if not blueprint_path.exists():
        print(f"❌ Blueprint file not found: {blueprint_path}")
        return None

    try:
        # Load the blueprint
        with open(blueprint_path, "r") as f:
            blueprint_data = json.load(f)

        print(f"📋 Loading blueprint: {blueprint_path}")
        print(f"   Entities: {len(blueprint_data['entities'])}")

        # Create renderer
        renderer = Renderer(
            entities=blueprint_data["entities"], sprites_dir=Path(".fle/sprites")
        )

        # Get size and render
        size = renderer.get_size()
        width = (size["width"] + 2) * 32
        height = (size["height"] + 2) * 32

        print(f"   Size: {size['width']}x{size['height']} tiles")
        print(f"   Render size: {width}x{height} pixels")

        image_resolver = ImageResolver(".fle/sprites")
        image = renderer.render(width, height, image_resolver)

        # Save result
        output_path = "miner_cycle_rendered.png"
        image.save(output_path)
        print(f"✅ Rendered blueprint saved as {output_path}")

        return image

    except Exception as e:
        print(f"❌ Error rendering blueprint: {e}")
        return None


def test_sample_blueprint_rendering():
    """Test rendering the sample blueprint with trees and resources"""

    # Test with the sample blueprint
    blueprint_path = Path("fle/agents/data/sprites/sample_blueprint.json")

    if not blueprint_path.exists():
        print(f"❌ Sample blueprint file not found: {blueprint_path}")
        return None

    try:
        # Load the blueprint
        with open(blueprint_path, "r") as f:
            blueprint_data = json.load(f)

        print(f"📋 Loading sample blueprint: {blueprint_path}")
        print(f"   Entities: {len(blueprint_data['entities'])}")
        print(f"   Resources: {len(blueprint_data.get('resources', []))}")
        print(f"   Water tiles: {len(blueprint_data.get('water_tiles', []))}")

        # Create renderer with all data
        renderer = Renderer(
            entities=blueprint_data["entities"],
            resources=blueprint_data.get("resources", []),
            water_tiles=blueprint_data.get("water_tiles", []),
            sprites_dir=Path(".fle/sprites"),
        )

        # Get size and render
        size = renderer.get_size()
        width = min((size["width"] + 2) * 32, 2048)  # Cap max width
        height = min((size["height"] + 2) * 32, 2048)  # Cap max height

        print(f"   Size: {size['width']}x{size['height']} tiles")
        print(f"   Render size: {width}x{height} pixels")

        image_resolver = ImageResolver(".fle/sprites")
        image = renderer.render(width, height, image_resolver)

        # Save result
        output_path = "sample_blueprint_rendered.png"
        image.save(output_path)
        print(f"✅ Sample blueprint saved as {output_path}")

        return image

    except Exception as e:
        print(f"❌ Error rendering sample blueprint: {e}")
        return None


def test_simple_blueprint():
    """Test rendering a simple custom blueprint"""

    # Simple test blueprint
    simple_blueprint = {
        "entities": [
            {"name": "transport-belt", "position": {"x": 0, "y": 0}, "direction": 0},
            {
                "name": "electric-mining-drill",
                "position": {"x": 2, "y": 0},
                "direction": 0,
            },
            {"name": "inserter", "position": {"x": 1, "y": 1}, "direction": 2},
        ]
    }

    try:
        print("📋 Testing simple custom blueprint")

        # Create renderer
        renderer = Renderer(
            entities=simple_blueprint["entities"], sprites_dir=Path(".fle/sprites")
        )

        # Get size and render
        size = renderer.get_size()
        width = (size["width"] + 2) * 32
        height = (size["height"] + 2) * 32

        print(f"   Size: {size['width']}x{size['height']} tiles")
        print(f"   Render size: {width}x{height} pixels")

        image_resolver = ImageResolver(".fle/sprites")
        image = renderer.render(width, height, image_resolver)

        # Save result
        output_path = "simple_blueprint_rendered.png"
        image.save(output_path)
        print(f"✅ Simple blueprint saved as {output_path}")

        return image

    except Exception as e:
        print(f"❌ Error rendering simple blueprint: {e}")
        return None


def main():
    """Main test function"""
    print("🎮 Testing Factorio Rendering Feature")
    print("=" * 40)

    # Test simple blueprint first
    print("\n🔧 Testing simple blueprint...")
    simple_image = test_simple_blueprint()

    # Test existing blueprints
    print("\n📋 Testing miner cycle blueprint...")
    miner_image = test_blueprint_rendering()

    print("\n🌳 Testing sample blueprint with trees/resources...")
    sample_image = test_sample_blueprint_rendering()

    print("\n✅ Rendering tests completed!")
    print("\n📁 Generated files:")
    if simple_image:
        print("   - simple_blueprint_rendered.png")
    if miner_image:
        print("   - miner_cycle_rendered.png")
    if sample_image:
        print("   - sample_blueprint_rendered.png")


if __name__ == "__main__":
    main()
