import pytest

from factorio_types import Prototype

@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance.namespace

def test_get_score(game):
    score = game.score()
