import pytest

from entities import Position, Direction
from game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_shift_entity(game):
    """
    Place a boiler at (0, 0)
    :param game:
    :return:
    """
    # boilers_in_inventory = game.inspect_inventory()[Prototype.Pipe]
    entity = game.place_entity(Prototype.StoneFurnace, position=Position(x=5, y=0))

    entity = game.shift_entity(entity, Direction.RIGHT, distance=10)
    assert entity
