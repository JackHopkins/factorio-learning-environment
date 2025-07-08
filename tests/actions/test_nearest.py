import pytest

from fle.env.entities import Position
from fle.env.game_types import Resource


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_nearest_resource(game):
    """
    Test distance to the nearest coal resource.
    :param game:
    :return:
    """
    coal: Position = game.nearest(Resource.Coal)
    assert coal.y == -0.5
    assert coal.x == 15.5


def test_move_to_nearest(game):
    """
    Test that when the player moves to the nearest water resource, the nearest water resource remains the same.
    :param game:
    :return:
    """
    water: Position = game.nearest(Resource.Water)
    game.move_to(water)
    assert abs(water.x - game.nearest(Resource.Water).x) <= 1
