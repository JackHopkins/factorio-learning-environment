"""
Test that the character is rendered on top of belts and splitters.
"""

import pytest
from fle.env.entities import Position, Direction
from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "splitter": 10,
        "transport-belt": 100,
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


def test_character_renders_on_top_of_belts(clear_terrain):
    """Test that character is visible when standing on belts."""
    game = clear_terrain

    # Place a grid of belts around the player
    for x in range(-3, 4):
        for y in range(-3, 4):
            game.place_entity(
                Prototype.TransportBelt,
                position=Position(x=x, y=y),
                direction=Direction.UP,
            )

    # Move player to center of belts
    game.move_to(Position(x=0, y=0))

    # Render - character should be visible on top of belts
    image = game._render(position=Position(x=0, y=0), radius=6)
    # image.show()
    assert image is not None


def test_character_renders_on_top_of_splitters(clear_terrain):
    """Test that character is visible when standing on/near splitters."""
    game = clear_terrain

    # Place splitters around the origin
    game.move_to(Position(x=0, y=0))
    game.place_entity(
        Prototype.Splitter, position=Position(x=0, y=-3), direction=Direction.UP
    )
    game.place_entity(
        Prototype.Splitter, position=Position(x=0, y=3), direction=Direction.UP
    )

    # Place belts connecting them
    for y in range(-2, 3):
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

    # Move player to center (on top of belts)
    game.move_to(Position(x=0, y=0))

    # Render - character should be visible on top
    image = game._render(position=Position(x=0, y=0), radius=8)
    image.show()
    assert image is not None


def test_character_and_shadow_layering(clear_terrain):
    """Test that character shadow appears under belts but character on top."""
    game = clear_terrain

    # Create a belt setup
    for y in range(-5, 6):
        game.place_entity(
            Prototype.TransportBelt, position=Position(x=0, y=y), direction=Direction.UP
        )

    # Move player to stand on belts
    game.move_to(Position(x=0, y=0))

    # Render
    image = game._render(position=Position(x=0, y=0), radius=8)
    image.show()
    assert image is not None
