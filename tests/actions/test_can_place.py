import pytest

from fle.env.entities import Position, Direction
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_can_place(game):
    """
    Place a boiler at (0, 0)
    :param game:
    :return:
    """
    can_place = game.can_place_entity(Prototype.Pipe, position=(5, 0))
    assert can_place

    # attempt to place a pipe beyond the reach of the player
    can_place = game.can_place_entity(Prototype.Pipe, position=(100, 0))
    assert not can_place

    game.place_entity(Prototype.Pipe, position=(5, 0))
    can_place = game.can_place_entity(Prototype.Pipe, position=(5, 0))
    assert not can_place


def test_can_place_over_resources(game):
    copper_ore = game.nearest(Resource.CopperOre)
    game.move_to(copper_ore)
    can_build = game.can_place_entity(Prototype.BurnerMiningDrill, position=copper_ore)
    assert can_build


def test_can_place_over_player_large(game):
    game.move_to(Position(x=0, y=0))
    assert game.can_place_entity(Prototype.SteamEngine, position=Position(x=0, y=0))

    game.place_entity(
        Prototype.SteamEngine, position=Position(x=0, y=0), direction=Direction.UP
    )
    pass
