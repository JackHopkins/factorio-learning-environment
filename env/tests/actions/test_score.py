import pytest


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance.namespace


def test_get_score(game):
    score, _ = game.score()
    assert isinstance(score, int)
