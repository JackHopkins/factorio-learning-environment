import pytest

from factorio_entities import Position, Furnace
from factorio_instance import Direction
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        'coal': 10,
        'iron-chest': 1,
        'iron-plate': 50,
        'iron-ore': 10,
        'stone-furnace': 1,
        'assembly-machine-1': 1,
        'burner-mining-drill': 1,
        'lab': 1,
        'automation-science-pack': 1,
        'gun-turret': 1,
        'firearm-magazine': 5,
        'transport-belt': 50,
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
    game.move_to(position)
    stone_furnace = game.place_entity(Prototype.StoneFurnace, Direction.UP, position)
    assert stone_furnace is not None, "Failed to place stone furnace"
    assert stone_furnace.warnings == ['out of fuel', 'no ingredients to smelt'], "Failed to place stone furnace"

    game.insert_item(Prototype.Coal, stone_furnace, 5)
    game.insert_item(Prototype.IronOre, stone_furnace, 5)
    game.sleep(5)
    retrieved_furnace: Furnace = game.get_entities({Prototype.StoneFurnace}, stone_furnace.position)[0]

    assert retrieved_furnace is not None, "Failed to retrieve stone furnace"
    assert retrieved_furnace.furnace_result.get(Prototype.IronPlate, 0) > 0, "Failed to smelt iron plate"
    assert retrieved_furnace.furnace_source.get(Prototype.IronOre, 0) < 5, "Failed to smelt iron ore"
    assert retrieved_furnace.fuel.get(Prototype.Coal, 0) < 5, "Failed to consume coal"

def test_get_connected_transport_belts(game):
    """
    Test to ensure that the inventory of a stone furnace is correctly updated after smelting iron ore
    :param game:
    :return:
    """
    start_position = game.nearest(Resource.Stone)
    end_position = game.nearest(Resource.IronOre)

    game.connect_entities(start_position, end_position, connection_type=Prototype.TransportBelt)

    transport_belts = game.get_entities({Prototype.TransportBelt}, start_position)

    assert len(transport_belts) == 1, "Failed to retrieve transport belts"

def test_get_entities_bug(game):
    # Check initial inventory
    iron_position = game.nearest(Resource.Stone)
    game.move_to(iron_position)
    print(f"Moved to iron patch at {iron_position}")
    game.harvest_resource(iron_position, 20)

    game.craft_item(Prototype.StoneFurnace, 3)

    # 1. Place a stone furnace
    stone_furnace = game.place_entity(Prototype.WoodenChest, Direction.UP, iron_position)
    assert stone_furnace is not None, "Failed to place stone furnace"

    game.insert_item(Prototype.Coal, stone_furnace, 5)
    game.insert_item(Prototype.IronOre, stone_furnace, 5)
    game.sleep(1)
    # print("Inserted coal and iron ore into the furnace")

    furnaces = game.get_entities({Prototype.StoneFurnace})
    print(furnaces)

def test_get_no_entities(game):
    furnaces = game.get_entities()
    assert not furnaces

def test_get_filtered_entities(game):
    # put down a chest at origin
    chest = game.place_entity(Prototype.IronChest, position=Position(x=1, y=0))
    # put 100 coal into the chest
    chest = game.insert_item(Prototype.Coal, chest, 5)

    # place a stone furnace
    furnace = game.place_entity(Prototype.StoneFurnace, position=Position(x=3, y=0))

    furnace = game.insert_item(Prototype.Coal, furnace, 5)

    entities = game.get_entities({Prototype.StoneFurnace})

    assert len(entities) == 1