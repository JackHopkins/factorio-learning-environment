import math
from typing import List

import pytest

from factorio_entities import Entity, Position, PipeGroup, EntityStatus, ResourcePatch
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
        'assembling-machine-1': 10,
        'boiler': 3,
        'steam-engine': 3
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_connect_offshore_pump_to_boiler(game):
    #game.craft_item(Prototype.OffshorePump)
    game.move_to(game.nearest(Resource.Water))
    game.move_to(game.nearest(Resource.Wood))
    game.harvest_resource(game.nearest(Resource.Wood), quantity=100)
    game.move_to(game.nearest(Resource.Water))
    offshore_pump = game.place_entity(Prototype.OffshorePump,
                                      position=game.nearest(Resource.Water))
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                       reference_position=offshore_pump.position,
                                       direction=offshore_pump.direction,
                                       spacing=5)
    water_pipes = game.connect_entities(boiler, offshore_pump, connection_type=Prototype.Pipe)
    assert len(water_pipes[0].pipes) == 5 + boiler.tile_dimensions.tile_width / 2 + offshore_pump.tile_dimensions.tile_width / 2 + 1

    game.move_to(game.nearest(Resource.Water))
    offshore_pump = game.place_entity(Prototype.OffshorePump,
                                      position=game.nearest(Resource.Water),
                                      direction=Direction.RIGHT)
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                       reference_position=offshore_pump.position,
                                       direction=offshore_pump.direction,
                                       spacing=5)
    assert boiler.direction.value == offshore_pump.direction.value
    water_pipes = game.connect_entities(boiler, offshore_pump, connection_type=Prototype.Pipe)
    assert len(water_pipes[0].pipes) >= math.ceil(
        5 + boiler.tile_dimensions.tile_height / 2 + offshore_pump.tile_dimensions.tile_height / 2 + 1)

    game.instance.reset()
    game.move_to(game.nearest(Resource.Water))

    offshore_pump = game.place_entity(Prototype.OffshorePump,
                                      position=game.nearest(Resource.Water),
                                      direction=Direction.DOWN,
                                      exact=False)
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                       reference_position=offshore_pump.position,
                                       direction=offshore_pump.direction,
                                       spacing=5)
    assert boiler.direction.value == offshore_pump.direction.value
    water_pipes = game.connect_entities(boiler, offshore_pump, connection_type=Prototype.Pipe)
    assert len(water_pipes[0].pipes) >= math.ceil(
        5 + boiler.tile_dimensions.tile_height / 2 + offshore_pump.tile_dimensions.tile_height / 2 + 1)

    game.move_to(Position(x=-30, y=0))
    offshore_pump = game.place_entity(Prototype.OffshorePump,
                                      position=game.nearest(Resource.Water),
                                      direction=Direction.LEFT)
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                       reference_position=offshore_pump.position,
                                       direction=offshore_pump.direction,
                                       spacing=5)
    assert boiler.direction.value == offshore_pump.direction.value
    water_pipes = game.connect_entities(boiler, offshore_pump, connection_type=Prototype.Pipe)
    assert len(water_pipes[0].pipes) >= math.ceil(
        5 + boiler.tile_dimensions.tile_width / 2 + offshore_pump.tile_dimensions.tile_width / 2 + 1)


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
    boiler: Entity = game.place_entity(Prototype.Boiler, position=Position(x=0, y=0), direction=Direction.UP)
    assert boiler.direction.value == Direction.UP.value
    game.move_to(Position(x=0, y=10))
    steam_engine: Entity = game.place_entity(Prototype.SteamEngine, position=Position(x=0, y=10),
                                             direction=Direction.UP)
    assert steam_engine.direction.value == Direction.UP.value

    connection: List[PipeGroup] = game.connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)
    # check to see if the steam engine has water
    #inspection = game.inspect_entities(position=steam_engine.position)

    #assert inspection.get_entity(Prototype.SteamEngine).warning == 'not receiving electricity'
    assert boilers_in_inventory - 1 == game.inspect_inventory()[Prototype.Boiler]
    assert steam_engines_in_inventory - 1 == game.inspect_inventory()[Prototype.SteamEngine]
    assert pipes_in_inventory - len(connection[0].pipes) == game.inspect_inventory()[Prototype.Pipe]
    assert len(connection[0].pipes) >= 10

    game.instance.reset()

    # Define the offsets for the four cardinal directions
    offsets = [Position(x=10, y=0), Position(x=0, y=-10), Position(x=-10, y=0)]  # Up, Right, Down, Left  (0, -10),
    directions = [Direction.RIGHT, Direction.UP, Direction.LEFT]
    for offset, direction in zip(offsets, directions):
        game.move_to(Position(x=0, y=0))
        boiler: Entity = game.place_entity(Prototype.Boiler, position=Position(x=0, y=0), direction=direction)

        game.move_to(offset)
        steam_engine: Entity = game.place_entity(Prototype.SteamEngine, position=offset, direction=direction)

        try:
            connection: List[PipeGroup] = game.connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)
        except Exception as e:
            print(e)
            assert False
        assert boilers_in_inventory - 1 == game.inspect_inventory()[Prototype.Boiler]
        assert steam_engines_in_inventory - 1 == game.inspect_inventory()[Prototype.SteamEngine]

        current_pipes_in_inventory = game.inspect_inventory()[Prototype.Pipe]
        spent_pipes = (pipes_in_inventory - current_pipes_in_inventory)
        assert spent_pipes == len(connection[0].pipes)

        # check to see if the steam engine has water
        entities = game.get_entities(position=steam_engine.position)
        #assert inspection.get_entity(Prototype.SteamEngine).warning == 'not receiving electricity'

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
    offshore_pump = game.place_entity(Prototype.OffshorePump,
                                      position=game.nearest(Resource.Water),
                                      direction=Direction.LEFT)

    # place the boiler next to the offshore pump
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                       reference_position=offshore_pump.position,
                                       direction=offshore_pump.direction,
                                       spacing=2)

    # place the steam engine next to the boiler
    steam_engine = game.place_entity_next_to(Prototype.SteamEngine,
                                             reference_position=boiler.position,
                                             direction=boiler.direction,
                                             spacing=2)

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
    boiler = game.place_entity(Prototype.Boiler, position=boiler_pos, direction=Direction.RIGHT)

    # Step 5: Place and set up the steam engine
    steam_engine_pos = Position(x=boiler.position.x + 5, y=boiler.position.y + 5)
    game.move_to(steam_engine_pos)
    steam_engine = game.place_entity(Prototype.SteamEngine, position=steam_engine_pos, direction=Direction.RIGHT)

    # Connect boiler to steam engine with pipes
    pipes = game.connect_entities(boiler, steam_engine, Prototype.Pipe)
    assert pipes, "Failed to connect boiler to steam engine with pipes"


def test_connect_boiler_to_steam_engine_with_pipes_vertically(game):
    boiler_pos = Position(x=0, y=0)
    game.move_to(boiler_pos)
    boiler = game.place_entity(Prototype.Boiler, position=boiler_pos, direction=Direction.UP)

    # Step 5: Place and set up the steam engine
    steam_engine_pos = Position(x=boiler.position.x + 5, y=boiler.position.y + 5)
    game.move_to(steam_engine_pos)
    steam_engine = game.place_entity(Prototype.SteamEngine, position=steam_engine_pos, direction=Direction.UP)

    # Connect boiler to steam engine with pipes
    pipes = game.connect_entities(boiler, steam_engine, Prototype.Pipe)
    assert pipes, "Failed to connect boiler to steam engine with pipes"

# def test_connect_pipe_groups_horizontally(game):
#
#     # Create a horizontal pipe group
#     pipe_group_right = game.connect_entities(Position(x=0, y=0), Position(x=5, y=0), Prototype.Pipe)
#
#     # Loop the pipes back around
#     pipe_group_right = game.connect_entities(pipe_group_right[0], pipe_group_right[0], Prototype.Pipe)
#
#     # This should result in a single contiguous group
#     assert len(pipe_group_right) == 1
#
#     pipe_group_left = game.connect_entities(Position(x=0, y=-10), Position(x=-5, y=-10), Prototype.Pipe)
#
#     # Loop the pipes back around
#     pipe_group_left = game.connect_entities(pipe_group_left[0], pipe_group_left[0], Prototype.Pipe)
#
#     # This should result in a single contiguous group
#     assert len(pipe_group_left) == 1

def test_avoid_self_collision(game):

    # Step 2: Move to the target location and find water
    target_position = Position(x=5, y=-4)
    game.move_to(target_position)
    print(f"Moved to target position: {target_position}")

    water_source = game.nearest(Resource.Water)
    print(f"Nearest water source found at: {water_source}")

    # Step 3: Place offshore pump
    game.move_to(water_source)
    offshore_pump = game.place_entity(Prototype.OffshorePump, position=water_source, direction=Direction.SOUTH)
    print(f"Placed offshore pump at: {offshore_pump.position}")

    # Step 4: Place boiler
    boiler_pos = Position(x=offshore_pump.position.x + 2, y=offshore_pump.position.y + 2)
    game.move_to(boiler_pos)
    boiler = game.place_entity(Prototype.Boiler, position=boiler_pos, direction=Direction.RIGHT)
    print(f"Placed boiler at: {boiler.position}")

    # Connect offshore pump to boiler with pipes
    pipes = game.connect_entities(offshore_pump, boiler, Prototype.Pipe)
    assert len(pipes) == 1, "Failed to construct a single contiguous pipe group"
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

    assert boiler.connection_points[0] in [p.position for p in pump_to_boiler_pipes[0].pipes]

def test_connect_ragged_edges(game):
    water: ResourcePatch = game.get_resource_patch(Resource.Water, game.nearest(Resource.Water))

    start_pos = water.bounding_box.left_top
    end_pos = water.bounding_box.right_bottom

    # Move to the start position and place an offshore pump
    game.move_to(start_pos)

    pipes = game.connect_entities(start_pos, end_pos, Prototype.Pipe)

    assert len(pipes) == 1

def test_connect_pipes_by_positions(game):
    """
    This should ensure that pipe groups are always returned - instead of pipes themselves.
    """
    position_1 = Position(x=0, y=1)
    position_2 = Position(x=2, y=4)
    belts = game.connect_entities(position_1, position_2, Prototype.Pipe)
    print(game.get_entities())


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
    assert len(pipes1) == 1
    assert len(pipes2) == 1
    assert pipes1[0].id != pipes2[0].id

def test_connect_pipes_through_trees(game):
    instance = game.instance

    for y in range(-10, 10):
        instance.add_command('/c game.surfaces[1].create_entity({name = "tree-01", position = {x = 1, y = ' + str(y) + '}})', raw=True)
    instance.execute_transaction()

    start = Position(x=0, y=0)
    end = Position(x=10, y=0)

    # Connect pipes - should route around the boiler
    pipes = game.connect_entities(start, end, Prototype.Pipe)

    assert len(pipes[0].pipes) == 11


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
    assert len(pipes) == 1
    assert len(pipes[0].pipes) > 10  # Should be longer due to routing



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
    assert len(branch) == 1
    assert branch[0].id == main_line[0].id
