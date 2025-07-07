import pytest

from fle.env.entities import Position
from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "iron-chest": 1,
        "iron-plate": 10,
        "assembling-machine-1": 1,
        "copper-cable": 3,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_extract(game):
    chest = game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))
    game.insert_item(Prototype.IronPlate, chest, quantity=10)
    count = game.extract_item(Prototype.IronPlate, chest.position, quantity=2)
    assert game.inspect_inventory()[Prototype.IronPlate] == 2
    assert count == 2


def test_extract_assembler_multi(game):
    assembler = game.place_entity(
        Prototype.AssemblingMachine1, position=Position(x=0, y=0)
    )
    game.set_entity_recipe(assembler, Prototype.ElectronicCircuit)
    game.insert_item(Prototype.IronPlate, assembler, quantity=10)
    game.insert_item(Prototype.CopperCable, assembler, quantity=3)
    inventory = game.inspect_inventory(assembler)
    assert inventory[Prototype.IronPlate] == 10
    assert inventory[Prototype.CopperCable] == 3

    count1 = game.extract_item(Prototype.IronPlate, assembler, quantity=2)
    count2 = game.extract_item(Prototype.CopperCable, assembler, quantity=2)
    assert game.inspect_inventory()[Prototype.IronPlate] == 2
    assert game.inspect_inventory()[Prototype.CopperCable] == 2
    assert count1 == 2 and count2 == 2
