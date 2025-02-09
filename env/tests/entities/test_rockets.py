import json
from entities import Position, Direction, EntityStatus
from game_types import Resource, Prototype
import pytest

@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        'rocket-silo': 1,
        'big-electric-pole': 10,
        'small-electric-pole': 10,
        'steel-chest': 5,
        'fast-inserter': 10,
        'pipe': 100,
        'offshore-pump': 1,
        'steam-engine': 5,
        'centrifuge': 1,
        'inserter': 5,
        'iron-chest': 5,
        'rocket-control-unit': 100,
        'rocket-fuel': 100,
        'low-density-structure': 100
    }
    instance.speed(10)
    instance.reset()
    yield instance.namespace

def test_rocket_launch(game):
    # Initialize starting position
    pos = Position(x=0, y=0)
    game.move_to(pos)

    # Set up basic power generation
    water_pos = game.nearest(Resource.Water)
    game.move_to(water_pos)
    pump = game.place_entity(Prototype.OffshorePump, position=water_pos)
    boiler = game.place_entity_next_to(Prototype.Boiler, pump.position, Direction.DOWN, spacing=5)
    engine = game.place_entity_next_to(Prototype.SteamEngine, boiler.position, Direction.DOWN, spacing=5)
    game.connect_entities(pump, boiler, Prototype.Pipe)
    game.connect_entities(boiler, engine, Prototype.Pipe)
    game.insert_item(Prototype.Coal, boiler, quantity=50)

    # Place rocket silo with spacing from power generation
    silo = game.place_entity_next_to(Prototype.RocketSilo, engine.position, Direction.RIGHT, spacing=5)

    # Left side setup (input components)
    # LowDensityStructure setup
    lds_chest = game.place_entity_next_to(Prototype.SteelChest, silo.position, Direction.LEFT, spacing=1)
    lds_inserter = game.place_entity_next_to(Prototype.FastInserter, lds_chest.position, Direction.RIGHT)
    game.move_to(lds_chest.position)


    # RocketFuel setup
    fuel_chest = game.place_entity_next_to(Prototype.SteelChest, lds_chest.position, Direction.DOWN, spacing=2)
    fuel_inserter = game.place_entity_next_to(Prototype.FastInserter, fuel_chest.position, Direction.RIGHT)


    # RocketControlUnit setup
    rcu_chest = game.place_entity_next_to(Prototype.SteelChest, lds_chest.position, Direction.UP, spacing=2)
    rcu_inserter = game.place_entity_next_to(Prototype.FastInserter, rcu_chest.position, Direction.RIGHT)

    game.connect_entities(engine, silo, Prototype.SmallElectricPole)

    # Connect power to all inserters
    inserters = [lds_inserter, fuel_inserter, rcu_inserter]
    for inserter in inserters:
        game.connect_entities(engine, inserter, Prototype.SmallElectricPole)

    for i in range(13):
        game.insert_item(Prototype.RocketFuel, fuel_chest, quantity=100)
        game.insert_item(Prototype.RocketControlUnit, rcu_chest, quantity=100)
        game.insert_item(Prototype.LowDensityStructure, lds_chest, quantity=100)

        inventory_items = {'rocket-control-unit': 100, 'rocket-fuel': 100, 'low-density-structure': 100}
        inventory_items_json = json.dumps(inventory_items)
        game.instance.add_command(f"/c global.actions.initialise_inventory({1}, '{inventory_items_json}')", raw=True)
        game.instance.execute_transaction()
        game.sleep(15)



    # Verify initial state
    # assert silo.status == EntityStatus.NORMAL
    assert silo.rocket_parts == 0
    assert silo.launch_count == 0

    # Wait for rocket parts to be inserted and assembled
    game.sleep(100)

    # Get fresh reference to silo
    silo = game.get_entities({Prototype.RocketSilo})[0]

    # Verify rocket construction has started
    assert silo.status == EntityStatus.PREPARING_ROCKET_FOR_LAUNCH

    # Wait for rocket construction to complete
    game.sleep(180)
    silo = game.get_entities({Prototype.RocketSilo})[0]

    # Verify rocket is ready
    assert silo.status == EntityStatus.WAITING_TO_LAUNCH_ROCKET

    # Launch the rocket
    silo = game.launch_rocket(silo)

    # Verify launch sequence started
    assert silo.status == EntityStatus.LAUNCHING_ROCKET

    # Wait for launch to complete
    game.sleep(10)
    silo = game.get_entities({Prototype.RocketSilo})[0]

    # Verify successful launch
    assert silo.status == EntityStatus.ITEM_INGREDIENT_SHORTAGE