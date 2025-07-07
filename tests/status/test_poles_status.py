import pytest

from fle.env import Direction, Position, EntityStatus
from fle.env.game_types import Resource, Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        "stone-furnace": 10,
        "burner-inserter": 50,
        "offshore-pump": 4,
        "pipe": 100,
        "small-electric-pole": 50,
        "transport-belt": 200,
        "coal": 100,
        "wooden-chest": 1,
        "assembling-machine-1": 10,
        "boiler": 3,
        "steam-engine": 3,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_connect_power_poles_without_blocking_mining_drill(game):
    coal_position = game.nearest(Resource.Coal)
    coal_patch = game.get_resource_patch(Resource.Coal, coal_position, radius=10)
    assert coal_patch, "No coal patch found within radius"
    game.move_to(coal_patch.bounding_box.center)
    miner = game.place_entity(
        Prototype.ElectricMiningDrill, Direction.UP, coal_patch.bounding_box.center
    )
    game.place_entity(Prototype.IronChest, Direction.UP, miner.drop_position)
    # print out initial inventory
    initial_inventory = game.inspect_inventory()
    print(f"Inventory at starting: {initial_inventory}")

    # Get the nearest water source
    # We will place an offshore pump onto the water
    water_position = game.nearest(Resource.Water)
    assert water_position, "No water source found nearby"
    game.move_to(water_position)
    offshore_pump = game.place_entity(
        Prototype.OffshorePump, Direction.UP, water_position
    )
    assert offshore_pump, "Failed to place offshore pump"
    print(f"Offshore pump placed at {offshore_pump.position}")

    # Place boiler next to offshore pump
    boiler = game.place_entity_next_to(
        Prototype.Boiler, offshore_pump.position, Direction.UP, spacing=2
    )
    assert boiler, "Failed to place boiler"
    print(f"Boiler placed at {boiler.position}")
    print(f"Current inventory: {game.inspect_inventory()}")

    # add coal to the boiler
    game.insert_item(Prototype.Coal, boiler, quantity=5)
    print(f"Inventory after adding coal: {game.inspect_inventory()}")

    # Connect offshore pump to boiler with pipes
    pipes = game.connect_entities(offshore_pump, boiler, Prototype.Pipe)
    assert pipes, "Failed to connect offshore pump to boiler"
    print("Pipes placed between offshore pump and boiler")

    # Place steam engine next to boiler
    steam_engine = game.place_entity_next_to(
        Prototype.SteamEngine, boiler.position, Direction.UP, spacing=2
    )
    assert steam_engine, "Failed to place steam engine"
    print(f"Steam engine placed at {steam_engine.position}")

    # Connect boiler to steam engine with pipes
    pipes = game.connect_entities(boiler, steam_engine, Prototype.Pipe)
    assert pipes, "Failed to connect boiler to steam engine"

    # Connect electric drill to steam engine with power poles
    poles = game.connect_entities(miner, steam_engine, Prototype.SmallElectricPole)
    assert poles.status == EntityStatus.WORKING, (
        "Failed to connect drill to steam engine"
    )


def test_not_connected_poles_is_not_connected(game):
    poles1 = game.connect_entities(
        Position(x=0, y=0),
        Position(x=5, y=0),
        connection_type=Prototype.SmallElectricPole,
    )
    assert poles1.status == EntityStatus.NOT_PLUGGED_IN_ELECTRIC_NETWORK
