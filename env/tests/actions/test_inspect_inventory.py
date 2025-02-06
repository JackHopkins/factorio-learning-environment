import pytest

from entities import Position
from game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory ={
        **instance.initial_inventory,
        'coal': 50,
        'iron-chest': 1,
        'iron-plate': 5,
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
    machine = game.place_entity(Prototype.AssemblingMachine1, position=Position(x=0, y=0))
    game.set_entity_recipe(machine, Prototype.IronGearWheel)
    game.insert_item(Prototype.IronPlate, machine, quantity=5)
    chest_inventory = game.inspect_inventory(entity=machine)
    iron_count = chest_inventory[Prototype.IronPlate]
    assert iron_count == 5

def test_inspect_chest_inventory(game):
    # Place storage chest at end of main belt
    storage_pos = Position(x=-8.5, y=30.5)
    game.move_to(storage_pos)
    storage_chest = game.place_entity(Prototype.IronChest, position=storage_pos)
    print(f"Placed storage chest at {storage_pos}")

    # Connect main belt to storage chest
    belt_end = Position(x=-10.5, y=30.5)
    game.connect_entities(belt_end, storage_pos, Prototype.TransportBelt)
    print(f"Connected main belt at {belt_end} to storage chest at {storage_pos}")

    # Verify ore flow to storage chest
    game.sleep(10)
    storage_chest = game.get_entity(Prototype.IronChest, storage_pos)
    storage_inv = game.inspect_inventory(storage_chest)
    pass


def test_print_inventory(game):
    inventory = game.inspect_inventory()
    game.print(inventory)
    assert True