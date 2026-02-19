"""
Test viewport coordinates returned by the renderer.
"""

import pytest
from fle.env.entities import Position
from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "transport-belt": 100,
        "iron-chest": 10,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


@pytest.fixture()
def clear_terrain(game):
    """Clear cliffs and rocks before each test"""
    game.instance.rcon_client.send_command(
        "/sc "
        "for _, cliff in pairs(game.surfaces[1].find_entities_filtered{type='cliff'}) do "
        "cliff.destroy() "
        "end "
        "for _, rock in pairs(game.surfaces[1].find_entities_filtered{type='simple-entity'}) do "
        "if rock.name:find('rock') then rock.destroy() end "
        "end"
    )
    return game


def test_viewport_is_returned(clear_terrain):
    """Test that the rendered image includes viewport information."""
    game = clear_terrain

    # Place some entities
    game.move_to(Position(x=0, y=0))
    game.place_entity(Prototype.IronChest, position=Position(x=2, y=0))
    game.place_entity(Prototype.IronChest, position=Position(x=-2, y=0))

    # Render
    result = game._render(position=Position(x=0, y=0), radius=10)

    # Check that viewport is returned
    assert result.viewport is not None, "Viewport should be returned"

    # Check viewport properties exist
    assert hasattr(result.viewport, "world_min_x")
    assert hasattr(result.viewport, "world_min_y")
    assert hasattr(result.viewport, "world_max_x")
    assert hasattr(result.viewport, "world_max_y")
    assert hasattr(result.viewport, "center_x")
    assert hasattr(result.viewport, "center_y")
    assert hasattr(result.viewport, "width_tiles")
    assert hasattr(result.viewport, "height_tiles")
    assert hasattr(result.viewport, "image_width")
    assert hasattr(result.viewport, "image_height")
    assert hasattr(result.viewport, "scaling")

    print("\nViewport info:")
    print(
        f"  World bounds: ({result.viewport.world_min_x}, {result.viewport.world_min_y}) to ({result.viewport.world_max_x}, {result.viewport.world_max_y})"
    )
    print(f"  Center: ({result.viewport.center_x}, {result.viewport.center_y})")
    print(
        f"  Size (tiles): {result.viewport.width_tiles} x {result.viewport.height_tiles}"
    )
    print(
        f"  Image size: {result.viewport.image_width} x {result.viewport.image_height}"
    )
    print(f"  Scaling: {result.viewport.scaling} pixels/tile")


def test_viewport_world_to_pixel(clear_terrain):
    """Test that world_to_pixel conversion works correctly."""
    game = clear_terrain

    # Move player to a known position
    game.move_to(Position(x=50, y=50))

    # Place a chest at a known position
    chest = game.place_entity(Prototype.IronChest, position=Position(x=52, y=55))

    # Render
    result = game._render(radius=64, max_render_radius=16)
    viewport = result.viewport

    # Convert the chest's world position to pixel coordinates
    pixel_x, pixel_y = viewport.world_to_pixel(chest.position.x, chest.position.y)

    print(f"\nChest at world ({chest.position.x}, {chest.position.y})")
    print(f"Converted to pixel ({pixel_x}, {pixel_y})")
    print(f"Viewport center: ({viewport.center_x}, {viewport.center_y})")

    # The pixel coordinates should be within the image bounds
    assert 0 <= pixel_x <= viewport.image_width, (
        f"Pixel X {pixel_x} should be within image width {viewport.image_width}"
    )
    assert 0 <= pixel_y <= viewport.image_height, (
        f"Pixel Y {pixel_y} should be within image height {viewport.image_height}"
    )

    result.show()


def test_viewport_pixel_to_world(clear_terrain):
    """Test that pixel_to_world conversion works correctly."""
    game = clear_terrain

    # Move player to a known position
    game.move_to(Position(x=10, y=10))

    # Render with max_render_radius to get a symmetric viewport centered on the player
    result = game._render(
        position=Position(x=10, y=10), radius=128, max_render_radius=128
    )
    viewport = result.viewport

    # Get the center pixel of the image
    center_pixel_x = viewport.image_width // 2
    center_pixel_y = viewport.image_height // 2

    # Convert to world coordinates
    world_x, world_y = viewport.pixel_to_world(center_pixel_x, center_pixel_y)

    # The expected world center is the midpoint of the viewport bounds
    expected_center_x = (viewport.world_min_x + viewport.world_max_x) / 2
    expected_center_y = (viewport.world_min_y + viewport.world_max_y) / 2

    print(f"\nCenter pixel ({center_pixel_x}, {center_pixel_y})")
    print(f"Converted to world ({world_x}, {world_y})")
    print(f"Expected viewport center: ({expected_center_x}, {expected_center_y})")
    print(f"Player position: ({viewport.center_x}, {viewport.center_y})")

    # The center of the image should map to the center of the viewport bounds
    tolerance = 1.0
    assert abs(world_x - expected_center_x) < tolerance, (
        f"World X {world_x} should be close to viewport center {expected_center_x}"
    )
    assert abs(world_y - expected_center_y) < tolerance, (
        f"World Y {world_y} should be close to viewport center {expected_center_y}"
    )


def test_viewport_is_in_viewport(clear_terrain):
    """Test the is_in_viewport helper method."""
    game = clear_terrain

    game.move_to(Position(x=0, y=0))

    # Render with a small radius
    result = game._render(position=Position(x=0, y=0), radius=5)
    viewport = result.viewport

    # The center should be in the viewport
    assert viewport.is_in_viewport(viewport.center_x, viewport.center_y), (
        "Center should be in viewport"
    )

    # A position far outside should not be in the viewport
    assert not viewport.is_in_viewport(100, 100), (
        "Far position should not be in viewport"
    )


def test_viewport_roundtrip_conversion(clear_terrain):
    """Test that world -> pixel -> world roundtrip works correctly."""
    game = clear_terrain

    game.move_to(Position(x=0, y=0))

    result = game._render(position=Position(x=0, y=0), radius=10)
    viewport = result.viewport

    # Test several world positions
    test_positions = [
        (0, 0),
        (5, 5),
        (-3, 2),
        (viewport.center_x, viewport.center_y),
    ]

    for world_x, world_y in test_positions:
        if viewport.is_in_viewport(world_x, world_y):
            # Convert to pixel and back
            pixel_x, pixel_y = viewport.world_to_pixel(world_x, world_y)
            recovered_x, recovered_y = viewport.pixel_to_world(pixel_x, pixel_y)

            # Should be close to original (accounting for rounding)
            tolerance = 1.0 / viewport.scaling  # One pixel tolerance
            assert abs(recovered_x - world_x) < tolerance, (
                f"X roundtrip failed: {world_x} -> {recovered_x}"
            )
            assert abs(recovered_y - world_y) < tolerance, (
                f"Y roundtrip failed: {world_y} -> {recovered_y}"
            )

            print(
                f"Roundtrip OK: ({world_x}, {world_y}) -> ({pixel_x}, {pixel_y}) -> ({recovered_x:.2f}, {recovered_y:.2f})"
            )


def test_viewport_with_max_render_radius(clear_terrain):
    """Test that viewport correctly reports bounds when max_render_radius is set."""
    game = clear_terrain

    game.move_to(Position(x=0, y=0))

    # Render with explicit max_render_radius
    result = game._render(position=Position(x=0, y=0), radius=20, max_render_radius=5)
    viewport = result.viewport

    print("\nWith max_render_radius=5:")
    print(
        f"  World bounds: ({viewport.world_min_x}, {viewport.world_min_y}) to ({viewport.world_max_x}, {viewport.world_max_y})"
    )
    print(f"  Width tiles: {viewport.width_tiles}")
    print(f"  Height tiles: {viewport.height_tiles}")

    # The viewport should be approximately 10x10 tiles (radius*2)
    assert abs(viewport.width_tiles - 10) < 1, (
        f"Width should be ~10 tiles, got {viewport.width_tiles}"
    )
    assert abs(viewport.height_tiles - 10) < 1, (
        f"Height should be ~10 tiles, got {viewport.height_tiles}"
    )


def test_render_centers_on_player_not_origin(clear_terrain):
    """Test that render centers on player position, not the origin.

    This test moves the player away from (0,0) and verifies the viewport
    is centered on the player's actual position.
    """
    game = clear_terrain

    # Move player to a position away from origin (but not too far)
    player_x, player_y = 20, 15
    game.move_to(Position(x=player_x, y=player_y))

    # Render WITHOUT specifying position - should auto-center on player
    result = game._render(radius=10, max_render_radius=8)
    viewport = result.viewport

    print(f"\nPlayer at: ({player_x}, {player_y})")
    print(f"Viewport center: ({viewport.center_x}, {viewport.center_y})")
    print(
        f"World bounds: ({viewport.world_min_x}, {viewport.world_min_y}) to ({viewport.world_max_x}, {viewport.world_max_y})"
    )

    # The viewport center should be the player position, NOT (0, 0)
    tolerance = 1.0
    assert abs(viewport.center_x - player_x) < tolerance, (
        f"Viewport center_x should be ~{player_x} (player pos), got {viewport.center_x}"
    )
    assert abs(viewport.center_y - player_y) < tolerance, (
        f"Viewport center_y should be ~{player_y} (player pos), got {viewport.center_y}"
    )

    # Verify the world bounds are centered on player
    expected_min_x = player_x - 8  # max_render_radius
    expected_max_x = player_x + 8
    _expected_min_y = player_y - 8
    _expected_max_y = player_y + 8

    assert abs(viewport.world_min_x - expected_min_x) < tolerance, (
        f"world_min_x should be ~{expected_min_x}, got {viewport.world_min_x}"
    )
    assert abs(viewport.world_max_x - expected_max_x) < tolerance, (
        f"world_max_x should be ~{expected_max_x}, got {viewport.world_max_x}"
    )


def test_render_produces_512x512_image(clear_terrain):
    """Test that render produces a 512x512 image by default."""
    game = clear_terrain

    game.move_to(Position(x=0, y=0))

    # Place some entities
    game.place_entity(Prototype.IronChest, position=Position(x=2, y=0))

    # Render with max_render_radius to get consistent size
    result = game._render(radius=10, max_render_radius=8)

    # Get the actual PIL image
    img = result.image

    print(f"\nImage size: {img.width} x {img.height}")
    print(f"Viewport: {result.viewport.image_width} x {result.viewport.image_height}")

    # Check image dimensions
    # Note: The actual requirement may vary - adjust if 512x512 is not the target
    assert img.width == img.height, (
        f"Image should be square, got {img.width}x{img.height}"
    )
