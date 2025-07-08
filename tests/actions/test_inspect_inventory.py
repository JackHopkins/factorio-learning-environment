import pytest

from fle.env.entities import Position
from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        "coal": 50,
        "iron-chest": 1,
        "iron-plate": 5,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_inspect_inventory(game):
    assert game.inspect_inventory().get(Prototype.Coal, 0) == 50
    inventory = game.inspect_inventory()
    coal_count = inventory[Prototype.Coal]
    assert coal_count != 0
    chest = game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))
    chest = game.insert_item(Prototype.Coal, chest, quantity=5)

    chest_inventory = game.inspect_inventory(entity=chest)
    chest_coal_count = chest_inventory[Prototype.Coal]
    assert chest_coal_count == 5


def test_inspect_assembling_machine_inventory(game):
    machine = game.place_entity(
        Prototype.AssemblingMachine1, position=Position(x=0, y=0)
    )
    game.set_entity_recipe(machine, Prototype.IronGearWheel)
    game.insert_item(Prototype.IronPlate, machine, quantity=5)
    chest_inventory = game.inspect_inventory(entity=machine)
    iron_count = chest_inventory[Prototype.IronPlate]
    assert iron_count == 5


def test_print_inventory(game):
    inventory = game.inspect_inventory()
    game.print(inventory)
    assert True
