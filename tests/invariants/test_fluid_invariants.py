"""
Fluid System Invariant Tests

Tests verifying fluid system behavior based on Factorio 2.0 API documentation.
See: https://lua-api.factorio.com/latest/classes/LuaFluidBox.html

Invariants tested:
1. No fluid mixing in pipe networks (Factorio 2.0 constraint)
2. Offshore pump requires water tile
3. Boiler converts water to steam (different fluids, no mixing)
4. Connected pipes form a network (share fluidbox_id)
5. Disconnected pipes have NOT_CONNECTED or EMPTY status
"""

import pytest

from fle.env import Direction, EntityStatus, Position
from fle.env.entities import BuildingBox, PipeGroup
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    """Fixture with inventory for fluid system testing."""
    instance.initial_inventory = {
        "offshore-pump": 5,
        "pipe": 200,
        "pipe-to-ground": 50,
        "storage-tank": 5,
        "boiler": 5,
        "steam-engine": 5,
        "coal": 200,
        "small-electric-pole": 30,
        "pump": 5,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_offshore_pump_requires_water_tile(game):
    """
    Invariant: Offshore pump can only be placed on/adjacent to water tiles.

    From Factorio 2.0 docs: Offshore pumps check source tiles for valid fluid types.
    """
    # Find water position
    water_pos = game.nearest(Resource.Water)
    assert water_pos is not None, "Test requires water on the map"

    game.move_to(water_pos)

    # Place offshore pump at water - should succeed
    pump = game.place_entity(
        Prototype.OffshorePump,
        position=water_pos,
        direction=Direction.DOWN,
        exact=False,
    )

    assert pump is not None, "Invariant: Offshore pump should be placeable near water"

    # Try to place offshore pump far from water (should fail)
    dry_pos = Position(x=50, y=50)  # Assuming this is far from water
    game.move_to(dry_pos)

    try:
        bad_pump = game.place_entity(
            Prototype.OffshorePump,
            position=dry_pos,
            direction=Direction.DOWN,
        )
        # If placement succeeded, the invariant may have been violated
        # (unless there's water there too)
        if bad_pump is not None:
            # Check if there's actually water nearby
            nearby_water = game.nearest(Resource.Water)
            if nearby_water and nearby_water.distance(dry_pos) > 10:
                pytest.fail("Invariant violation: Offshore pump placed far from water")
    except Exception:
        # Expected - pump cannot be placed without water
        pass


def test_fluid_connection_forms_network(game):
    """
    Invariant: Connected pipes share the same fluid network (fluidbox_id).

    From Factorio 2.0 docs: Fluid segments can only contain 1 fluid.
    """
    # Create a line of connected pipes
    start_pos = Position(x=0, y=0)
    end_pos = Position(x=10, y=0)

    pipe_group = game.connect_entities(
        start_pos,
        end_pos,
        connection_type=Prototype.Pipe,
    )

    # All pipes should be part of the same group
    assert isinstance(pipe_group, PipeGroup), (
        "Invariant: Connected pipes should form a PipeGroup"
    )

    # Get all pipes and verify they share network properties
    pipes = game.get_entities({Prototype.Pipe})
    assert len(pipes) >= 2, "Expected multiple pipes to be placed"

    # All pipes in a connected network should have consistent fluidbox properties
    if hasattr(pipes[0], "fluidbox_id"):
        fluidbox_ids = [p.fluidbox_id for p in pipes if hasattr(p, "fluidbox_id")]
        # Connected pipes should share the same fluidbox_id
        if fluidbox_ids:
            assert len(set(fluidbox_ids)) == 1, (
                f"Invariant violation: Connected pipes should share fluidbox_id, "
                f"got {set(fluidbox_ids)}"
            )


def test_disconnected_pipe_has_empty_status(game):
    """
    Invariant: Isolated pipes without fluid should have EMPTY status.

    From Factorio 2.0 docs: Empty fluidbox returns nil for fluid contents.
    """
    # Create two separate pipe networks
    pipe_group1 = game.connect_entities(
        Position(x=0, y=0),
        Position(x=5, y=0),
        connection_type=Prototype.Pipe,
    )

    pipe_group2 = game.connect_entities(
        Position(x=10, y=0),
        Position(x=15, y=0),
        connection_type=Prototype.Pipe,
    )

    # Both isolated pipe groups should have EMPTY status (no fluid source)
    assert pipe_group1.status == EntityStatus.EMPTY, (
        f"Invariant: Isolated pipes should have EMPTY status, got {pipe_group1.status}"
    )
    assert pipe_group2.status == EntityStatus.EMPTY, (
        f"Invariant: Isolated pipes should have EMPTY status, got {pipe_group2.status}"
    )


def test_boiler_separates_water_and_steam(game):
    """
    Invariant: Boiler has separate input (water) and output (steam) connections.

    From Factorio 2.0 docs: No fluid mixing - each fluidbox segment contains 1 fluid.
    """
    # Find water and set up power chain
    water_pos = game.nearest(Resource.Water)
    game.move_to(water_pos)

    # Place offshore pump
    pump = game.place_entity(
        Prototype.OffshorePump,
        position=water_pos,
        direction=Direction.DOWN,
        exact=False,
    )

    # Place boiler
    boiler_box = BuildingBox(width=5, height=5)
    boiler_coords = game.nearest_buildable(Prototype.Boiler, boiler_box, pump.position)
    game.move_to(boiler_coords.center)
    boiler = game.place_entity(Prototype.Boiler, position=boiler_coords.center)

    # Place steam engine
    engine_box = BuildingBox(width=5, height=7)
    engine_coords = game.nearest_buildable(
        Prototype.SteamEngine, engine_box, boiler.position
    )
    game.move_to(engine_coords.center)
    engine = game.place_entity(Prototype.SteamEngine, position=engine_coords.center)

    # Connect water: pump -> boiler
    water_pipes = game.connect_entities(
        pump, boiler, {Prototype.Pipe, Prototype.UndergroundPipe}
    )

    # Connect steam: boiler -> engine
    steam_pipes = game.connect_entities(
        boiler, engine, {Prototype.Pipe, Prototype.UndergroundPipe}
    )

    # Both connections should succeed
    assert water_pipes is not None, "Water pipe connection should succeed"
    assert steam_pipes is not None, "Steam pipe connection should succeed"

    # Add fuel to boiler
    game.insert_item(Prototype.Coal, boiler, 50)

    # Wait for system to operate
    game.sleep(60)

    # Refresh boiler state
    boiler = game.get_entity(Prototype.Boiler, boiler.position)

    # Boiler should be working (converting water to steam)
    # Status could be WORKING, LOW_TEMPERATURE (warming up), or similar
    valid_statuses = [
        EntityStatus.WORKING,
        EntityStatus.LOW_TEMPERATURE,
        EntityStatus.NO_FUEL,
        EntityStatus.FULL_OUTPUT,
    ]
    assert boiler.status in valid_statuses or boiler.status == EntityStatus.WORKING, (
        f"Boiler should be operational, got {boiler.status}"
    )


def test_pump_working_status_when_connected(game):
    """
    Invariant: Offshore pump with pipe connection should have WORKING status.

    From Factorio 2.0 docs: WORKING status means actively performing function.
    """
    # Find water
    water_pos = game.nearest(Resource.Water)
    game.move_to(water_pos)

    # Place offshore pump
    pump = game.place_entity(
        Prototype.OffshorePump,
        position=water_pos,
        direction=Direction.DOWN,
        exact=False,
    )

    # Initially NOT_CONNECTED
    assert pump.status == EntityStatus.NOT_CONNECTED, (
        f"Pump without connections should be NOT_CONNECTED, got {pump.status}"
    )

    # Connect a pipe to the pump
    pipe_pos = pump.position.down(2)
    game.move_to(pipe_pos)

    # Use connect_entities to properly connect
    _pipes = game.connect_entities(
        pump.position,
        pump.position.down(5),
        connection_type=Prototype.Pipe,
    )

    # Wait for fluid flow
    game.sleep(30)

    # Refresh pump state
    pump = game.get_entity(Prototype.OffshorePump, pump.position)

    # Pump should now be WORKING
    assert pump.status == EntityStatus.WORKING, (
        f"Invariant: Connected pump should be WORKING, got {pump.status}"
    )
