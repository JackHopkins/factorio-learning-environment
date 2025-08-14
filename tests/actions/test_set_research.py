import pytest

from fle.env.game import FactorioInstance
from fle.env.game.game_types import Technology

@pytest.fixture()
def game(unresearched_instance: FactorioInstance):
    unresearched_instance.reset()
    yield unresearched_instance.namespace
    unresearched_instance.reset()


def test_set_research(game):
    ingredients = game.set_research(Technology.Automation)
    assert ingredients[0].count == 10


def test_fail_to_research_locked_technology(game):
    try:
        game.set_research(Technology.Automation2)
    except Exception:
        assert True
        return
    assert False, "Was able to research locked technology. Expected exception."
