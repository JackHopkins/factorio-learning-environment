import pytest

from factorio_instance import FactorioInstance
from factorio_types import Technology


@pytest.fixture()
def game(instance):
    #game.initial_inventory = {'assembling-machine-1': 1}
    instance = FactorioInstance(address='localhost',
                                 bounding_box=200,
                                 tcp_port=27015,
                                 all_technologies_researched=False,
                                 fast=True,
                                 inventory={})
    instance.reset()
    yield instance
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