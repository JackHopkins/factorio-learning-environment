import pytest

from fle.env.entities import Position, BuildingBox
from fle.env.game_types import Prototype, Resource, RecipeName


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "stone-furnace": 1,
        "transport-belt": 30,
        "boiler": 1,
        "storage-tank": 5,
        "pipe-to-ground": 50,
        "pumpjack": 5,
        "oil-refinery": 5,
        "small-electric-pole": 50,
        "steam-engine": 1,
        "offshore-pump": 1,
        "pipe": 100,
        "iron-plate": 50,
        "copper-plate": 20,
        "coal": 50,
    }

    instance.reset()

    yield instance.namespace


def test_full_oil_chain(game):
    # First find water for power generation
    water_pos = game.nearest(Resource.Water)
    print(f"Found water at {water_pos}")

    # Place offshore pump
    game.move_to(water_pos)
    offshore_pump = game.place_entity(Prototype.OffshorePump, position=water_pos)
    print(f"Placed offshore pump at {offshore_pump.position}")

    # Place boiler with space for connections
    building_box = BuildingBox(
        width=Prototype.Boiler.WIDTH + 4, height=Prototype.Boiler.HEIGHT + 4
    )
    coords = game.nearest_buildable(
        Prototype.Boiler, building_box, offshore_pump.position
    )
    game.move_to(coords.center)
    boiler = game.place_entity(Prototype.Boiler, position=coords.center)
    print(f"Placed boiler at {boiler.position}")

    # Place steam engine
    building_box = BuildingBox(
        width=Prototype.SteamEngine.WIDTH + 4, height=Prototype.SteamEngine.HEIGHT + 4
    )
    coords = game.nearest_buildable(
        Prototype.SteamEngine, building_box, boiler.position
    )
    game.move_to(coords.center)
    steam_engine = game.place_entity(Prototype.SteamEngine, position=coords.center)
    print(f"Placed steam engine at {steam_engine.position}")

    # Connect water system
    game.move_to(offshore_pump.position)
    game.connect_entities(offshore_pump, boiler, Prototype.Pipe)
    game.connect_entities(boiler, steam_engine, Prototype.Pipe)
    print("Connected water and steam pipes")

    # Add fuel to boiler
    boiler = game.insert_item(Prototype.Coal, boiler, 50)
    print("Added coal to boiler")

    # Move to oil and place pumpjack directly
    oil_pos = game.nearest(Resource.CrudeOil)
    game.move_to(oil_pos)
    pumpjack = game.place_entity(Prototype.PumpJack, position=oil_pos)
    print(f"Placed pumpjack at {pumpjack.position}")

    # Connect power to pumpjack
    game.connect_entities(steam_engine, pumpjack, Prototype.SmallElectricPole)
    print("Connected power to pumpjack")

    # Place oil refinery 15 spaces east of pumpjack
    refinery_pos = Position(x=pumpjack.position.x + 15, y=pumpjack.position.y)
    game.move_to(refinery_pos)
    refinery = game.place_entity(Prototype.OilRefinery, position=refinery_pos)
    print(f"Placed oil refinery at {refinery.position}")

    # Set recipe to basic oil processing
    refinery = game.set_entity_recipe(refinery, RecipeName.BasicOilProcessing)
    print("Set refinery recipe to basic oil processing")

    # Connect power to refinery
    game.connect_entities(pumpjack, refinery, Prototype.SmallElectricPole)
    print("Connected power to refinery")

    # Connect pumpjack to refinery with pipes
    game.connect_entities(
        pumpjack, refinery, {Prototype.UndergroundPipe, Prototype.Pipe}
    )
    pass


def test_fix_storage_tank_connection(game):
    # First find water for power generation
    water_pos = game.nearest(Resource.Water)
    print(f"Found water at {water_pos}")

    # Place offshore pump
    game.move_to(water_pos)
    offshore_pump = game.place_entity(Prototype.OffshorePump, position=water_pos)
    print(f"Placed offshore pump at {offshore_pump.position}")

    # Place boiler with space for connections
    building_box = BuildingBox(
        width=Prototype.Boiler.WIDTH + 4, height=Prototype.Boiler.HEIGHT + 4
    )
    coords = game.nearest_buildable(
        Prototype.Boiler, building_box, offshore_pump.position
    )
    game.move_to(coords.center)
    boiler = game.place_entity(Prototype.Boiler, position=coords.center)
    print(f"Placed boiler at {boiler.position}")

    # Place steam engine
    building_box = BuildingBox(
        width=Prototype.SteamEngine.WIDTH + 4, height=Prototype.SteamEngine.HEIGHT + 4
    )
    coords = game.nearest_buildable(
        Prototype.SteamEngine, building_box, boiler.position
    )
    game.move_to(coords.center)
    steam_engine = game.place_entity(Prototype.SteamEngine, position=coords.center)
    print(f"Placed steam engine at {steam_engine.position}")

    # Connect water system
    game.connect_entities(offshore_pump, boiler, Prototype.Pipe)
    game.connect_entities(boiler, steam_engine, Prototype.Pipe)
    print("Connected water and steam pipes")

    # Add fuel to boiler
    boiler = game.insert_item(Prototype.Coal, boiler, 50)
    print("Added coal to boiler")

    # Move to oil and place pumpjack directly
    jack_pos = Position(x=32.5, y=49.5)
    game.move_to(jack_pos)
    pumpjack = game.place_entity(Prototype.PumpJack, position=jack_pos)
    print(f"Placed pumpjack at {pumpjack.position}")

    # Connect power to pumpjack
    game.connect_entities(steam_engine, pumpjack, Prototype.SmallElectricPole)
    print("Connected power to pumpjack")

    # Place oil refinery 15 spaces east of pumpjack
    refinery_pos = Position(x=pumpjack.position.x + 15, y=pumpjack.position.y)
    game.move_to(refinery_pos)
    refinery = game.place_entity(Prototype.OilRefinery, position=refinery_pos)
    print(f"Placed oil refinery at {refinery.position}")

    # Set recipe to basic oil processing
    refinery = game.set_entity_recipe(refinery, RecipeName.BasicOilProcessing)
    print("Set refinery recipe to basic oil processing")

    # Connect power to refinery
    game.connect_entities(pumpjack, refinery, Prototype.SmallElectricPole)
    print("Connected power to refinery")

    # Connect pumpjack to refinery with pipes
    game.connect_entities(
        pumpjack, refinery, {Prototype.UndergroundPipe, Prototype.Pipe}
    )
    print("Connected pumpjack to refinery with pipes")

    # Place storage tank for petroleum gas output
    # Place it 10 spaces east of refinery
    tank_pos = Position(x=refinery.position.x + 10, y=refinery.position.y)
    game.move_to(tank_pos)
    storage_tank = game.place_entity(Prototype.StorageTank, position=tank_pos)
    print(f"Placed storage tank at {storage_tank.position}")

    # Connect refinery to storage tank
    game.connect_entities(
        refinery, storage_tank, {Prototype.UndergroundPipe, Prototype.Pipe}
    )
    pass
