import pytest

from env.src.game_types import Technology

@pytest.fixture()
def game(instance):
    instance.all_technologies_researched = False
    instance.reset()
    yield instance.namespace
    instance.reset()

def test_set_research(game):
    ingredients = game.set_research(Technology.Automation)
    assert ingredients[0].count == 10

def test_fail_to_research_locked_technology(game):
    try:
        game.set_research(Technology.Automation2)
    except Exception as e:
        assert True
        return
    assert False, "Was able to research locked technology. Expected exception."