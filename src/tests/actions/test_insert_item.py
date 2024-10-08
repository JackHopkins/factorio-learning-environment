import pytest

from factorio_entities import Position
from factorio_instance import Direction
from factorio_types import Prototype

@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        'iron-chest': 1,
        'iron-ore': 10,
        'coal': 10,
        'stone-furnace': 1,
        'transport-belt': 10,
        'burner-inserter': 1,
    }
    instance.reset()
    yield instance
    #instance.reset()

def test_insert_and_fuel_furnace(game):
    furnace = game.place_entity(Prototype.StoneFurnace, direction=Direction.UP, position=Position(x=0, y=0))
    furnace = game.insert_item(Prototype.IronOre, furnace, quantity=10)
    furnace = game.insert_item(Prototype.Coal, furnace, quantity=10)

    assert furnace.fuel_inventory[Prototype.Coal] == 10
    assert furnace.input_inventory[Prototype.IronOre] == 10

def test_insert_iron_ore_into_stone_furnace(game):
    furnace = game.place_entity(Prototype.StoneFurnace, direction=Direction.UP, position=Position(x=0, y=0))
    furnace = game.insert_item(Prototype.IronOre, furnace, quantity=10)

    assert furnace.input_inventory[Prototype.IronOre] == 10

def test_insert_coal_into_burner_inserter(game):
    inserter = game.place_entity(Prototype.BurnerInserter, direction=Direction.UP, position=Position(x=0, y=0))
    inserter = game.insert_item(Prototype.Coal, inserter, quantity=10)

    assert inserter.fuel_inventory[Prototype.Coal] == 10
def test_insert_coal_onto_belt(game):
    #belt = game.place_entity(Prototype.TransportBelt, direction=Direction.UP, position=Position(x=0, y=0))
    belt = game.connect_entities(Position(x=0.5, y=0.5), Position(x=0.5, y=8.5), Prototype.TransportBelt)
    game.insert_item(Prototype.IronOre, belt[0], quantity=5)

    inspected_results = game.inspect_entities(Position(x=0, y=0), radius=10)

    assert belt.inventory[Prototype.Coal] == 10
    pass