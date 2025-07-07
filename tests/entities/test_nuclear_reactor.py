import pytest

from fle.env import Direction, EntityStatus, Position
from fle.env.game_types import Prototype, Resource, RecipeName


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        "nuclear-reactor": 1,
        "uranium-fuel-cell": 10,
        "heat-exchanger": 5,
        "heat-pipe": 100,
        "pipe": 100,
        "offshore-pump": 1,
        "steam-engine": 5,
        "centrifuge": 1,
        "uranium-ore": 100,
        "inserter": 5,
        "iron-chest": 5,
    }
    instance.speed(10)
    instance.reset()
    yield instance.namespace


def test_centrifuge(game):
    # Initialize starting position
    pos = Position(x=0, y=0)
    game.move_to(pos)

    # Set up basic power generation first (steam engine system)
    water_pos = game.nearest(Resource.Water)
    game.move_to(water_pos)

    # Place and connect basic power setup
    pump = game.place_entity(Prototype.OffshorePump, position=water_pos)
    boiler = game.place_entity_next_to(
        Prototype.Boiler, pump.position, Direction.RIGHT, spacing=5
    )
    engine = game.place_entity_next_to(
        Prototype.SteamEngine, boiler.position, Direction.DOWN, spacing=5
    )

    # Connect water system
    game.connect_entities(pump, boiler, Prototype.Pipe)
    game.connect_entities(boiler, engine, Prototype.Pipe)

    # Add fuel to boiler
    game.insert_item(Prototype.Coal, boiler, quantity=5)

    # Place centrifuge with some spacing from power generation
    centrifuge = game.place_entity_next_to(
        Prototype.Centrifuge, engine.position, Direction.RIGHT, spacing=2
    )
    inserter = game.place_entity_next_to(
        Prototype.BurnerInserter, centrifuge.position, Direction.DOWN
    )
    chest = game.place_entity_next_to(
        Prototype.IronChest, inserter.position, Direction.DOWN
    )
    # Connect power to centrifuge
    game.connect_entities(engine, centrifuge, Prototype.SmallElectricPole)

    # Insert uranium ore for processing
    game.get_prototype_recipe(RecipeName.UraniumProcessing)
    game.set_entity_recipe(centrifuge, RecipeName.UraniumProcessing)
    game.insert_item(Prototype.UraniumOre, centrifuge, quantity=50)

    assert game.inspect_inventory(centrifuge)[Prototype.UraniumOre] >= 30

    game.insert_item(Prototype.Coal, inserter, quantity=30)

    # Wait for processing to begin
    game.sleep(20)

    # Get fresh reference to centrifuge
    centrifuge = game.get_entities({Prototype.Centrifuge})[0]

    # Verify centrifuge is operational
    assert centrifuge.energy > 0
    assert centrifuge.status == EntityStatus.WORKING

    # Wait for processing to complete
    game.sleep(30)

    # Verify output exists (should have both U-235 and U-238)
    inventory = game.inspect_inventory(chest)
    assert (
        inventory.get(Prototype.Uranium235, 0) > 0
        or inventory.get(Prototype.Uranium238, 0) > 0
    )


def test_nuclear_reactor(game):
    # Initialize starting position at origin coordinates
    pos = Position(x=0, y=0)
    game.move_to(pos)

    # Place nuclear reactor at the starting position and fuel it
    reactor = game.place_entity(Prototype.NuclearReactor, position=pos)
    game.insert_item(Prototype.UraniumFuelCell, reactor, quantity=10)

    # Place heat exchanger below the reactor to transfer heat to water
    heat_exchanger = game.place_entity_next_to(
        Prototype.HeatExchanger, reactor.position, Direction.DOWN
    )

    # Find nearest water source and move to it
    water_pos = game.nearest(Resource.Water)
    game.move_to(water_pos)

    # Place offshore pump at water source to extract water
    pump = game.place_entity(Prototype.OffshorePump, position=water_pos)

    # Connect heat exchanger to pump with pipes to transfer water
    game.connect_entities(heat_exchanger, pump, Prototype.Pipe)

    # Place steam engine 3 units below heat exchanger to generate electricity from steam
    engine = game.place_entity_next_to(
        Prototype.SteamEngine, heat_exchanger.position, Direction.DOWN, spacing=3
    )

    # Place assembling machine 2 units to the right of steam engine as power consumer
    assembler = game.place_entity_next_to(
        Prototype.AssemblingMachine1, engine.position, Direction.RIGHT, spacing=2
    )

    # Connect steam engine to heat exchanger with pipes for steam transfer
    game.connect_entities(engine, heat_exchanger, Prototype.Pipe)

    # Connect steam engine to assembler with power poles for electricity distribution
    game.connect_entities(engine, assembler, Prototype.SmallElectricPole)

    # Wait 150 ticks for the system to start operating
    game.sleep(150)

    # Get reference to assembler to check its power status
    assembler = game.get_entities({Prototype.AssemblingMachine1})[0]

    # Verify that assembler is receiving power, indicating the nuclear power system is working
    assert assembler.energy > 0
