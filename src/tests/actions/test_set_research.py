import pytest

from factorio_instance import FactorioInstance
from factorio_types import Technology


@pytest.fixture()
def game(instance):
    #game.initial_inventory = {'assembling-machine-1': 1}
    instance = FactorioInstance(address='localhost',
                                 bounding_box=200,
                                 tcp_port=27000,
                                 all_technologies_researched=False,
                                 fast=True,
                                 inventory={})
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