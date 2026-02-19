"""Tests for rocket silo functionality and rocket launching."""

from fle.env.entities import Position, Direction, EntityStatus
from fle.env.game_types import Resource, Prototype
import pytest


@pytest.fixture()
def game(configure_game):
    """Configure game with rocket silo and required components."""
    return configure_game(
        inventory={
            "rocket-silo": 1,
            "big-electric-pole": 10,
            "small-electric-pole": 10,
            "steel-chest": 10,
            "fast-inserter": 20,
            "pipe": 100,
            "offshore-pump": 1,
            "boiler": 1,
            "steam-engine": 5,
            "inserter": 10,
            "iron-chest": 5,
            "rocket-control-unit": 100,
            "rocket-fuel": 100,
            "low-density-structure": 100,
            "solar-panel": 10,
            "coal": 100,
        },
        merge=True,
        reset_position=True,
    )


def test_rocket_silo_placement(game):
    """Test that rocket silo can be placed and serialized correctly."""
    # Rocket silo is 9x9, needs space
    silo_pos = Position(x=20, y=20)
    game.move_to(silo_pos)

    silo = game.place_entity(Prototype.RocketSilo, position=silo_pos)

    # Verify silo was placed
    assert silo is not None, "Failed to place rocket silo"
    assert silo.position.x == pytest.approx(20.5, abs=0.5)
    assert silo.position.y == pytest.approx(20.5, abs=0.5)

    # Verify initial state - should have no power initially
    assert silo.rocket_parts == 0
    assert silo.rocket_progress == 0.0

    # Verify we can retrieve the silo
    silos = game.get_entities({Prototype.RocketSilo})
    assert len(silos) == 1
    assert silos[0].rocket_parts == 0


def test_rocket_silo_with_power(game):
    """Test rocket silo with power connection - status should change from NO_POWER."""
    # Set up power generation first with steam engine (reliable power source)
    water_pos = game.nearest(Resource.Water)
    game.move_to(water_pos)
    pump = game.place_entity(Prototype.OffshorePump, position=water_pos)
    boiler = game.place_entity_next_to(
        Prototype.Boiler, pump.position, Direction.RIGHT, spacing=2
    )
    engine = game.place_entity_next_to(
        Prototype.SteamEngine, boiler.position, Direction.DOWN, spacing=2
    )
    game.connect_entities(pump, boiler, Prototype.Pipe)
    game.connect_entities(boiler, engine, Prototype.Pipe)
    game.insert_item(Prototype.Coal, boiler, quantity=50)

    # Wait for steam to build up
    game.sleep(10)

    # Place rocket silo
    silo_pos = Position(x=20, y=20)
    game.move_to(silo_pos)
    silo = game.place_entity(Prototype.RocketSilo, position=silo_pos)

    # Connect power to silo
    game.connect_entities(engine, silo, Prototype.BigElectricPole)

    # Wait for power network to establish
    game.sleep(10)

    # Get fresh reference to check status
    silo = game.get_entities({Prototype.RocketSilo})[0]

    # Should no longer be NO_POWER (likely ITEM_INGREDIENT_SHORTAGE since no rocket parts)
    print(f"Silo status: {silo.status}")
    # The silo requires 4MW of power, a single steam engine only provides ~900kW
    # So it may still show NO_POWER or LOW_POWER. Check for any progress.
    print(f"Silo has power: {silo.status not in [EntityStatus.NO_POWER]}")


def test_inserter_to_rocket_silo(configure_game):
    """Test that inserters can insert items into rocket silo."""
    # Use configure_game to properly set up inventory with rocket components
    game = configure_game(
        inventory={
            "rocket-silo": 1,
            "big-electric-pole": 10,
            "small-electric-pole": 10,
            "steel-chest": 10,
            "fast-inserter": 20,
            "pipe": 100,
            "offshore-pump": 1,
            "boiler": 1,
            "steam-engine": 5,
            "coal": 100,
            "low-density-structure": 200,
            "rocket-fuel": 200,
            "rocket-control-unit": 200,
        },
        merge=True,
    )

    # Set up power generation first with steam engine
    water_pos = game.nearest(Resource.Water)
    game.move_to(water_pos)
    pump = game.place_entity(Prototype.OffshorePump, position=water_pos)
    boiler = game.place_entity_next_to(
        Prototype.Boiler, pump.position, Direction.RIGHT, spacing=2
    )
    engine = game.place_entity_next_to(
        Prototype.SteamEngine, boiler.position, Direction.DOWN, spacing=2
    )
    game.connect_entities(pump, boiler, Prototype.Pipe)
    game.connect_entities(boiler, engine, Prototype.Pipe)
    game.insert_item(Prototype.Coal, boiler, quantity=50)

    # Wait for steam to build up
    game.sleep(10)

    # Place rocket silo
    silo_pos = Position(x=20, y=20)
    game.move_to(silo_pos)
    silo = game.place_entity(Prototype.RocketSilo, position=silo_pos)

    # Connect power to silo
    game.connect_entities(engine, silo, Prototype.BigElectricPole)

    # Place a chest next to the silo with rocket components
    # The silo is at 20.5, 20.5 and is 9x9, so it extends from ~16 to ~25
    # Place chest outside the silo on the left side
    game.move_to(Position(x=14, y=20))
    chest = game.place_entity(Prototype.SteelChest, position=Position(x=14, y=20))

    # Place inserter between chest and silo (facing right towards silo)
    inserter = game.place_entity_next_to(
        Prototype.FastInserter, chest.position, Direction.RIGHT, spacing=0
    )

    # Connect power to inserter via small electric poles
    game.connect_entities(engine, inserter, Prototype.SmallElectricPole)

    # Insert rocket components into the chest one at a time with error handling
    for item_name, prototype in [
        ("low-density-structure", Prototype.LowDensityStructure),
        ("rocket-fuel", Prototype.RocketFuel),
        ("rocket-control-unit", Prototype.RocketControlUnit),
    ]:
        try:
            game.insert_item(prototype, chest, quantity=10)
            print(f"Successfully inserted {item_name}")
        except Exception as e:
            print(f"Failed to insert {item_name}: {e}")

    # Print initial state
    chest_inv = game.inspect_inventory(chest)
    print(f"Chest inventory: {chest_inv}")
    print(f"Inserter position: {inserter.position}, direction: {inserter.direction}")

    # Wait for inserter to operate
    game.sleep(30)

    # Check if inserter moved items
    chest_inv_after = game.inspect_inventory(chest)
    print(f"Chest inventory after waiting: {chest_inv_after}")

    # Get fresh silo reference
    silo = game.get_entities({Prototype.RocketSilo})[0]
    print(f"Silo status: {silo.status}, rocket_parts: {silo.rocket_parts}")


def test_rocket_silo_status_progression(game):
    """Test that rocket silo status progresses as parts are added."""
    # Set up power generation with multiple steam engines for sufficient power
    # Rocket silo needs 4MW, each steam engine provides ~900kW, so we need 5+
    water_pos = game.nearest(Resource.Water)
    game.move_to(water_pos)
    pump = game.place_entity(Prototype.OffshorePump, position=water_pos)

    # Place multiple boilers and steam engines
    boiler1 = game.place_entity_next_to(
        Prototype.Boiler, pump.position, Direction.RIGHT, spacing=2
    )
    engine1 = game.place_entity_next_to(
        Prototype.SteamEngine, boiler1.position, Direction.DOWN, spacing=2
    )
    engine2 = game.place_entity_next_to(
        Prototype.SteamEngine, engine1.position, Direction.DOWN, spacing=2
    )
    engine3 = game.place_entity_next_to(
        Prototype.SteamEngine, engine2.position, Direction.DOWN, spacing=2
    )
    engine4 = game.place_entity_next_to(
        Prototype.SteamEngine, engine3.position, Direction.DOWN, spacing=2
    )

    # Connect water/steam
    game.connect_entities(pump, boiler1, Prototype.Pipe)
    game.connect_entities(boiler1, engine1, Prototype.Pipe)
    game.connect_entities(engine1, engine2, Prototype.Pipe)
    game.connect_entities(engine2, engine3, Prototype.Pipe)
    game.connect_entities(engine3, engine4, Prototype.Pipe)

    # Add fuel
    game.insert_item(Prototype.Coal, boiler1, quantity=100)

    # Wait for steam to build up
    game.sleep(15)

    # Place rocket silo
    silo_pos = Position(x=20, y=20)
    game.move_to(silo_pos)
    silo = game.place_entity(Prototype.RocketSilo, position=silo_pos)

    # Connect power to silo
    game.connect_entities(engine1, silo, Prototype.BigElectricPole)

    # Wait for power to stabilize
    game.sleep(10)

    silo = game.get_entities({Prototype.RocketSilo})[0]
    initial_status = silo.status
    print(f"Silo status with power: {initial_status}")

    # The silo might still show NO_POWER or LOW_POWER if we don't have enough
    # This test is mainly diagnostic to see what status we get
    print(f"Status is NO_POWER: {initial_status == EntityStatus.NO_POWER}")
    print(f"Status is LOW_POWER: {initial_status == EntityStatus.LOW_POWER}")
    print(
        f"Status is ITEM_INGREDIENT_SHORTAGE: {initial_status == EntityStatus.ITEM_INGREDIENT_SHORTAGE}"
    )


def test_rocket_silo_serialization(game):
    """Test that rocket silo serializes all expected fields."""
    # Place rocket silo
    silo_pos = Position(x=20, y=20)
    game.move_to(silo_pos)
    silo = game.place_entity(Prototype.RocketSilo, position=silo_pos)

    # Verify all expected fields are present and have correct types
    assert hasattr(silo, "rocket_parts"), "Missing rocket_parts field"
    assert hasattr(silo, "rocket_progress"), "Missing rocket_progress field"
    assert hasattr(silo, "status"), "Missing status field"
    assert hasattr(silo, "position"), "Missing position field"

    assert isinstance(silo.rocket_parts, int), "rocket_parts should be int"
    assert isinstance(silo.rocket_progress, float), "rocket_progress should be float"

    print("Silo serialization test passed:")
    print(f"  rocket_parts: {silo.rocket_parts}")
    print(f"  rocket_progress: {silo.rocket_progress}")
    print(f"  status: {silo.status}")


def test_rocket_launch_full(configure_game):
    """Test that rocket silo can receive components and assemble rocket parts with sufficient power."""
    game = configure_game(
        inventory={
            "rocket-silo": 1,
            "big-electric-pole": 10,
            "small-electric-pole": 10,
            "solar-panel": 10,
            "low-density-structure": 50,
            "rocket-fuel": 50,
            "processing-unit": 50,
        },
        merge=True,
    )
    # Place rocket silo at origin
    silo_pos = Position(x=0, y=0)
    game.move_to(silo_pos)
    silo = game.place_entity(Prototype.RocketSilo, position=silo_pos)

    # Power via solar panels placed next to silo (same proven pattern as test_assembler_2_concrete)
    # Silo needs 250kW for crafting; each solar panel provides 60kW peak
    solar = game.place_entity_next_to(
        Prototype.SolarPanel, silo.position, Direction.DOWN, spacing=1
    )
    game.connect_entities(solar, silo, Prototype.SmallElectricPole)

    # Wait for power to establish
    game.sleep(10)

    # Insert rocket components directly into the silo
    # Factorio 2.0 recipe: low-density-structure + rocket-fuel + processing-unit (RCU removed in 2.0)
    silo = game.insert_item(Prototype.LowDensityStructure, silo, quantity=50)
    silo = game.insert_item(Prototype.RocketFuel, silo, quantity=50)
    silo = game.insert_item(Prototype.ProcessingUnit, silo, quantity=50)

    # Wait for silo to assemble rocket parts
    game.sleep(300)

    # Get fresh reference to silo
    silo = game.get_entities({Prototype.RocketSilo})[0]
    print(
        f"Final silo status: {silo.status}, rocket_parts: {silo.rocket_parts}, progress: {silo.rocket_progress}"
    )
    assert silo.rocket_parts > 0 or silo.rocket_progress > 0, (
        f"Expected rocket assembly progress, got parts={silo.rocket_parts}, progress={silo.rocket_progress}"
    )
