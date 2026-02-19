"""Test the vision rendering function to debug empty grid issue."""

import pytest
from fle.env import Prototype, Position


@pytest.fixture
def game_with_entities(instance):
    """Create a game with some entities to render."""
    game = instance
    game.reset()
    namespace = game.namespaces[0]
    # Move player to a known location
    namespace.move_to(Position(x=0, y=0))

    # Place some entities to ensure there's something to render
    namespace.place_entity(Prototype.IronChest, position=Position(x=2, y=0))
    namespace.place_entity(Prototype.IronChest, position=Position(x=4, y=0))
    namespace.place_entity(Prototype.StoneFurnace, position=Position(x=0, y=2))

    return game


def test_vision_render_basic(game_with_entities):
    """Test basic vision rendering."""
    game = game_with_entities
    namespace = game.namespaces[0]

    # Get player position
    player_pos = namespace.player_location
    print(f"\nPlayer position: ({player_pos.x}, {player_pos.y})")

    # Render with position explicitly set
    result = namespace._render(
        radius=64,
        max_render_radius=32,
        position=player_pos,
        include_status=True,
    )

    # Check viewport
    viewport = result.viewport
    print(f"Viewport center: ({viewport.center_x}, {viewport.center_y})")
    print(
        f"World bounds: ({viewport.world_min_x}, {viewport.world_min_y}) to ({viewport.world_max_x}, {viewport.world_max_y})"
    )
    print(f"Size: {viewport.width_tiles} x {viewport.height_tiles} tiles")
    print(f"Image: {viewport.image_width} x {viewport.image_height} pixels")

    # Check image is not empty
    img = result.image
    print(f"Image mode: {img.mode}, size: {img.size}")

    # Get pixel colors to check if image is just empty grid
    # Sample from the center of the image where entities are rendered,
    # not the top row which may land entirely on a grid line
    pixels = list(img.getdata())
    center_row = img.size[1] // 2
    center_start = center_row * img.size[0]
    center_pixels = pixels[center_start : center_start + img.size[0]]
    unique_colors = set(center_pixels)
    print(f"Unique colors in center row: {len(unique_colors)}")
    print(f"Sample colors: {list(unique_colors)[:5]}")

    # Show the image for visual inspection
    # result.show()

    # Assert image has content
    assert len(unique_colors) > 1, "Image appears to be single-color (empty)"


def test_vision_render_return_renderer(game_with_entities):
    """Test rendering with return_renderer to inspect entities."""
    game = game_with_entities.namespaces[0]

    player_pos = game.player_location

    # Render with return_renderer to inspect what entities were found
    result, renderer = game._render(
        radius=64,
        max_render_radius=32,
        position=player_pos,
        include_status=True,
        return_renderer=True,
    )

    # Check what entities the renderer found
    print(f"\nRenderer found {len(renderer.entities)} entities")

    # Print entity names
    entity_names = [e.name for e in renderer.entities[:20]]
    print(f"Entity names (first 20): {entity_names}")

    # Check for character
    character_entities = [e for e in renderer.entities if e.name == "character"]
    print(f"Character entities found: {len(character_entities)}")
    if character_entities:
        print(f"Character position: {character_entities[0].position}")

    # Check renderer offset
    print(f"Renderer offset: ({renderer.offset_x}, {renderer.offset_y})")
    print(f"Renderer player_position: {renderer.player_position}")

    # Show the image
    # result.show()


def test_render_without_position(game_with_entities):
    """Test rendering without explicit position - should auto-center on player."""
    game = game_with_entities
    namespace = game.namespaces[0]

    # Move player away from origin
    namespace.move_to(Position(x=10, y=10))

    # Render WITHOUT position - should auto-detect player position
    result = namespace._render(
        radius=64,
        max_render_radius=16,
        include_status=True,
    )

    viewport = result.viewport
    print("\nPlayer moved to (10, 10)")
    print(f"Viewport center: ({viewport.center_x}, {viewport.center_y})")

    # The viewport should be centered near (10, 10), not (0, 0)
    assert abs(viewport.center_x - 10) < 2, (
        f"Expected center_x ~10, got {viewport.center_x}"
    )
    assert abs(viewport.center_y - 10) < 2, (
        f"Expected center_y ~10, got {viewport.center_y}"
    )

    # result.show()


if __name__ == "__main__":
    pytest.main([__file__, "-xvs"])
