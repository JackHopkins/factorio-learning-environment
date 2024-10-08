import pytest

from factorio_entities import Position
from factorio_instance import Direction
from factorio_types import Prototype

@pytest.fixture()
def game(instance):
    instance.initial_inventory = {'iron-chest': 1, 'iron-ore': 10, 'coal': 10, 'stone-furnace': 1}
    instance.reset()
    yield instance
    instance.reset()

def test_insert_and_fuel_furnace(game):
    furnace = game.place_entity(Prototype.StoneFurnace, direction=Direction.UP, position=Position(x=0, y=0))
    furnace = game.insert_item(Prototype.IronOre, furnace, quantity=10)
    furnace = game.insert_item(Prototype.Coal, furnace, quantity=10)

    assert furnace.fuel_inventory[Prototype.Coal] == 10
    assert furnace.input_inventory[Prototype.IronOre] == 10

