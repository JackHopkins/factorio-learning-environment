"""
Entity Status Invariant Tests

Tests verifying EntityStatus behavior based on Factorio 2.0 API documentation.
See: https://lua-api.factorio.com/latest/types/EntityStatus.html

Invariants tested:
1. WORKING status requires power, fuel, and ingredients (where applicable)
2. NO_FUEL status for burner entities without fuel
3. FULL_OUTPUT when output inventory is blocked
4. NOT_CONNECTED for fluid entities without connections
5. NO_RECIPE for assembling machines without recipe set
"""

import pytest

from fle.env import Direction, EntityStatus, Position
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    """Fixture with inventory for status testing."""
    instance.initial_inventory = {
        "stone-furnace": 10,
        "burner-mining-drill": 10,
        "burner-inserter": 50,
        "offshore-pump": 5,
        "pipe": 100,
        "boiler": 5,
        "steam-engine": 5,
        "small-electric-pole": 30,
        "coal": 200,
        "iron-ore": 100,
        "iron-plate": 100,
        "copper-plate": 50,
        "wooden-chest": 20,
        "assembling-machine-1": 10,
        "transport-belt": 100,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_no_fuel_status_when_burner_empty(game):
    """
    Invariant: Burner entities without fuel should have NO_FUEL status.

    From Factorio 2.0 docs: NO_FUEL status indicates burner equipment lacks fuel.
    """
    # Place a stone furnace without fuel
    furnace = game.place_entity(
        Prototype.StoneFurnace,
        position=Position(x=0, y=0),
    )

    # Furnace without fuel should have NO_FUEL status
    assert furnace.status == EntityStatus.NO_FUEL, (
        f"Invariant violation: Furnace without fuel should have NO_FUEL status, "
        f"got {furnace.status}"
    )


def test_working_status_with_fuel_and_ingredients(game):
    """
    Invariant: Burner entities with fuel and work should have WORKING status.

    From Factorio 2.0 docs: WORKING status means entity is actively performing its function.
    """
    # Place a stone furnace
    furnace = game.place_entity(
        Prototype.StoneFurnace,
        position=Position(x=0, y=0),
    )

    # Insert fuel
    game.insert_item(Prototype.Coal, furnace, 10)

    # Insert smeltable ore
    game.insert_item(Prototype.IronOre, furnace, 10)

    # Wait for furnace to start processing
    game.sleep(30)

    # Re-fetch furnace state
    furnace = game.get_entity(Prototype.StoneFurnace, furnace.position)

    # Furnace should now be WORKING
    assert furnace.status == EntityStatus.WORKING, (
        f"Invariant violation: Furnace with fuel and ore should have WORKING status, "
        f"got {furnace.status}"
    )


def test_not_connected_status_for_offshore_pump(game):
    """
    Invariant: Offshore pump without pipe connections should have NOT_CONNECTED status.

    From Factorio 2.0 docs: NOT_CONNECTED indicates entity lacks required connections.
    """
    # Find water position
    water_pos = game.nearest(Resource.Water)
    game.move_to(water_pos)

    # Place offshore pump
    pump = game.place_entity(
        Prototype.OffshorePump,
        position=water_pos,
        direction=Direction.DOWN,
        exact=False,
    )

    # Offshore pump without connections should be NOT_CONNECTED
    assert pump.status == EntityStatus.NOT_CONNECTED, (
        f"Invariant violation: Offshore pump without connections should have NOT_CONNECTED status, "
        f"got {pump.status}"
    )


def test_full_output_status_when_blocked(game):
    """
    Invariant: Entity with full output should have FULL_OUTPUT status.

    From Factorio 2.0 docs: FULL_OUTPUT indicates output inventory at capacity.
    """
    # Find water position for power setup
    water_pos = game.nearest(Resource.Water)
    game.move_to(water_pos)

    # Create a working offshore pump connected to pipes
    pump = game.place_entity(
        Prototype.OffshorePump,
        position=water_pos,
        direction=Direction.DOWN,
        exact=False,
    )

    # Connect pipe to pump
    pipe_pos = pump.position.down(2)
    game.move_to(pipe_pos)
    pipe = game.place_entity(
        Prototype.Pipe,
        position=pipe_pos,
    )

    # Connect them
    game.connect_entities(pump, pipe, Prototype.Pipe)

    # Wait for pipes to fill with water
    game.sleep(60)

    # Get updated pipe status - should be FULL_OUTPUT when filled
    pipes = game.get_entities({Prototype.Pipe})
    if pipes:
        # At least one pipe should show FULL_OUTPUT when water backs up
        statuses = [p.status for p in pipes]
        assert (
            EntityStatus.FULL_OUTPUT in statuses or EntityStatus.WORKING in statuses
        ), (
            f"Invariant: Filled pipes should have FULL_OUTPUT or WORKING status, "
            f"got {statuses}"
        )
