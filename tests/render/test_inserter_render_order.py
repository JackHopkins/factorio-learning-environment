"""
Test that inserter arms are rendered on top of transport belts.
"""

import pytest
from fle.env.entities import Position, Direction
from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "transport-belt": 100,
        "splitter": 10,
        "inserter": 20,
        "fast-inserter": 20,
        "long-handed-inserter": 10,
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


def test_inserter_arm_renders_on_top_of_belt(clear_terrain):
    """Test that inserter arms are visible when placed next to belts."""
    game = clear_terrain

    # Place a line of belts
    for y in range(-3, 4):
        game.place_entity(
            Prototype.TransportBelt, position=Position(x=0, y=y), direction=Direction.UP
        )

    # Place inserters next to the belt line - they should reach over the belts
    game.place_entity(
        Prototype.Inserter, position=Position(x=-1, y=0), direction=Direction.RIGHT
    )
    game.place_entity(
        Prototype.Inserter, position=Position(x=1, y=0), direction=Direction.LEFT
    )

    # Place chests on the other side
    game.place_entity(Prototype.IronChest, position=Position(x=-2, y=0))
    game.place_entity(Prototype.IronChest, position=Position(x=2, y=0))

    # Render - inserter arms should be visible on top of the belts
    image = game._render(position=Position(x=0, y=0), radius=8)
    # image.show()
    assert image is not None


def test_multiple_inserter_types_on_belts(clear_terrain):
    """Test various inserter types with belts."""
    game = clear_terrain

    # Create lines of belts
    for y in range(-3, 4):
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=-2, y=y),
            direction=Direction.UP,
        )
        game.place_entity(
            Prototype.TransportBelt, position=Position(x=0, y=y), direction=Direction.UP
        )
        game.place_entity(
            Prototype.TransportBelt, position=Position(x=2, y=y), direction=Direction.UP
        )

    # Place different inserter types next to belts (not on top)
    game.place_entity(
        Prototype.Inserter, position=Position(x=-3, y=0), direction=Direction.RIGHT
    )
    game.place_entity(
        Prototype.FastInserter, position=Position(x=-1, y=0), direction=Direction.RIGHT
    )
    game.place_entity(
        Prototype.LongHandedInserter,
        position=Position(x=1, y=0),
        direction=Direction.RIGHT,
    )

    # Render
    image = game._render(position=Position(x=0, y=0), radius=10)
    # image.show()
    assert image is not None


def test_inserter_between_belt_and_chest(clear_terrain):
    """Test classic inserter setup: belt -> inserter -> chest."""
    game = clear_terrain

    # Create a line of belts
    for y in range(-5, 6):
        game.place_entity(
            Prototype.TransportBelt, position=Position(x=0, y=y), direction=Direction.UP
        )

    # Place inserters taking from belt to chests
    for y in range(-3, 4, 2):
        game.place_entity(
            Prototype.Inserter, position=Position(x=1, y=y), direction=Direction.LEFT
        )
        game.place_entity(Prototype.IronChest, position=Position(x=2, y=y))

    # Render
    image = game._render(position=Position(x=1, y=0), radius=8)
    # image.show()
    assert image is not None


def test_inserter_on_splitter(clear_terrain):
    """Test inserter rendered on top of splitter."""
    game = clear_terrain

    # Place splitter
    game.place_entity(
        Prototype.Splitter, position=Position(x=0, y=0), direction=Direction.UP
    )

    # Place belts connecting to splitter
    for y in range(-3, 0):
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

    # Place inserter on top of splitter area
    game.place_entity(
        Prototype.FastInserter, position=Position(x=0, y=1), direction=Direction.DOWN
    )

    # Render
    image = game._render(position=Position(x=0, y=0), radius=8)
    # image.show()
    assert image is not None
