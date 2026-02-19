"""
Tests for splitter rendering in various orientations and configurations.

These tests help diagnose splitter rendering issues by placing splitters
in different directions and with various belt connections.
"""

import pytest
from fle.env.entities import Position, Layer, Direction
from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "splitter": 20,
        "fast-splitter": 10,
        "express-splitter": 10,
        "transport-belt": 100,
        "fast-transport-belt": 50,
        "express-transport-belt": 50,
        "underground-belt": 20,
        "iron-plate": 50,
        "copper-plate": 50,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


@pytest.fixture()
def clear_terrain(game):
    """Clear cliffs, rocks, and water tiles before each test"""
    game.instance.rcon_client.send_command(
        "/sc "
        "for _, cliff in pairs(game.surfaces[1].find_entities_filtered{type='cliff'}) do "
        "cliff.destroy() "
        "end "
        "for _, rock in pairs(game.surfaces[1].find_entities_filtered{type='simple-entity'}) do "
        "if rock.name:find('rock') then rock.destroy() end "
        "end "
        "local tiles = {} "
        "for x = -30, 30 do "
        "for y = -30, 30 do "
        "local tile = game.surfaces[1].get_tile(x, y) "
        "if tile.name == 'water' or tile.name == 'deepwater' or "
        "tile.name == 'water-green' or tile.name == 'deepwater-green' or "
        "tile.name == 'water-shallow' or tile.name == 'water-mud' then "
        "table.insert(tiles, {name='grass-1', position={x=x, y=y}}) "
        "end "
        "end "
        "end "
        "if #tiles > 0 then game.surfaces[1].set_tiles(tiles) end"
    )
    return game


def test_splitter_all_directions(clear_terrain):
    """Test splitters in all 4 cardinal directions."""
    game = clear_terrain

    # Place splitters in all 4 directions with spacing
    # North-facing splitter (horizontal, items flow north)
    game.move_to(Position(x=-10, y=-10))
    _s_north = game.place_entity(
        Prototype.Splitter, position=Position(x=-10, y=-10), direction=Direction.UP
    )

    # South-facing splitter (horizontal, items flow south)
    game.move_to(Position(x=0, y=-10))
    _s_south = game.place_entity(
        Prototype.Splitter, position=Position(x=0, y=-10), direction=Direction.DOWN
    )

    # East-facing splitter (vertical, items flow east)
    game.move_to(Position(x=10, y=-10))
    _s_east = game.place_entity(
        Prototype.Splitter, position=Position(x=10, y=-10), direction=Direction.RIGHT
    )

    # West-facing splitter (vertical, items flow west)
    game.move_to(Position(x=20, y=-10))
    _s_west = game.place_entity(
        Prototype.Splitter, position=Position(x=20, y=-10), direction=Direction.LEFT
    )

    # Render the result
    image = game._render(position=Position(x=5, y=-10), radius=20, layers=Layer.ALL)
    # image.show()
    assert image is not None


def test_splitter_tiers(clear_terrain):
    """Test all 3 tiers of splitters (normal, fast, express)."""
    game = clear_terrain

    # Normal splitter
    game.move_to(Position(x=-10, y=0))
    game.place_entity(
        Prototype.Splitter, position=Position(x=-10, y=0), direction=Direction.UP
    )

    # Fast splitter
    game.move_to(Position(x=0, y=0))
    game.place_entity(
        Prototype.FastSplitter, position=Position(x=0, y=0), direction=Direction.UP
    )

    # Express splitter
    game.move_to(Position(x=10, y=0))
    game.place_entity(
        Prototype.ExpressSplitter, position=Position(x=10, y=0), direction=Direction.UP
    )

    # Render
    image = game._render(position=Position(x=0, y=0), radius=15, layers=Layer.ALL)
    # image.show()
    assert image is not None


def test_splitter_with_input_belts(clear_terrain):
    """Test splitters with input belts connected."""
    game = clear_terrain

    # North-facing splitter with input belt from south
    game.move_to(Position(x=0, y=0))
    _splitter = game.place_entity(
        Prototype.Splitter, position=Position(x=0, y=0), direction=Direction.UP
    )

    # Add input belts feeding into the splitter
    for y in range(1, 5):
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=-0.5, y=y),
            direction=Direction.UP,
        )
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=0.5, y=y),
            direction=Direction.UP,
        )

    # Render
    image = game._render(position=Position(x=0, y=2), radius=8, layers=Layer.ALL)
    # image.show()
    assert image is not None


def test_splitter_with_output_belts(clear_terrain):
    """Test splitters with output belts connected."""
    game = clear_terrain

    # North-facing splitter with output belts going north
    game.move_to(Position(x=0, y=0))
    _splitter = game.place_entity(
        Prototype.Splitter, position=Position(x=0, y=0), direction=Direction.UP
    )

    # Add output belts from the splitter
    for y in range(-4, 0):
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=-0.5, y=y),
            direction=Direction.UP,
        )
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=0.5, y=y),
            direction=Direction.UP,
        )

    # Render
    image = game._render(position=Position(x=0, y=-2), radius=8, layers=Layer.ALL)
    # image.show()
    assert image is not None


def test_splitter_full_belt_system(clear_terrain):
    """Test splitter with full input and output belt system."""
    game = clear_terrain

    # Place splitter
    game.move_to(Position(x=0, y=0))
    _splitter = game.place_entity(
        Prototype.Splitter, position=Position(x=0, y=0), direction=Direction.UP
    )

    # Input belts (from south)
    for y in range(1, 6):
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=-0.5, y=y),
            direction=Direction.UP,
        )
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=0.5, y=y),
            direction=Direction.UP,
        )

    # Output belts (to north)
    for y in range(-5, 0):
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=-0.5, y=y),
            direction=Direction.UP,
        )
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=0.5, y=y),
            direction=Direction.UP,
        )

    # Render
    image = game._render(position=Position(x=0, y=0), radius=10, layers=Layer.ALL)
    # image.show()
    assert image is not None


def test_splitter_east_west_orientations(clear_terrain):
    """Test splitters in east/west orientations with belts."""
    game = clear_terrain

    # East-facing splitter
    game.move_to(Position(x=-10, y=0))
    _s_east = game.place_entity(
        Prototype.Splitter, position=Position(x=-10, y=0), direction=Direction.RIGHT
    )

    # Input belts from west
    for x in range(-15, -11):
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=x, y=-0.5),
            direction=Direction.RIGHT,
        )
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=x, y=0.5),
            direction=Direction.RIGHT,
        )

    # Output belts to east
    for x in range(-9, -4):
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=x, y=-0.5),
            direction=Direction.RIGHT,
        )
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=x, y=0.5),
            direction=Direction.RIGHT,
        )

    # West-facing splitter
    game.move_to(Position(x=10, y=0))
    _s_west = game.place_entity(
        Prototype.Splitter, position=Position(x=10, y=0), direction=Direction.LEFT
    )

    # Input belts from east
    for x in range(11, 16):
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=x, y=-0.5),
            direction=Direction.LEFT,
        )
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=x, y=0.5),
            direction=Direction.LEFT,
        )

    # Output belts to west
    for x in range(5, 10):
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=x, y=-0.5),
            direction=Direction.LEFT,
        )
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=x, y=0.5),
            direction=Direction.LEFT,
        )

    # Render
    image = game._render(position=Position(x=0, y=0), radius=20, layers=Layer.ALL)
    # image.show()
    assert image is not None


def test_splitter_priority_configurations(clear_terrain):
    """Test splitters with different priority settings if accessible."""
    game = clear_terrain

    # Place multiple splitters to test priority visuals
    game.move_to(Position(x=0, y=0))
    _s1 = game.place_entity(
        Prototype.Splitter, position=Position(x=0, y=0), direction=Direction.UP
    )

    game.move_to(Position(x=5, y=0))
    _s2 = game.place_entity(
        Prototype.Splitter, position=Position(x=5, y=0), direction=Direction.UP
    )

    game.move_to(Position(x=10, y=0))
    _s3 = game.place_entity(
        Prototype.Splitter, position=Position(x=10, y=0), direction=Direction.UP
    )

    # Render
    image = game._render(position=Position(x=5, y=0), radius=12, layers=Layer.ALL)
    # image.show()
    assert image is not None


def test_splitter_chain(clear_terrain):
    """Test a chain of splitters connected in series."""
    game = clear_terrain

    # Create a chain of splitters going north
    for i in range(4):
        y_pos = i * 3
        game.move_to(Position(x=0, y=y_pos))
        game.place_entity(
            Prototype.Splitter, position=Position(x=0, y=y_pos), direction=Direction.UP
        )

        # Connect with belts between splitters (except after the last one)
        if i < 3:
            game.place_entity(
                Prototype.TransportBelt,
                position=Position(x=-0.5, y=y_pos - 1),
                direction=Direction.UP,
            )
            game.place_entity(
                Prototype.TransportBelt,
                position=Position(x=0.5, y=y_pos - 1),
                direction=Direction.UP,
            )
            game.place_entity(
                Prototype.TransportBelt,
                position=Position(x=-0.5, y=y_pos - 2),
                direction=Direction.UP,
            )
            game.place_entity(
                Prototype.TransportBelt,
                position=Position(x=0.5, y=y_pos - 2),
                direction=Direction.UP,
            )

    # Render
    _entities = game.get_entities()
    image = game._render(position=Position(x=0, y=4), radius=15)  # , layers=Layer.ALL)
    # image.show()
    assert image is not None


def test_splitter_grid_all_directions(clear_terrain):
    """Test a grid of splitters showing all directions clearly labeled."""
    game = clear_terrain

    # Row 1: North-facing splitters
    for i in range(3):
        game.move_to(Position(x=i * 5, y=0))
        game.place_entity(
            Prototype.Splitter, position=Position(x=i * 5, y=0), direction=Direction.UP
        )

    # Row 2: South-facing splitters
    for i in range(3):
        game.move_to(Position(x=i * 5, y=5))
        game.place_entity(
            Prototype.Splitter,
            position=Position(x=i * 5, y=5),
            direction=Direction.DOWN,
        )

    # Row 3: East-facing splitters
    for i in range(3):
        game.move_to(Position(x=i * 5, y=10))
        game.place_entity(
            Prototype.Splitter,
            position=Position(x=i * 5, y=10),
            direction=Direction.RIGHT,
        )

    # Row 4: West-facing splitters
    for i in range(3):
        game.move_to(Position(x=i * 5, y=15))
        game.place_entity(
            Prototype.Splitter,
            position=Position(x=i * 5, y=15),
            direction=Direction.LEFT,
        )

    # Render
    image = game._render(position=Position(x=5, y=7), radius=15, layers=Layer.ALL)
    # image.show()
    assert image is not None


def test_splitter_balancer_2x2(clear_terrain):
    """Test a simple 2-to-2 balancer configuration."""
    game = clear_terrain

    # Create a 2-to-2 balancer
    # Two parallel splitters
    game.move_to(Position(x=0, y=0))
    game.place_entity(
        Prototype.Splitter, position=Position(x=0, y=0), direction=Direction.UP
    )

    game.move_to(Position(x=0, y=-3))
    game.place_entity(
        Prototype.Splitter, position=Position(x=0, y=-3), direction=Direction.UP
    )

    # Cross-connect belts between splitters
    # Left output of first to right input of second (and vice versa)
    game.place_entity(
        Prototype.TransportBelt, position=Position(x=-0.5, y=-1), direction=Direction.UP
    )
    game.place_entity(
        Prototype.TransportBelt, position=Position(x=0.5, y=-1), direction=Direction.UP
    )
    game.place_entity(
        Prototype.TransportBelt, position=Position(x=-0.5, y=-2), direction=Direction.UP
    )
    game.place_entity(
        Prototype.TransportBelt, position=Position(x=0.5, y=-2), direction=Direction.UP
    )

    # Input belts
    for y in range(1, 4):
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=-0.5, y=y),
            direction=Direction.UP,
        )
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=0.5, y=y),
            direction=Direction.UP,
        )

    # Output belts
    for y in range(-6, -3):
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=-0.5, y=y),
            direction=Direction.UP,
        )
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=0.5, y=y),
            direction=Direction.UP,
        )

    # Render
    image = game._render(position=Position(x=0, y=-1), radius=10, layers=Layer.ALL)
    image.show()
    assert image is not None


def test_splitter_mixed_belt_types(clear_terrain):
    """Test splitters with different belt tiers connected."""
    game = clear_terrain

    # Normal splitter with normal belts
    game.move_to(Position(x=-10, y=0))
    game.place_entity(
        Prototype.Splitter, position=Position(x=-10, y=0), direction=Direction.UP
    )
    for y in range(1, 4):
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=-10.5, y=y),
            direction=Direction.UP,
        )
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=-9.5, y=y),
            direction=Direction.UP,
        )

    # Fast splitter with fast belts
    game.move_to(Position(x=0, y=0))
    game.place_entity(
        Prototype.FastSplitter, position=Position(x=0, y=0), direction=Direction.UP
    )
    for y in range(1, 4):
        game.place_entity(
            Prototype.FastTransportBelt,
            position=Position(x=-0.5, y=y),
            direction=Direction.UP,
        )
        game.place_entity(
            Prototype.FastTransportBelt,
            position=Position(x=0.5, y=y),
            direction=Direction.UP,
        )

    # Express splitter with express belts
    game.move_to(Position(x=10, y=0))
    game.place_entity(
        Prototype.ExpressSplitter, position=Position(x=10, y=0), direction=Direction.UP
    )
    for y in range(1, 4):
        game.place_entity(
            Prototype.ExpressTransportBelt,
            position=Position(x=9.5, y=y),
            direction=Direction.UP,
        )
        game.place_entity(
            Prototype.ExpressTransportBelt,
            position=Position(x=10.5, y=y),
            direction=Direction.UP,
        )

    # Render
    image = game._render(position=Position(x=0, y=1), radius=18, layers=Layer.ALL)
    image.show()
    assert image is not None


def test_splitter_single_isolated(clear_terrain):
    """Test a single isolated splitter in each direction for close inspection."""
    game = clear_terrain

    # Single north splitter - for detailed inspection
    game.move_to(Position(x=0, y=0))
    _splitter = game.place_entity(
        Prototype.Splitter, position=Position(x=0, y=0), direction=Direction.UP
    )

    # Render close-up
    image = game._render(position=Position(x=0, y=0), radius=5, layers=Layer.ALL)
    image.show()
    assert image is not None


def test_splitter_single_east(clear_terrain):
    """Test a single east-facing splitter for close inspection."""
    game = clear_terrain

    game.move_to(Position(x=0, y=0))
    _splitter = game.place_entity(
        Prototype.Splitter, position=Position(x=0, y=0), direction=Direction.RIGHT
    )

    # Render close-up
    image = game._render(position=Position(x=0, y=0), radius=5, layers=Layer.ALL)
    image.show()
    assert image is not None
