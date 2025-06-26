import pytest

from env.src.game_types import Technology

@pytest.fixture()
def game(instance):
    instance.all_technologies_researched = False
    instance.reset()
    yield instance.namespace
    instance.reset()

def test_get_research_progress_automation(game):
    ingredients = game.get_research_progress(Technology.Automation)
    assert ingredients[0].count == 10

def test_get_research_progress_none_fail(game):
    try:
        ingredients = game.get_research_progress()
    except:
        assert True
        return

    assert False, "Need to set research before calling get_research_progress() without an argument"


def test_get_research_progress_none(game):
    ingredients1 = game.set_research(Technology.Automation)
    ingredients2 = game.get_research_progress()

    assert len(ingredients1) == len(ingredients2)