import pytest

from fle.env import entities as ent
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        "coal": 10,
        "iron-chest": 1,
        "iron-plate": 50,
        "iron-ore": 10,
        "stone-furnace": 1,
        "offshore-pump": 1,
        "assembly-machine-1": 1,
        "burner-mining-drill": 1,
        "lab": 1,
        "automation-science-pack": 1,
        "gun-turret": 1,
        "firearm-magazine": 5,
        "transport-belt": 200,
        "boiler": 1,
        "pipe": 20,
    }
    instance.reset()
    yield instance.namespace
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
    stone_furnace = game.place_entity(
        Prototype.StoneFurnace, ent.Direction.UP, position
    )
    assert stone_furnace is not None, "Failed to place stone furnace"
    assert stone_furnace.warnings == ["out of fuel", "no ingredients to smelt"], (
        "Failed to place stone furnace"
    )

    game.insert_item(Prototype.Coal, stone_furnace, 5)
    game.insert_item(Prototype.IronOre, stone_furnace, 5)
    game.sleep(5)
    retrieved_furnace: ent.Furnace = game.get_entities(
        {Prototype.StoneFurnace}, stone_furnace.position
    )[0]

    assert retrieved_furnace is not None, "Failed to retrieve stone furnace"
    assert retrieved_furnace.furnace_result.get(Prototype.IronPlate, 0) > 0, (
        "Failed to smelt iron plate"
    )
    assert retrieved_furnace.furnace_source.get(Prototype.IronOre, 0) < 5, (
        "Failed to smelt iron ore"
    )
    assert retrieved_furnace.fuel.get(Prototype.Coal, 0) < 5, "Failed to consume coal"


def test_get_connected_transport_belts(game):
    """
    Test to ensure that the inventory of a stone furnace is correctly updated after smelting iron ore
    :param game:
    :return:
    """
    start_position = game.nearest(Resource.Stone)
    end_position = game.nearest(Resource.IronOre)

    game.connect_entities(
        start_position, end_position, connection_type=Prototype.TransportBelt
    )

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
    stone_furnace = game.place_entity(
        Prototype.StoneFurnace, ent.Direction.UP, iron_position
    )
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


def test_get_contiguous_transport_belts(game):
    start_position = game.nearest(Resource.Stone)
    end_position = game.nearest(Resource.IronOre)

    game.connect_entities(
        start_position, end_position, connection_type=Prototype.TransportBelt
    )

    transport_belts = game.get_entities({Prototype.TransportBelt}, start_position)

    assert len(transport_belts) == 1, "Failed to retrieve transport belts"


def test_get_filtered_entities(game):
    # put down a chest at origin
    chest = game.place_entity(Prototype.IronChest, position=ent.Position(x=1, y=0))
    # put 100 coal into the chest
    chest = game.insert_item(Prototype.Coal, chest, 5)

    # place a stone furnace
    furnace = game.place_entity(Prototype.StoneFurnace, position=ent.Position(x=3, y=0))

    furnace = game.insert_item(Prototype.Coal, furnace, 5)

    entities = game.get_entities({Prototype.StoneFurnace})

    assert len(entities) == 1


def test_get_entities_hanging_bug(game):
    game.move_to(ent.Position(x=1, y=1))

    # Place offshore pump near water
    water_position = game.nearest(Resource.Water)
    assert water_position, "No water source found nearby"
    game.move_to(water_position)
    offshore_pump = game.place_entity(
        Prototype.OffshorePump, ent.Direction.DOWN, water_position
    )
    assert offshore_pump, "Failed to place offshore pump"

    # Place boiler next to offshore pump
    # Important: The boiler needs to be placed with a spacing of 2 to allow for pipe connections
    boiler = game.place_entity_next_to(
        Prototype.Boiler, offshore_pump.position, ent.Direction.RIGHT, spacing=2
    )
    assert boiler, "Failed to place boiler"

    # add coal to the boiler
    # need to update the boiler var after insert
    boiler = game.insert_item(Prototype.Coal, boiler, quantity=5)

    # Connect offshore pump to boiler with pipes
    pipes = game.connect_entities(offshore_pump, boiler, Prototype.Pipe)
    assert pipes, "Failed to connect offshore pump to boiler"

    # Place steam engine next to boiler
    # Important: The steam engine needs to be placed with a spacing of 2 to allow for pipe connections
    steam_engine = game.place_entity_next_to(
        Prototype.SteamEngine, boiler.position, ent.Direction.RIGHT, spacing=2
    )
    assert steam_engine, "Failed to place steam engine"

    # Connect boiler to steam engine with pipes
    pipes = game.connect_entities(boiler, steam_engine, Prototype.Pipe)
    assert pipes, "Failed to connect boiler to steam engine"

    entities = game.get_entities()
    assert len(entities) == 5


def test_get_assembling_machine_1(game):
    """
    Test to ensure that the inventory of an assembling machine is correctly updated after crafting items
    :param game:
    :return:
    """
    # Check initial inventory
    inventory = game.inspect_inventory()
    assembling_machine_count = inventory.get(Prototype.AssemblingMachine1, 0)
    assert assembling_machine_count != 0, "Failed to get assembling machine count"

    assembling_machine = game.place_entity(
        Prototype.AssemblingMachine1, position=ent.Position(x=0, y=0)
    )
    game.set_entity_recipe(assembling_machine, Prototype.IronGearWheel)
    game.insert_item(Prototype.IronPlate, assembling_machine, quantity=5)

    retrieved_machine = game.get_entities({Prototype.AssemblingMachine1})[0]

    assert retrieved_machine is not None, "Failed to retrieve assembling machine"


def test_get_pipe_groups(game):
    # game.craft_item(Prototype.OffshorePump)

    water_patch = game.get_resource_patch(Resource.Water, game.nearest(Resource.Water))
    game.move_to(water_patch.bounding_box.left_top)
    offshore_pump = game.place_entity(
        Prototype.OffshorePump, position=game.nearest(Resource.Water)
    )
    boiler = game.place_entity_next_to(
        Prototype.Boiler,
        reference_position=offshore_pump.position,
        direction=offshore_pump.direction,
        spacing=5,
    )
    game.connect_entities(boiler, offshore_pump, connection_type=Prototype.Pipe)

    pipes = game.get_entities()
    assert len(pipes) == 3
