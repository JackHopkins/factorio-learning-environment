import pytest

from factorio_entities import Position, Furnace
from factorio_instance import Direction
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        'coal': 5,
        'iron-chest': 1,
        'iron-plate': 50,
        'iron-ore': 10,
        'stone-furnace': 1,
        'assembly-machine-1': 1,
    }
    instance.reset()
    yield instance
    instance.reset()
def test_get_stone_furnace(game):
    """
    Test to ensure that the inventory of a stone furnace is correctly updated after smelting iron ore
    :param game:
    :return:
    """
    # Check initial inventory
    position = game.nearest(Resource.Stone)
    # 1. Place a stone furnace
    stone_furnace = game.place_entity(Prototype.StoneFurnace, Direction.UP, position)
    assert stone_furnace is not None, "Failed to place stone furnace"

    game.insert_item(Prototype.Coal, stone_furnace, 5)
    game.insert_item(Prototype.IronOre, stone_furnace, 5)
    game.sleep(5)
    retrieved_furnace: Furnace = game.get_entity(Prototype.StoneFurnace, stone_furnace.position)

    assert retrieved_furnace is not None, "Failed to retrieve stone furnace"
    assert retrieved_furnace.furnace_result.get(Prototype.IronPlate, 0) > 0, "Failed to smelt iron plate"
    assert retrieved_furnace.furnace_source.get(Prototype.IronOre, 0) < 5, "Failed to smelt iron ore"
    assert retrieved_furnace.fuel.get(Prototype.Coal, 0) < 5, "Failed to consume coal"

def test_get_iron_chest(game):
    """
    Test to ensure that the inventory of an iron chest is correctly updated after inserting items
    :param game:
    :return:
    """
    # Check initial inventory
    inventory = game.inspect_inventory()
    iron_chest_count = inventory.get(Prototype.IronChest, 0)
    assert iron_chest_count != 0, "Failed to get iron chest count"

    iron_chest = game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))
    game.insert_item(Prototype.Coal, iron_chest, quantity=5)
    game.insert_item(Prototype.IronPlate, iron_chest, quantity=5)

    retrieved_chest = game.get_entity(Prototype.IronChest, iron_chest.position)

    assert retrieved_chest is not None, "Failed to retrieve iron chest"
    assert retrieved_chest.inventory.get(Prototype.Coal, 0) == 5, "Failed to insert coal"
    assert retrieved_chest.inventory.get(Prototype.IronPlate, 0) == 5, "Failed to insert iron plate"

def test_get_assembling_machine(game):
    """
    Test to ensure that the inventory of an assembling machine is correctly updated after crafting items
    :param game:
    :return:
    """
    # Check initial inventory
    inventory = game.inspect_inventory()
    assembling_machine_count = inventory.get(Prototype.AssemblingMachine1, 0)
    assert assembling_machine_count != 0, "Failed to get assembling machine count"

    assembling_machine = game.place_entity(Prototype.AssemblingMachine1, position=Position(x=0, y=0))
    game.set_entity_recipe(assembling_machine, Prototype.IronGearWheel)
    game.insert_item(Prototype.IronPlate, assembling_machine, quantity=5)
    game.craft_item(Prototype.IronGearWheel, 5)
    game.insert_item(Prototype.IronGearWheel, assembling_machine, quantity=5)

    retrieved_machine = game.get_entity(Prototype.AssemblingMachine1, assembling_machine.position)

    assert retrieved_machine is not None, "Failed to retrieve assembling machine"
    assert retrieved_machine.inventory.get(Prototype.IronGearWheel, 0) == 5, "Failed to craft iron gear wheel"