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

    # Test with the steel smelting blueprint (much better!)
    blueprint_path = Path("data/vqa/blueprint.example.json")

    if not blueprint_path.exists():
        print(f"❌ Blueprint file not found: {blueprint_path}")
        return None

    print(f"🎮 Loading blueprint: {blueprint_path}")

    with open(blueprint_path, "r") as f:
        blueprint_data = json.load(f)

    entities = blueprint_data.get("entities", [])
    print(f"📊 Blueprint contains {len(entities)} entities")

    # Create renderer with entities
    renderer = Renderer(entities=entities)

    try:
        # Get size and render
        size = renderer.get_size()
        width = (size["width"] + 2) * 32
        height = (size["height"] + 2) * 32

        print(f"📏 Render size: {width}x{height} pixels")

        # Create image resolver and render
        image_resolver = ImageResolver(".fle/sprites")
        rendered_image = renderer.render(width, height, image_resolver)

        if rendered_image:
            # Save the rendered image
            output_path = "steel_smelting_blueprint_rendered.png"
            rendered_image.save(output_path)
            print(f"✅ Rendered blueprint saved to: {output_path}")
            print(f"📏 Image size: {rendered_image.width}x{rendered_image.height}")
            return output_path
        else:
            print("❌ Failed to render blueprint")
            return None

    except Exception as e:
        print(f"❌ Error rendering blueprint: {e}")
        return None


def test_simple_blueprint():
    """Test with a simple blueprint to compare"""

    # Simple test blueprint
    simple_entities = [
        {"name": "transport-belt", "position": {"x": 0, "y": 0}, "direction": 0},
        {"name": "electric-mining-drill", "position": {"x": 2, "y": 0}, "direction": 0},
        {"name": "inserter", "position": {"x": 1, "y": 1}, "direction": 2},
    ]

    print("🎮 Testing simple blueprint...")

    renderer = Renderer(entities=simple_entities)

    try:
        # Get size and render
        size = renderer.get_size()
        width = (size["width"] + 2) * 32
        height = (size["height"] + 2) * 32

        print(f"📏 Render size: {width}x{height} pixels")

        image_resolver = ImageResolver(".fle/sprites")
        rendered_image = renderer.render(width, height, image_resolver)

        if rendered_image:
            output_path = "simple_blueprint_rendered.png"
            rendered_image.save(output_path)
            print(f"✅ Simple blueprint saved to: {output_path}")
            return output_path
        else:
            print("❌ Failed to render simple blueprint")
            return None

    except Exception as e:
        print(f"❌ Error rendering simple blueprint: {e}")
        return None


if __name__ == "__main__":
    print("🚀 Testing Factorio Blueprint Renderer")
    print("=" * 50)

    # Test the steel smelting blueprint
    result1 = test_blueprint_rendering()

    print("\n" + "=" * 50)

    # Test simple blueprint for comparison
    result2 = test_simple_blueprint()

    print("\n" + "=" * 50)
    print("📋 Summary:")
    if result1:
        print(f"✅ Steel smelting blueprint: {result1}")
    if result2:
        print(f"✅ Simple blueprint: {result2}")

    print("🎉 Rendering tests completed!")
