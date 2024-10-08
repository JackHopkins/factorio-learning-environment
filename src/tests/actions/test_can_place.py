import pytest

from factorio_types import Prototype

@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance
    instance.reset()

def test_can_place(game):
    """
    Place a boiler at (0, 0)
    :param game:
    :return:
    """
    boilers_in_inventory = game.inspect_inventory()[Prototype.Pipe]
    can_place = game.can_place_entity(Prototype.Pipe, position=(5, 0))
    assert can_place == True

    # attempt to place a pipe beyond the reach of the player
    can_place = game.can_place_entity(Prototype.Pipe, position=(100, 0))
    assert can_place == False

    game.place_entity(Prototype.Pipe, position=(5, 0))
    can_place = game.can_place_entity(Prototype.Pipe, position=(5, 0))
    assert can_place == False

