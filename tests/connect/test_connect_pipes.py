import math

import pytest

from fle.env.entities import (
    BuildingBox,
    Direction,
    Entity,
    EntityStatus,
    Generator,
    PipeGroup,
    Position,
    ResourcePatch,
)
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        "stone-furnace": 10,
        "burner-inserter": 50,
        "offshore-pump": 4,
        "pipe": 100,
        "small-electric-pole": 50,
        "pipe-to-ground": 10,
        "transport-belt": 200,
        "coal": 100,
        "wooden-chest": 1,
        "assembling-machine-1": 10,
        "assembling-machine-2": 10,
        "assembling-machine-3": 10,
        "storage-tank": 3,
        "boiler": 3,
        "steam-engine": 3,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_connect_electricity_bug(game):
    # First find water
    water_pos = game.nearest(Resource.Water)
    print(f"Found water at {water_pos}")

    # Place offshore pump
    game.move_to(water_pos)
    offshore_pump = game.place_entity(Prototype.OffshorePump, position=water_pos)
    print(f"Placed offshore pump at {offshore_pump.position}")

    # Place storage tank for water buffer
    # Need to find safe spot away from water
    building_box = BuildingBox(
        width=Prototype.StorageTank.WIDTH + 4, height=Prototype.StorageTank.HEIGHT + 4
    )
    coords = game.nearest_buildable(
        Prototype.StorageTank, building_box, offshore_pump.position
    )
    game.move_to(coords.center)
    water_tank = game.place_entity(Prototype.StorageTank, position=coords.center)
    print(f"Placed water storage tank at {water_tank.position}")

    # Connect pump to tank with pipes
    game.connect_entities(
        offshore_pump, water_tank, {Prototype.Pipe, Prototype.UndergroundPipe}
    )
    print("Connected offshore pump to storage tank with pipes")

    print("Setting up power system...")
    # Place boiler near water tank
    building_box = BuildingBox(
        width=Prototype.Boiler.WIDTH + 4, height=Prototype.Boiler.HEIGHT + 4
    )
    coords = game.nearest_buildable(Prototype.Boiler, building_box, water_tank.position)
    game.move_to(coords.center)
    boiler = game.place_entity(Prototype.Boiler, position=coords.center)
    print(f"Placed boiler at {boiler.position}")

    # Add steam engine
    building_box = BuildingBox(
        width=Prototype.SteamEngine.WIDTH + 4, height=Prototype.SteamEngine.HEIGHT + 4
    )
    coords = game.nearest_buildable(
        Prototype.SteamEngine, building_box, boiler.position
    )
    game.move_to(coords.center)
    steam_engine = game.place_entity(Prototype.SteamEngine, position=coords.center)
    print(f"Placed steam engine at {steam_engine.position}")

    # Connect water and steam
    game.connect_entities(
        water_tank, boiler, {Prototype.Pipe, Prototype.UndergroundPipe}
    )
    game.connect_entities(
        boiler, steam_engine, {Prototype.Pipe, Prototype.UndergroundPipe}
    )
    print("Connected water and steam pipes")


def test_connect_offshore_pump_to_boiler(game):
    # game.craft_item(Prototype.OffshorePump)
    game.move_to(game.nearest(Resource.Water))
    game.move_to(game.nearest(Resource.Wood))
    game.harvest_resource(game.nearest(Resource.Wood), quantity=100)
    game.move_to(game.nearest(Resource.Water))
    offshore_pump = game.place_entity(
        Prototype.OffshorePump, position=game.nearest(Resource.Water)
    )
    boiler = game.place_entity_next_to(
        Prototype.Boiler,
        reference_position=offshore_pump.position,
        direction=offshore_pump.direction,
        spacing=5,
    )
    water_pipes = game.connect_entities(
        boiler, offshore_pump, connection_type=Prototype.Pipe
    )
    assert (
        len(water_pipes.pipes)
        == 5
        + boiler.tile_dimensions.tile_width / 2
        + offshore_pump.tile_dimensions.tile_width / 2
        + 1
    )

    game.instance.reset()
    game.move_to(game.nearest(Resource.Water))
    offshore_pump = game.place_entity(
        Prototype.OffshorePump,
        position=game.nearest(Resource.Water),
        direction=Direction.RIGHT,
    )
    boiler = game.place_entity_next_to(
        Prototype.Boiler,
        reference_position=offshore_pump.position,
        direction=offshore_pump.direction,
        spacing=5,
    )
    assert boiler.direction.value == offshore_pump.direction.value
    water_pipes = game.connect_entities(
        boiler, offshore_pump, connection_type=Prototype.Pipe
    )
    assert len(water_pipes.pipes) >= math.ceil(
        5
        + boiler.tile_dimensions.tile_height / 2
        + offshore_pump.tile_dimensions.tile_height / 2
        + 1
    )

    game.instance.reset()
    game.move_to(game.nearest(Resource.Water))

    offshore_pump = game.place_entity(
        Prototype.OffshorePump,
        position=game.nearest(Resource.Water),
        direction=Direction.DOWN,
        exact=False,
    )
    boiler = game.place_entity_next_to(
        Prototype.Boiler,
        reference_position=offshore_pump.position,
        direction=offshore_pump.direction,
        spacing=5,
    )
    assert boiler.direction.value == offshore_pump.direction.value
    water_pipes = game.connect_entities(
        boiler, offshore_pump, connection_type=Prototype.Pipe
    )
    assert len(water_pipes.pipes) >= math.ceil(
        5
        + boiler.tile_dimensions.tile_height / 2
        + offshore_pump.tile_dimensions.tile_height / 2
        + 1
    )

    game.move_to(Position(x=-30, y=0))
    offshore_pump = game.place_entity(
        Prototype.OffshorePump,
        position=game.nearest(Resource.Water),
        direction=Direction.LEFT,
    )
    boiler = game.place_entity_next_to(
        Prototype.Boiler,
        reference_position=offshore_pump.position,
        direction=offshore_pump.direction,
        spacing=5,
    )
    assert boiler.direction.value == offshore_pump.direction.value
    water_pipes = game.connect_entities(
        boiler, offshore_pump, connection_type=Prototype.Pipe
    )
    assert len(water_pipes.pipes) >= math.ceil(
        5
        + boiler.tile_dimensions.tile_width / 2
        + offshore_pump.tile_dimensions.tile_width / 2
        + 1
    )


def test_connect_steam_engines_to_boilers_using_pipes(game):
    """
    Place a boiler and a steam engine next to each other in 3 cardinal directions.
    :param game:
    :return:
    """
    boilers_in_inventory = game.inspect_inventory()[Prototype.Boiler]
    steam_engines_in_inventory = game.inspect_inventory()[Prototype.SteamEngine]
    pipes_in_inventory = game.inspect_inventory()[Prototype.Pipe]

    game.move_to(Position(x=0, y=0))
    boiler: Entity = game.place_entity(
        Prototype.Boiler, position=Position(x=0, y=0), direction=Direction.UP
    )
    assert boiler.direction.value == Direction.UP.value
    game.move_to(Position(x=0, y=10))
    steam_engine: Entity = game.place_entity(
        Prototype.SteamEngine, position=Position(x=0, y=10), direction=Direction.UP
    )
    assert steam_engine.direction.value == Direction.UP.value

    connection: PipeGroup = game.connect_entities(
        boiler, steam_engine, connection_type=Prototype.Pipe
    )
    # check to see if the steam engine has water
    # inspection = game.inspect_entities(position=steam_engine.position)

    # assert inspection.get_entity(Prototype.SteamEngine).warning == 'not receiving electricity'
    assert boilers_in_inventory - 1 == game.inspect_inventory()[Prototype.Boiler]
    assert (
        steam_engines_in_inventory - 1
        == game.inspect_inventory()[Prototype.SteamEngine]
    )
    assert (
        pipes_in_inventory - len(connection.pipes)
        == game.inspect_inventory()[Prototype.Pipe]
    )
    assert len(connection.pipes) >= 10

    game.instance.reset()

    # Define the offsets for the four cardinal directions
    offsets = [
        Position(x=5, y=0),
        Position(x=0, y=-5),
        Position(x=-5, y=0),
    ]  # Up, Right, Down, Left  (0, -10),
    directions = [Direction.RIGHT, Direction.UP, Direction.LEFT]
    for offset, direction in zip(offsets, directions):
        game.move_to(Position(x=0, y=0))
        boiler: Entity = game.place_entity(
            Prototype.Boiler, position=Position(x=0, y=0), direction=direction
        )

        game.move_to(offset)
        steam_engine: Entity = game.place_entity(
            Prototype.SteamEngine, position=offset, direction=direction
        )

        try:
            connection: PipeGroup = game.connect_entities(
                boiler, steam_engine, connection_type=Prototype.Pipe
            )
        except Exception as e:
            print(e)
            assert False
        assert boilers_in_inventory - 1 == game.inspect_inventory()[Prototype.Boiler]
        assert (
            steam_engines_in_inventory - 1
            == game.inspect_inventory()[Prototype.SteamEngine]
        )

        current_pipes_in_inventory = game.inspect_inventory()[Prototype.Pipe]
        spent_pipes = pipes_in_inventory - current_pipes_in_inventory
        assert spent_pipes == len(connection.pipes)

        # check to see if the steam engine has water
        game.get_entities(position=steam_engine.position)
        # assert inspection.get_entity(Prototype.SteamEngine).warning == 'not receiving electricity'

        game.instance.reset()  # Reset the game state after each iteration


def test_connect_steam_engine_boiler_nearly_adjacent(game):
    """
    We've had problems with gaps of exactly 2.
    :param game:
    :return:
    """
    # place the offshore pump at nearest water source
    game.move_to(Position(x=-30, y=12))
    game.move_to(game.nearest(Resource.Water))
    offshore_pump = game.place_entity(
        Prototype.OffshorePump,
        position=game.nearest(Resource.Water),
        direction=Direction.LEFT,
    )

    # place the boiler next to the offshore pump
    boiler = game.place_entity_next_to(
        Prototype.Boiler,
        reference_position=offshore_pump.position,
        direction=offshore_pump.direction,
        spacing=2,
    )

    # place the steam engine next to the boiler
    steam_engine = game.place_entity_next_to(
        Prototype.SteamEngine,
        reference_position=boiler.position,
        direction=boiler.direction,
        spacing=2,
    )

    # place connective pipes between the boiler and steam engine
    game.connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)

    game.connect_entities(offshore_pump, boiler, connection_type=Prototype.Pipe)

    # insert coal into boiler
    game.insert_item(Prototype.Coal, boiler, 50)

    # check to see if the steam engine has water
    engine = game.get_entity(Prototype.SteamEngine, steam_engine.position)

    assert engine.status == EntityStatus.NOT_PLUGGED_IN_ELECTRIC_NETWORK


def test_connect_boiler_to_steam_engine_with_pipes_horizontally(game):
    boiler_pos = Position(x=0, y=0)
    game.move_to(boiler_pos)
    boiler = game.place_entity(
        Prototype.Boiler, position=boiler_pos, direction=Direction.RIGHT
    )

    # Step 5: Place and set up the steam engine
    steam_engine_pos = Position(x=boiler.position.x + 5, y=boiler.position.y + 5)
    game.move_to(steam_engine_pos)
    steam_engine = game.place_entity(
        Prototype.SteamEngine, position=steam_engine_pos, direction=Direction.RIGHT
    )

    # Connect boiler to steam engine with pipes
    pipes = game.connect_entities(boiler, steam_engine, Prototype.Pipe)
    assert pipes, "Failed to connect boiler to steam engine with pipes"


def test_connect_boiler_to_steam_engine_with_pipes_vertically(game):
    boiler_pos = Position(x=0, y=0)
    game.move_to(boiler_pos)
    boiler = game.place_entity(
        Prototype.Boiler, position=boiler_pos, direction=Direction.UP
    )

    # Step 5: Place and set up the steam engine
    steam_engine_pos = Position(x=boiler.position.x + 5, y=boiler.position.y + 5)
    game.move_to(steam_engine_pos)
    steam_engine = game.place_entity(
        Prototype.SteamEngine, position=steam_engine_pos, direction=Direction.UP
    )

    # Connect boiler to steam engine with pipes
    pipes = game.connect_entities(boiler, steam_engine, Prototype.Pipe)
    assert pipes, "Failed to connect boiler to steam engine with pipes"


def test_connect_boiler_to_steam_engine_with_pipes_vertically_with_positions(game):
    boiler_pos = Position(x=0, y=0)
    game.move_to(boiler_pos)
    boiler = game.place_entity(
        Prototype.Boiler, position=boiler_pos, direction=Direction.UP
    )

    # Step 5: Place and set up the steam engine
    steam_engine_pos = Position(x=boiler.position.x + 5, y=boiler.position.y + 5)
    game.move_to(steam_engine_pos)
    steam_engine: Generator = game.place_entity(
        Prototype.SteamEngine, position=steam_engine_pos, direction=Direction.UP
    )

    # Connect boiler to steam engine with pipes
    pipes = game.connect_entities(
        boiler.steam_output_point, steam_engine.connection_points[0], Prototype.Pipe
    )
    assert pipes, "Failed to connect boiler to steam engine with pipes"


def test_avoid_self_collision(game):
    # Step 2: Move to the target location and find water
    target_position = Position(x=5, y=-4)
    game.move_to(target_position)
    print(f"Moved to target position: {target_position}")

    water_source = game.nearest(Resource.Water)
    print(f"Nearest water source found at: {water_source}")

    # Step 3: Place offshore pump
    game.move_to(water_source)
    offshore_pump = game.place_entity(
        Prototype.OffshorePump, position=water_source, direction=Direction.SOUTH
    )
    print(f"Placed offshore pump at: {offshore_pump.position}")

    # Step 4: Place boiler
    boiler_pos = Position(
        x=offshore_pump.position.x + 5, y=offshore_pump.position.y - 2
    )
    game.move_to(boiler_pos)
    boiler = game.place_entity(
        Prototype.Boiler, position=boiler_pos, direction=Direction.RIGHT
    )
    print(f"Placed boiler at: {boiler.position}")

    # Connect offshore pump to boiler with pipes
    pipes = game.connect_entities(offshore_pump, boiler, Prototype.Pipe)
    assert pipes, "Failed to connect offshore pump to boiler with pipes"
    print("Successfully connected offshore pump to boiler with pipes")


def test_connect_where_connection_points_are_blocked(game):
    # Move to the water source
    water_source = game.nearest(Resource.Water)
    game.move_to(water_source)
    print(f"Moved to water source at {water_source}")
    # Place the offshore pump
    pump = game.place_entity(Prototype.OffshorePump, Direction.RIGHT, water_source)
    print(f"Placed offshore pump at {pump.position}")
    """
    Step 2: Place the boiler and connect it to the pump
    """
    # Calculate position for the boiler (4 tiles away from the pump)
    boiler_position = Position(x=pump.position.x + 4, y=pump.position.y)

    # Move to the calculated position
    game.move_to(boiler_position)
    print(f"Moved to boiler position at {boiler_position}")

    # Place the boiler
    boiler = game.place_entity(Prototype.Boiler, Direction.UP, boiler_position)
    print(f"Placed boiler at {boiler.position}")

    # Connect the pump to the boiler with pipes
    pump_to_boiler_pipes = game.connect_entities(pump, boiler, Prototype.Pipe)
    assert pump_to_boiler_pipes, "Failed to connect pump to boiler with pipes"
    print("Connected pump to boiler with pipes")

    assert boiler.connection_points[0] in [
        p.position for p in pump_to_boiler_pipes.pipes
    ]


def test_connect_ragged_edges(game):
    water: ResourcePatch = game.get_resource_patch(
        Resource.Water, game.nearest(Resource.Water)
    )

    start_pos = water.bounding_box.left_top
    end_pos = water.bounding_box.right_bottom

    # Move to the start position and place an offshore pump
    game.move_to(start_pos)

    pipes = game.connect_entities(start_pos, end_pos, Prototype.Pipe)

    assert pipes


def test_connect_pipes_by_positions(game):
    """
    This should ensure that pipe groups are always returned - instead of pipes themselves.
    """
    position_1 = Position(x=0, y=1)
    position_2 = Position(x=2, y=4)
    pipes = game.connect_entities(position_1, position_2, Prototype.Pipe)
    assert len(pipes.pipes) == 6


def test_connect_pipes_to_advanced_assembler(game):
    """
    Ensure that advanced assemblers can be connected to.
    """
    position_1 = Position(x=10, y=0)

    assembler_2 = game.place_entity(
        Prototype.AssemblingMachine2, Direction.UP, Position(x=0, y=0)
    )
    pipes = game.connect_entities(position_1, assembler_2, Prototype.Pipe)

    assert len(pipes.pipes) == 13


def test_fail_connect_pipes_with_mixed_connection_types(game):
    """
    This should ensure that pipe groups are always returned - instead of pipes themselves.
    """
    position_1 = Position(x=0, y=1)
    position_2 = Position(x=2, y=4)
    try:
        game.connect_entities(
            position_1, position_2, {Prototype.Pipe, Prototype.UndergroundBelt}
        )
        assert False
    except Exception:
        assert True


def test_avoiding_pipe_networks(game):
    """Test connecting pipes that cross paths"""
    # Create two intersecting pipe lines
    start1 = Position(x=0, y=0)
    end1 = Position(x=10, y=0)
    start2 = Position(x=5, y=-5)
    end2 = Position(x=5, y=5)

    pipes1 = game.connect_entities(start1, end1, Prototype.Pipe)
    pipes2 = game.connect_entities(start2, end2, Prototype.Pipe)

    # Verify both networks exist independently
    assert pipes1
    assert pipes2
    assert pipes1.id != pipes2.id


def test_pipe_around_obstacle(game):
    """Test pipe pathfinding around placed entities"""
    # Place an obstacle
    obstacle_pos = Position(x=5, y=0)
    game.move_to(obstacle_pos)
    game.place_entity(Prototype.Boiler, position=obstacle_pos)

    start = Position(x=0, y=0)
    end = Position(x=10, y=0)

    # Connect pipes - should route around the boiler
    pipes = game.connect_entities(start, end, Prototype.Pipe)
    assert pipes
    assert len(pipes.pipes) > 10  # Should be longer due to routing


def test_pipe_network_branching(game):
    """Test creating T-junctions and branched pipe networks"""
    # Create main pipe line
    start = Position(x=0, y=0)
    end = Position(x=10, y=0)
    main_line = game.connect_entities(start, end, Prototype.Pipe)

    # Add branch from middle
    branch_end = Position(x=5, y=5)
    branch = game.connect_entities(Position(x=5, y=0), branch_end, Prototype.Pipe)

    # Should merge into single network
    assert branch
    assert branch.id == main_line.id


def test_pipe_network_branching_inverted(game):
    """Test creating T-junctions and branched pipe networks"""
    # Create main pipe line
    start = Position(x=0, y=0)
    end = Position(x=10, y=0)
    main_line = game.connect_entities(start, end, Prototype.Pipe)

    # Add branch from middle
    branch_end = Position(x=5, y=5)
    branch = game.connect_entities(branch_end, Position(x=5, y=0), Prototype.Pipe)

    # Should merge into single network
    assert branch
    assert branch.id == main_line.id


def test_connect_power_system_with_nearest_buildable(game):
    water_position = game.nearest(Resource.Water)
    # moveto water positon
    game.move_to(water_position)
    # first place offshore pump on the water system
    offshore_pump = game.place_entity(Prototype.OffshorePump, position=water_position)
    print(f"Placed offshore pump to get water at {offshore_pump.position}")
    # Use nearest_buildable to find a valid position for the boiler
    # The boiler has a dimension of 2x3, so we need to ensure there is enough space
    boiler_building_box = BuildingBox(width=3, height=2)
    boiler_bounding_box = game.nearest_buildable(
        Prototype.Boiler,
        building_box=boiler_building_box,
        center_position=offshore_pump.position,
    )

    # Log the found position for the boiler
    print(f"Found buildable position for boiler: {boiler_bounding_box.center}")

    # Move to the center of the bounding box and place the boiler
    game.move_to(boiler_bounding_box.center)
    boiler = game.place_entity(
        Prototype.Boiler, position=boiler_bounding_box.center.left(1)
    )
    print(f"Placed boiler at {boiler.position}")

    # Connect the offshore pump to the boiler with pipes
    pipes_to_boiler = game.connect_entities(
        offshore_pump.position, boiler.position, Prototype.Pipe
    )
    print(f"Connected offshore pump to boiler with pipes: {pipes_to_boiler}")
    game.sleep(2)
    print(f"Updated entities on the map: {game.get_entities()}")
    pass


def test_connect_steam_engine_battery(game):
    """
    Test setting up a battery of steam engines and boilers in a 2x2 configuration:
    - 2 boilers side by side
    - 2 steam engines connected to each boiler
    - All components properly connected with pipes
    Layout:
    OP - B - SE - SE
       |
    OP - B - SE - SE

    Where: OP = Offshore Pump, B = Boiler, SE = Steam Engine
    """
    # First, find water and set up the first line
    water_pos = game.nearest(Resource.Water)
    game.move_to(water_pos)

    # Place first offshore pump
    offshore_pump1 = game.place_entity(
        Prototype.OffshorePump, position=water_pos, direction=Direction.RIGHT
    )

    # Place first boiler with some spacing for pipes
    boiler1 = game.place_entity_next_to(
        Prototype.Boiler,
        reference_position=offshore_pump1.position,
        direction=Direction.RIGHT,
        spacing=3,
    )

    # Connect first pump to first boiler
    pump1_pipes = game.connect_entities(
        offshore_pump1, boiler1, connection_type=Prototype.Pipe
    )
    assert pump1_pipes, "Failed to connect first pump to first boiler"

    # Place two steam engines after the first boiler
    steam_engine1a = game.place_entity_next_to(
        Prototype.SteamEngine,
        reference_position=boiler1.position,
        direction=Direction.RIGHT,
        spacing=2,
    )

    steam_engine1b = game.place_entity_next_to(
        Prototype.SteamEngine,
        reference_position=steam_engine1a.position,
        direction=Direction.RIGHT,
        spacing=2,
    )

    # Connect first boiler to its steam engines
    boiler1_pipes = game.connect_entities(
        boiler1, steam_engine1a, connection_type=Prototype.Pipe
    )
    assert boiler1_pipes, "Failed to connect first boiler to first steam engine"

    engine1_pipes = game.connect_entities(
        steam_engine1a, steam_engine1b, connection_type=Prototype.Pipe
    )
    assert engine1_pipes, "Failed to connect steam engines in first row"

    # Set up second row
    # Place second offshore pump below first one
    offshore_pump2 = game.place_entity_next_to(
        Prototype.OffshorePump,
        reference_position=offshore_pump1.position,
        direction=Direction.DOWN,
        spacing=3,
    )

    # Place second boiler
    boiler2 = game.place_entity_next_to(
        Prototype.Boiler,
        reference_position=offshore_pump2.position,
        direction=Direction.RIGHT,
        spacing=3,
    )

    # Connect second pump to second boiler
    pump2_pipes = game.connect_entities(
        offshore_pump2, boiler2, connection_type=Prototype.Pipe
    )
    assert pump2_pipes, "Failed to connect second pump to second boiler"

    # Place two more steam engines
    steam_engine2a = game.place_entity_next_to(
        Prototype.SteamEngine,
        reference_position=boiler2.position,
        direction=Direction.RIGHT,
        spacing=2,
    )

    steam_engine2b = game.place_entity_next_to(
        Prototype.SteamEngine,
        reference_position=steam_engine2a.position,
        direction=Direction.RIGHT,
        spacing=2,
    )

    # Connect second boiler to its steam engines
    boiler2_pipes = game.connect_entities(
        boiler2, steam_engine2a, connection_type=Prototype.Pipe
    )
    assert boiler2_pipes, "Failed to connect second boiler to first steam engine"

    engine2_pipes = game.connect_entities(
        steam_engine2a, steam_engine2b, connection_type=Prototype.Pipe
    )
    assert engine2_pipes, "Failed to connect steam engines in second row"

    # Add fuel to boilers
    game.insert_item(Prototype.Coal, boiler1, 50)
    game.insert_item(Prototype.Coal, boiler2, 50)

    # Connect boilers
    boiler_connective_pipes = game.connect_entities(
        boiler1, boiler2, connection_type=Prototype.Pipe
    )
    assert boiler_connective_pipes, "Failed to connect boiler connective pipes"

    # Verify steam engines are properly set up but waiting for power connection
    for engine in [steam_engine1a, steam_engine1b, steam_engine2a, steam_engine2b]:
        engine_status = game.get_entity(Prototype.SteamEngine, engine.position)
        assert engine_status.status in (
            EntityStatus.NOT_PLUGGED_IN_ELECTRIC_NETWORK,
            EntityStatus.NOT_CONNECTED,
        )
