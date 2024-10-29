import pytest

from factorio_entities import Entity, Position
from factorio_instance import Direction
from factorio_types import Prototype, Resource, PrototypeName


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        'stone-furnace': 10,
        'burner-inserter': 50,
        'offshore-pump': 4,
        'pipe': 100,
        'small-electric-pole': 50,
        'transport-belt': 200,
        'coal': 100,
        'wooden-chest': 1,
        'assembling-machine': 10,
    }
    instance.reset()
    yield instance
    instance.reset()
def test_connect_steam_engine_to_assembler_with_electricity_poles(game):
    """
    Place a steam engine and an assembling machine next to each other.
    Connect them with electricity poles.
    :param game:
    :return:
    """
    steam_engine = game.place_entity(Prototype.SteamEngine, position=Position(x=0, y=0))
    assembler = game.place_entity_next_to(Prototype.AssemblingMachine1, reference_position=steam_engine.position,
                                          direction=game.RIGHT, spacing=10)
    game.move_to(Position(x=5, y=5))
    diagonal_assembler = game.place_entity(Prototype.AssemblingMachine1, position=Position(x=10, y=10))

    # check to see if the assemblers are connected to the electricity network
    inspected_assemblers = game.inspect_entities(position=diagonal_assembler.position, radius=50).get_entities(
        Prototype.AssemblingMachine1)

    for a in inspected_assemblers:
        assert a.warning == 'not connected to power network'

    poles_in_inventory = game.inspect_inventory()[Prototype.SmallElectricPole]

    poles = game.connect_entities(steam_engine, assembler, connection_type=Prototype.SmallElectricPole)
    poles2 = game.connect_entities(steam_engine, diagonal_assembler, connection_type=Prototype.SmallElectricPole)

    current_poles_in_inventory = game.inspect_inventory()[Prototype.SmallElectricPole]
    spent_poles = (poles_in_inventory - current_poles_in_inventory)

    assert spent_poles == len(poles + poles2)

    # check to see if the assemblers are connected to the electricity network
    inspected_assemblers = game.inspect_entities(position=diagonal_assembler.position, radius=50).get_entities(Prototype.AssemblingMachine1)

    for assembler in inspected_assemblers:
        assert assembler.warning == 'not receiving electricity'

def test_connect_power_poles_without_blocking_mining_drill(game):
    coal_position = game.nearest(Resource.Coal)
    coal_patch = game.get_resource_patch(Resource.Coal, coal_position, radius=10)
    assert coal_patch, "No coal patch found within radius"
    game.move_to(coal_patch.bounding_box.center)
    miner = game.place_entity(Prototype.ElectricMiningDrill, Direction.UP, coal_patch.bounding_box.center)

    # print out initial inventory
    initial_inventory = game.inspect_inventory()
    print(f"Inventory at starting: {initial_inventory}")

    # Get the nearest water source
    # We will place an offshore pump onto the water
    water_position = game.nearest(Resource.Water)
    assert water_position, "No water source found nearby"
    game.move_to(water_position)
    offshore_pump = game.place_entity(Prototype.OffshorePump, Direction.UP, water_position)
    assert offshore_pump, "Failed to place offshore pump"
    print(f"Offshore pump placed at {offshore_pump.position}")

    # Place boiler next to offshore pump
    boiler = game.place_entity_next_to(Prototype.Boiler, offshore_pump.position, Direction.UP, spacing=2)
    assert boiler, "Failed to place boiler"
    print(f"Boiler placed at {boiler.position}")
    print(f"Current inventory: {game.inspect_inventory()}")

    # add coal to the boiler
    boiler_with_coal = game.insert_item(Prototype.Coal, boiler, quantity=5)
    print(f"Inventory after adding coal: {game.inspect_inventory()}")

    # Connect offshore pump to boiler with pipes
    pipes = game.connect_entities(offshore_pump, boiler, Prototype.Pipe)
    assert pipes, "Failed to connect offshore pump to boiler"
    print(f"Pipes placed between offshore pump and boiler")

    # Place steam engine next to boiler
    steam_engine = game.place_entity_next_to(Prototype.SteamEngine, boiler.position, Direction.UP, spacing=2)
    assert steam_engine, "Failed to place steam engine"
    print(f"Steam engine placed at {steam_engine.position}")

    # Connect boiler to steam engine with pipes
    pipes = game.connect_entities(boiler, steam_engine, Prototype.Pipe)
    assert pipes, "Failed to connect boiler to steam engine"

    # Connect electric drill to steam engine with power poles
    poles = game.connect_entities(miner, steam_engine, Prototype.SmallElectricPole)
    assert poles, "Failed to connect drill to steam engine"
    print(f"Connected electric mining drill to steam engine with power poles")

    # Get the mining drill status
    drill = game.get_entity(Prototype.ElectricMiningDrill, miner.position)
    assert drill, "Failed to get mining drill"
    assert not drill.warnings, f"Drill has warnings: {drill.warnings}"