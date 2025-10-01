"""Tests for vision/rendering functionality in the gym environment."""

import base64
import io
from PIL import Image

from fle.env.gym_env.environment import FactorioGymEnv
from fle.env.gym_env.action import Action


def test_vision_disabled_by_default(instance):
    """Test that vision is disabled by default and map_image is empty."""
    instance.reset()
    env = FactorioGymEnv(instance, pause_after_action=False)
    observation, _ = env.reset()

    # Verify map_image exists and is empty
    assert "map_image" in observation, "Observation should contain map_image field"
    assert observation["map_image"] == "", (
        "map_image should be empty when vision is disabled"
    )


def test_vision_enabled_produces_base64_image(instance):
    """Test that enabling vision produces a base64 encoded image."""
    instance.reset()
    env = FactorioGymEnv(instance, pause_after_action=False, enable_vision=True)
    observation, _ = env.reset()

    # Verify map_image exists and is not empty
    assert "map_image" in observation, "Observation should contain map_image field"
    assert observation["map_image"] != "", (
        "map_image should not be empty when vision is enabled"
    )
    assert isinstance(observation["map_image"], str), "map_image should be a string"

    # Verify it's valid base64
    try:
        image_data = base64.b64decode(observation["map_image"])
        img = Image.open(io.BytesIO(image_data))

        # Verify it's a valid image with reasonable dimensions
        assert img.width > 0, "Image should have positive width"
        assert img.height > 0, "Image should have positive height"
        assert img.mode in ["RGB", "RGBA"], (
            f"Image should be RGB or RGBA, got {img.mode}"
        )

        # Should be roughly 800x800 based on 20 tiles * 2 * 20 pixels/tile
        # Allow some margin for different render configurations
        assert 600 <= img.width <= 1000, (
            f"Image width {img.width} should be roughly 800px"
        )
        assert 600 <= img.height <= 1000, (
            f"Image height {img.height} should be roughly 800px"
        )

        print(f"Image size: {img.width}x{img.height}")

    except Exception as e:
        raise AssertionError(f"Failed to decode base64 image: {e}")


def test_vision_multimodal_api_format(instance):
    """Test that the base64 image is in the correct format for multimodal APIs."""
    instance.reset()
    env = FactorioGymEnv(instance, pause_after_action=False, enable_vision=True)
    observation, _ = env.reset()

    map_image_b64 = observation["map_image"]

    # Simulate creating a multimodal API message (GPT-4V / Claude format)
    # This is the format used by OpenAI and Anthropic
    message_content = [
        {"type": "text", "text": "What do you see in this Factorio factory?"},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{map_image_b64}"},
        },
    ]

    # Verify the structure is correct
    assert len(message_content) == 2
    assert message_content[1]["type"] == "image_url"
    assert message_content[1]["image_url"]["url"].startswith("data:image/png;base64,")

    # Verify the base64 portion is valid
    base64_part = message_content[1]["image_url"]["url"].split(",")[1]
    assert base64_part == map_image_b64

    # Verify it can be decoded
    try:
        decoded = base64.b64decode(base64_part)
        assert len(decoded) > 0, "Decoded image should have content"
    except Exception as e:
        raise AssertionError(f"Failed to decode base64 for API: {e}")

    print("✓ Image is correctly formatted for multimodal APIs")
    print(f"  Base64 length: {len(map_image_b64)} characters")
    print(f"  Decoded size: {len(decoded)} bytes")


def test_vision_persists_across_steps(instance):
    """Test that vision rendering works across multiple steps."""
    instance.initial_inventory = {"stone-furnace": 1}
    instance.reset()

    env = FactorioGymEnv(instance, pause_after_action=False, enable_vision=True)
    observation1, _ = env.reset()

    # First observation should have an image
    assert observation1["map_image"] != ""
    initial_image = observation1["map_image"]

    # Get player position from namespace
    player_pos = instance.namespaces[0].player_location

    # Place an entity and get a new observation
    action = Action(
        agent_idx=0,
        code=f"place_entity(Prototype.StoneFurnace, position=Position(x={player_pos.x + 5}, y={player_pos.y + 5}))",
        game_state=None,
    )
    observation2, _, _, _, _ = env.step(action)

    # Second observation should also have an image
    assert observation2["map_image"] != ""

    # Images should potentially be different (entity was placed)
    # But both should be valid base64
    assert len(observation2["map_image"]) > 100

    # Verify both are valid base64
    try:
        base64.b64decode(initial_image)
        base64.b64decode(observation2["map_image"])
    except Exception as e:
        raise AssertionError(f"Failed to decode images: {e}")
