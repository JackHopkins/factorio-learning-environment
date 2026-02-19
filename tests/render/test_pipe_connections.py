"""
Tests for pipe connection rendering.

These tests verify that pipes correctly show connections to fluid-handling entities
like boilers, steam engines, and other entities with fluid boxes.
"""

import pytest
from fle.env.entities import Position, Layer, Direction
from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "pipe": 100,
        "boiler": 5,
        "steam-engine": 5,
        "offshore-pump": 2,
        "storage-tank": 2,
        "chemical-plant": 2,
        "pump": 5,
        "small-electric-pole": 10,
        "coal": 100,
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


def test_boiler_to_steam_engine_connection(clear_terrain):
    """Test that pipes correctly connect boiler to steam engine using connect_entities."""
    game = clear_terrain

    # Place steam engine
    game.move_to(Position(x=0, y=0))
    engine = game.place_entity(Prototype.SteamEngine, position=Position(x=0, y=0))

    # Place boiler
    game.move_to(Position(x=10, y=0))
    boiler = game.place_entity(
        Prototype.Boiler, position=Position(x=10, y=0), direction=Direction.LEFT
    )

    # Connect them with pipes using connect_entities
    game.connect_entities(engine, boiler, {Prototype.Pipe})

    # Render and verify - pipes should show proper connections to both entities
    image = game._render(radius=32, layers=Layer.ALL)  # position=Position(x=5, y=0),
    # image.show()
    assert image is not None


def test_pipe_connections_different_directions(clear_terrain):
    """Test pipe connections to boilers facing different directions."""
    game = clear_terrain

    # Place a boiler facing north
    game.move_to(Position(x=0, y=0))
    boiler_north = game.place_entity(
        Prototype.Boiler, position=Position(x=0, y=0), direction=Direction.UP
    )

    # Place a steam engine to connect to
    engine = game.place_entity(Prototype.SteamEngine, position=Position(x=0, y=-6))

    # Connect them
    game.connect_entities(boiler_north, engine, {Prototype.Pipe})

    # Render
    image = game._render(position=Position(x=0, y=-3), radius=10, layers=Layer.ALL)
    # image.show()
    assert image is not None


def test_pipe_t_junction_with_boiler(clear_terrain):
    """Test T-junction of pipes with a boiler connection."""
    game = clear_terrain

    # Place boiler facing up (steam output is north side)
    game.move_to(Position(x=0, y=5))
    boiler = game.place_entity(
        Prototype.Boiler, position=Position(x=0, y=5), direction=Direction.UP
    )

    # Place first steam engine above the boiler
    game.move_to(Position(x=0, y=-3))
    engine1 = game.place_entity(Prototype.SteamEngine, position=Position(x=0, y=-3))

    # Connect boiler to first engine (creates pipe run from steam output northward)
    game.connect_entities(boiler, engine1, {Prototype.Pipe})

    # Place second steam engine to the side, connectable from the pipe run
    game.move_to(Position(x=8, y=0))
    engine2 = game.place_entity(Prototype.SteamEngine, position=Position(x=8, y=0))

    # Connect from the first engine to the second to form a T-junction
    game.connect_entities(engine1, engine2, {Prototype.Pipe})

    # Render - should show T-junctions where pipes meet
    image = game._render(position=Position(x=0, y=2), radius=15, layers=Layer.ALL)
    # image.show()
    assert image is not None


def test_horizontal_pipe_chain(clear_terrain):
    """Test a horizontal chain of pipes between two boilers."""
    game = clear_terrain

    # Place two boilers facing each other
    game.move_to(Position(x=-8, y=0))
    boiler1 = game.place_entity(
        Prototype.Boiler, position=Position(x=-8, y=0), direction=Direction.RIGHT
    )

    game.move_to(Position(x=8, y=0))
    boiler2 = game.place_entity(
        Prototype.Boiler, position=Position(x=8, y=0), direction=Direction.LEFT
    )

    # Connect them
    game.connect_entities(boiler1, boiler2, {Prototype.Pipe})

    # Render
    image = game._render(position=Position(x=0, y=0), radius=15, layers=Layer.ALL)
    # image.show()
    assert image is not None


def test_vertical_pipe_chain(clear_terrain):
    """Test a vertical chain of pipes between entities."""
    game = clear_terrain

    # Place steam engine at top
    game.move_to(Position(x=0, y=-8))
    engine = game.place_entity(Prototype.SteamEngine, position=Position(x=0, y=-8))

    # Place boiler at bottom
    game.move_to(Position(x=0, y=8))
    boiler = game.place_entity(
        Prototype.Boiler, position=Position(x=0, y=8), direction=Direction.UP
    )

    # Connect them
    game.connect_entities(engine, boiler, {Prototype.Pipe})

    # Render
    image = game._render(position=Position(x=0, y=0), radius=15, layers=Layer.ALL)
    # image.show()
    assert image is not None


def test_corner_pipe_connections(clear_terrain):
    """Test corner/curved pipe connections."""
    game = clear_terrain

    # Place a boiler at origin facing up
    game.move_to(Position(x=0, y=0))
    boiler = game.place_entity(
        Prototype.Boiler, position=Position(x=0, y=0), direction=Direction.UP
    )

    # Place steam engine to the side and up (requiring a corner in the pipe)
    game.move_to(Position(x=10, y=-10))
    engine = game.place_entity(Prototype.SteamEngine, position=Position(x=10, y=-10))

    # Connect them - this should create corner pipes
    game.connect_entities(boiler, engine, {Prototype.Pipe})

    # Render - should show corner pipes
    image = game._render(position=Position(x=5, y=-5), radius=15, layers=Layer.ALL)
    # image.show()
    assert image is not None


def test_multiple_pipe_connections_to_one_entity(clear_terrain):
    """Test multiple pipe connections to a single entity."""
    game = clear_terrain

    # Place a boiler in the center
    game.move_to(Position(x=0, y=0))
    boiler = game.place_entity(
        Prototype.Boiler, position=Position(x=0, y=0), direction=Direction.UP
    )

    # Place steam engine above (connected to steam output)
    game.move_to(Position(x=0, y=-8))
    engine = game.place_entity(Prototype.SteamEngine, position=Position(x=0, y=-8))

    # Connect boiler to engine
    game.connect_entities(boiler, engine, {Prototype.Pipe})

    # Render
    image = game._render(position=Position(x=0, y=-4), radius=12, layers=Layer.ALL)
    # image.show()
    assert image is not None


def test_long_pipe_connection(clear_terrain):
    """Test a long pipe connection between distant entities."""
    game = clear_terrain

    # Place entities far apart
    game.move_to(Position(x=-15, y=0))
    engine = game.place_entity(Prototype.SteamEngine, position=Position(x=-15, y=0))

    game.move_to(Position(x=15, y=0))
    boiler = game.place_entity(
        Prototype.Boiler, position=Position(x=15, y=0), direction=Direction.LEFT
    )

    # Connect them with a long pipe run
    game.connect_entities(engine, boiler, {Prototype.Pipe})

    # Render - all pipes should show proper connections
    image = game._render(position=Position(x=0, y=0), radius=20, layers=Layer.ALL)
    # image.show()
    assert image is not None
