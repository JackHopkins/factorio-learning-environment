import pytest

from fle.env import FactorioInstance
from fle.env.game_types import Technology



@pytest.fixture()
def game(instance: FactorioInstance):
    instance.reset(all_technologies_researched=False)
    yield instance.namespace

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
