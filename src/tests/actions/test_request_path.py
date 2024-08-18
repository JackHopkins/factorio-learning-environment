import pytest

from factorio_entities import Position
from factorio_types import Prototype

@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_path(game):
    """
    Get a path from (0, 0) to (10, 0)
    :param game:
    :return:
    """
    path = game.request_path(Position(x=0, y=0), Position(x=10, y=0))

    assert path