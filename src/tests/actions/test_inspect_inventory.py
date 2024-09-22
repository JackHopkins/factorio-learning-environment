import pytest

from factorio_entities import Position
from factorio_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory ={
        **instance.initial_inventory,
        'coal': 50,
        'iron-chest': 1
    }
    instance.reset()
    yield instance

def test_inspect_inventory(game):
    assert game.inspect_inventory().get(Prototype.Coal, 0) == 50
    inventory = game.inspect_inventory()
    coal_count = inventory[Prototype.Coal]
    assert coal_count != 0
    chest = game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))
    game.insert_item(Prototype.Coal, chest, quantity=5)

    chest_inventory = game.inspect_inventory(entity=chest)
    chest_coal_count = chest_inventory[Prototype.Coal]
    assert chest_coal_count == 5
    game.reset()

def test_inspect_assembling_machine_inventory(game):
    machine = game.place_entity(Prototype.AssemblingMachine1, position=Position(x=0, y=0))

    chest_inventory = game.inspect_inventory(entity=machine)
    chest_coal_count = chest_inventory[Prototype.Coal]
    assert chest_coal_count == 5
    game.reset()


def test_print_inventory(game):
    inventory = game.inspect_inventory()
    game.print(inventory)
    assert True