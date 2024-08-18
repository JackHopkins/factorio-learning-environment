import pytest

from factorio_types import Prototype

@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_place(game):
    """
    Place a boiler at (0, 0)
    :param game:
    :return:
    """
    boilers_in_inventory = game.inspect_inventory()[Prototype.Boiler]
    game.place_entity(Prototype.Boiler, position=(0, 0))
    assert boilers_in_inventory - 1 == game.inspect_inventory()[Prototype.Boiler]

def test_place_pickup(game):
    """
    Place a boiler at (0, 0) and then pick it up
    :param game:
    :return:
    """
    boilers_in_inventory = game.inspect_inventory()[Prototype.Boiler]
    game.place_entity(Prototype.Boiler, position=(0, 0))
    assert boilers_in_inventory == game.inspect_inventory()[Prototype.Boiler] + 1

    game.pickup_entity(Prototype.Boiler, position=(0, 0))
    assert boilers_in_inventory == game.inspect_inventory()[Prototype.Boiler] - 1
