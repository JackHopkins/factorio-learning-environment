import pytest
from time import sleep
from entities import Position, ResourcePatch
from instance import Direction
from game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        'stone-furnace': 10,
        'burner-mining-drill': 10,
        'electric-mining-drill': 5,
        'transport-belt': 200,
        'underground-belt': 20,
        'splitter': 10,
        'burner-inserter': 50,
        'fast-inserter': 20,
        'pipe': 100,
        'pipe-to-ground': 20,
        'offshore-pump': 5,
        'boiler': 5,
        'steam-engine': 10,
        'small-electric-pole': 50,
        'medium-electric-pole': 20,
        'assembling-machine-1': 10,
        'iron-chest': 20,
        'coal': 500,
        'iron-plate': 200,
        'copper-plate': 200,
    }
    instance.reset()
    yield instance.namespace

def test_variables(game):

    game.eval_with_error("fizz='mart'")
    _, _, result = game.eval_with_error("fizz")

    assert result == '0: mart'

def test_print(game):
    _, _, result = game.eval_with_error("print('hello')")

    assert result == '0: hello'