import pytest

from fle.env.entities import Position


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_path(game):
    """
    Get a path from (0, 0) to (10, 0)
    :param game:
    :return:
    """
    path = game._request_path(Position(x=0, y=0), Position(x=10, y=0))

    assert path
