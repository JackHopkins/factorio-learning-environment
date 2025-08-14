import pytest

from fle.env.game import FactorioInstance
from fle.env.game.game_types import Technology


@pytest.fixture()
def game(unresearched_instance: FactorioInstance):
    unresearched_instance.reset()
    yield unresearched_instance.namespace
    unresearched_instance.reset()


def test_get_research_progress_automation(game):
    ingredients = game.get_research_progress(Technology.Automation)
    assert ingredients[0].count == 10


def test_get_research_progress_none_fail(game):
    try:
        game.get_research_progress()
    except:
        assert True
        return

    assert False, (
        "Need to set research before calling get_research_progress() without an argument"
    )


def test_get_research_progress_none(game):
    ingredients1 = game.set_research(Technology.Automation)
    ingredients2 = game.get_research_progress()

    assert len(ingredients1) == len(ingredients2)
