import math
from time import sleep
from typing import List

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
        PrototypeName.AssemblingMachine.value: 10,
    }
    instance.reset()
    yield instance
    instance.reset()

def test_connect_offshore_pump_to_boiler(game):
    #game.craft_item(Prototype.OffshorePump)

    water_patch = game.get_resource_patch(Resource.Water, game.nearest(Resource.Water))
    game.move_to(water_patch.bounding_box.left_top)
    offshore_pump = game.place_entity(Prototype.OffshorePump,
                                      position=game.nearest(Resource.Water))
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                       reference_position=offshore_pump.position,
                                       direction=offshore_pump.direction,
                                       spacing=5)
    water_pipes = game.connect_entities(boiler, offshore_pump, connection_type=Prototype.Pipe)
    assert len(water_pipes) == 5 + boiler.tile_dimensions.tile_width/2 + offshore_pump.tile_dimensions.tile_width/2 + 1

    game.move_to(water_patch.bounding_box.right_bottom)
    offshore_pump = game.place_entity(Prototype.OffshorePump,
                                      position=game.nearest(Resource.Water),
                                      direction=Direction.RIGHT)
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                        reference_position=offshore_pump.position,
                                        direction=offshore_pump.direction,
                                        spacing=5)
    assert boiler.direction.value == Direction.RIGHT.value
    water_pipes = game.connect_entities(boiler, offshore_pump, connection_type=Prototype.Pipe)
    assert len(water_pipes) == math.ceil(5 + boiler.tile_dimensions.tile_height/2 + offshore_pump.tile_dimensions.tile_height/2 + 1)

    offshore_pump = game.place_entity(Prototype.OffshorePump,
                                      position=game.nearest(Resource.Water),
                                      direction=Direction.DOWN)
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                       reference_position=offshore_pump.position,
                                       direction=offshore_pump.direction,
                                       spacing=5)
    assert boiler.direction.value == Direction.DOWN.value
    water_pipes = game.connect_entities(boiler, offshore_pump, connection_type=Prototype.Pipe)
    assert len(water_pipes) == math.ceil(5 + boiler.tile_dimensions.tile_height / 2 + offshore_pump.tile_dimensions.tile_height / 2 + 1)

    game.move_to(Position(x=-30, y=0))
    offshore_pump = game.place_entity(Prototype.OffshorePump,
                                      position=game.nearest(Resource.Water),
                                      direction=Direction.LEFT)
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                       reference_position=offshore_pump.position,
                                       direction=offshore_pump.direction,
                                       spacing=5)
    assert boiler.direction.value == Direction.LEFT.value
    water_pipes = game.connect_entities(boiler, offshore_pump, connection_type=Prototype.Pipe)
    assert len(water_pipes) == math.ceil(
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

    boiler: Entity = game.place_entity(Prototype.Boiler, position=Position(x=0, y=0), direction=Direction.UP)
    assert boiler.direction.value == Direction.UP.value
    game.move_to(Position(x=0, y=10))
    steam_engine: Entity = game.place_entity(Prototype.SteamEngine, position=Position(x=0, y=10), direction=Direction.UP)
    assert steam_engine.direction.value == Direction.UP.value

    connection: List[Entity] = game.connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)
    # check to see if the steam engine has water
    #inspection = game.inspect_entities(position=steam_engine.position)

    #assert inspection.get_entity(Prototype.SteamEngine).warning == 'not receiving electricity'
    assert boilers_in_inventory - 1 == game.inspect_inventory()[Prototype.Boiler]
    assert steam_engines_in_inventory - 1 == game.inspect_inventory()[Prototype.SteamEngine]
    assert pipes_in_inventory - len(connection) == game.inspect_inventory()[Prototype.Pipe]
    assert len(connection) >= 10

    game.reset()

    # Define the offsets for the four cardinal directions
    offsets = [Position(x=10, y=0), Position(x=0, y=-10), Position(x=-10, y=0)]  # Up, Right, Down, Left  (0, -10),
    directions = [Direction.RIGHT, Direction.UP, Direction.LEFT]
    for offset, direction in zip(offsets, directions):
        boiler: Entity = game.place_entity(Prototype.Boiler, position=Position(x=0, y=0),direction=direction)
        game.move_to(offset)

        steam_engine: Entity = game.place_entity(Prototype.SteamEngine, position=offset,direction=direction)

        try:
            connection: List[Entity] = game.connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)
        except Exception as e:
            print(e)
            assert False
        assert boilers_in_inventory - 1 == game.inspect_inventory()[Prototype.Boiler]
        assert steam_engines_in_inventory - 1 == game.inspect_inventory()[Prototype.SteamEngine]

        current_pipes_in_inventory = game.inspect_inventory()[Prototype.Pipe]
        spent_pipes = (pipes_in_inventory - current_pipes_in_inventory)
        assert spent_pipes == len(connection)

        # check to see if the steam engine has water
        inspection = game.inspect_entities(position=steam_engine.position)
        #assert inspection.get_entity(Prototype.SteamEngine).warning == 'not receiving electricity'

        game.reset()  # Reset the game state after each iteration

def test_place_and_connect_entities_in_grid(game):
    """
    Place a grid of furnaces and connect them with burner inserters.
    :param game:
    :return:
    """
    furnaces_in_inventory = game.inspect_inventory()[Prototype.StoneFurnace]
    inserters_in_inventory = game.inspect_inventory()[Prototype.BurnerInserter]
    placed_inserters = []
    grid_size = 3
    furnaces = [[None for _ in range(grid_size)] for _ in range(grid_size)]

    for i in range(grid_size):
        for j in range(grid_size):
            furnaces[i][j] = game.place_entity(Prototype.StoneFurnace, position=Position(x=1+(i*3), y=1+(j*3)))

    # Connect horizontally
    for i in range(grid_size):
        for j in range(grid_size - 1):
            try:
                connection = game.connect_entities(furnaces[i][j], furnaces[i][j + 1],
                                                   connection_type=Prototype.BurnerInserter)
                placed_inserters.append((connection[0], Direction.SOUTH))
            except Exception as e:
                print(e)
                assert False, f"Failed to connect furnaces horizontally at ({i}, {j}) to ({i}, {j + 1})"

    # Connect vertically
    for i in range(grid_size - 1):
        for j in range(grid_size):
            try:
                connection = game.connect_entities(furnaces[i][j], furnaces[i + 1][j],
                                                   connection_type=Prototype.BurnerInserter)
                placed_inserters.append((connection[0], Direction.EAST))
            except Exception as e:
                print(e)
                assert False, f"Failed to connect furnaces vertically at ({i}, {j}) to ({i + 1}, {j})"

    # Assert directions of placed inserters
    for inserter, expected_direction in placed_inserters:
        assert inserter.direction.value == expected_direction.value, f"Inserter at {inserter.position} has direction {inserter.direction}, expected {expected_direction}"

    current_furnaces_in_inventory = game.inspect_inventory()[Prototype.StoneFurnace]
    current_inserters_in_inventory = game.inspect_inventory()[Prototype.BurnerInserter]

    spent_furnaces = (furnaces_in_inventory - current_furnaces_in_inventory)
    spent_inserters = (inserters_in_inventory - current_inserters_in_inventory)

    assert spent_furnaces == grid_size * grid_size
    assert spent_inserters == 2 * grid_size * (grid_size - 1)
    game.reset()

def test_basic_connection_between_furnace_and_miner(game):
    """
    Place a furnace with a burner inserter pointing towards it.
    Find the nearest coal and place a burner mining drill on it.
    Connect the burner mining drill to the inserter using a transport belt.
    :param game:
    :return:
    """

    coal: Position = game.nearest(Resource.Coal)
    furnace_position = Position(x=coal.x, y=coal.y - 10)
    game.move_to(furnace_position)
    furnace = game.place_entity(Prototype.StoneFurnace, position=furnace_position)
    inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                         reference_position=furnace.position,
                                         direction=game.RIGHT,
                                         spacing=0.5)
    inserter = game.rotate_entity(inserter, Direction.LEFT)

    game.move_to(coal)
    miner = game.place_entity(Prototype.BurnerMiningDrill, position=coal)

    belts_in_inventory = game.inspect_inventory()[Prototype.TransportBelt]

    connection = game.connect_entities(miner, inserter, connection_type=Prototype.TransportBelt)

    current_belts_in_inventory = game.inspect_inventory()[Prototype.TransportBelt]
    spent_belts = (belts_in_inventory - current_belts_in_inventory)
    assert spent_belts == len(connection)
    game.reset()

def test_burner_inserter_grid_with_coal_movement(game):
    """
    Create a grid of burner inserters, each passing left and up from the bottom right point.
    Place some coal at the bottom right point and check whether it moves to the top left
    within a reasonable amount of time.
    :param game:
    :return:
    """

    # Define the grid size
    grid_size = 6

    # Check inventory for inserters
    inserters_in_inventory = game.inspect_inventory()[Prototype.BurnerInserter]

    # Array to keep track of burner inserters in the grid
    inserters = [[None for _ in range(grid_size)] for _ in range(grid_size)]

    for i in range(0, grid_size, 2):
        for j in range(0, grid_size, 2):
            # Place burner inserters with orientation to pass items to the left and up
            # Assuming the orientation is controlled by a parameter in place_entity
            try:
                inserters[i][j] = game.place_entity(Prototype.BurnerInserter,
                                                    direction=Direction.LEFT,
                                                    position=Position(x=i, y=j))
            except Exception as e:
                pass

    for i in range(1, grid_size, 2):
        for j in range(1, grid_size, 2):
            # Place burner inserters with orientation to pass items to the left and up
            # Assuming the orientation is controlled by a parameter in place_entity
            try:
                inserters[i][j] = game.place_entity(Prototype.BurnerInserter,
                                                    direction=Direction.UP,
                                                    position=Position(x=i, y=j))

            except Exception as e:
                pass

    try:
        # Place coal at the bottom right inserter
        source = game.place_entity(Prototype.IronChest, position=inserters[-1][-1].pickup_position)
        target = game.place_entity(Prototype.IronChest, position=inserters[0][0].drop_position)
        game.insert_item(Prototype.Coal, source, 50)
        # Wait for some time to allow coal to move, assuming there's a method to wait in game
        sleep(10)  # Wait for 200 ticks or adjust as needed based on game speed

        # Now check if the coal has reached the top left point (i.e., the first inserter in the grid)
        # Assuming there's a method to inspect the contents of an inserter
        target_inventory = game.inspect_inventory(entity=target)

        current_inserters_in_inventory = game.inspect_inventory()[Prototype.BurnerInserter]

        spent_inserters = (inserters_in_inventory - current_inserters_in_inventory)

        # Assert the spent inserters and if the coal reached its destination
        assert spent_inserters == 18

        coal_in_final_chest = target_inventory[Prototype.Coal]

        assert coal_in_final_chest >= 5
    except Exception as e:
        print(e)
        assert False

    game.reset()  # Reset the game state after each iteration

def test_failure_to_connect_adjacent_furnaces(game):
    """
    Place adjacent furnaces and fail to connect them with transport belts.
    :param game:
    :return:
    """
    iron_position = game.nearest(Resource.IronOre)
    game.move_to(iron_position)

    drill = game.place_entity(Prototype.BurnerMiningDrill, position=iron_position, direction=Direction.UP, exact=True)
    furnace = game.place_entity_next_to(Prototype.StoneFurnace, reference_position=drill.position, direction=Direction.LEFT, spacing=2)
    inserter = game.place_entity_next_to(Prototype.BurnerInserter, reference_position=furnace.position, direction=Direction.RIGHT, spacing=0)
    inserter = game.rotate_entity(inserter, Direction.LEFT)
    result = game.connect_entities(target=inserter, source=drill, connection_type=Prototype.TransportBelt)

    # insert coal in the drill
    game.insert_item(Prototype.Coal, drill, 50)

    # wait for the iron to be mined
    sleep(5)

    # check if the coal was inserted in the furnace
    assert game.inspect_inventory(entity=furnace)[Prototype.IronOre] > 1
    game.reset()

def test_inserter_pickup_positions(game):

    # Lay belts from intermediate position to iron position (along X-axis)
    iron_position = game.nearest(Resource.IronOre)
    far_left_of_iron = Position(x=iron_position.x + 10, y=iron_position.y)
    left_of_iron = Position(x=iron_position.x + 1, y=iron_position.y)
    coal_belt = game.connect_entities(far_left_of_iron, left_of_iron,
                                            connection_type=Prototype.TransportBelt)

    # Place the iron mining drill at iron_position, facing down
    move_to_iron = game.move_to(iron_position)
    iron_drill = game.place_entity(Prototype.BurnerMiningDrill, position=iron_position, direction=Direction.DOWN)

    # Place an inserter to fuel the iron drill from the coal belt
    inserter_position = Position(x=coal_belt[-1].position.x,
                                 y=coal_belt[-1].position.y)

    iron_drill_fuel_inserter = game.place_entity(Prototype.BurnerInserter, position=inserter_position,
                                                     direction=Direction.LEFT, exact=True)
    # Extend coal belt to pass next to the furnace position
    furnace_position = Position(x=iron_drill.drop_position.x, y=iron_drill.drop_position.y + 1)

    # Place the furnace at the iron drill's drop position
    iron_furnace = game.place_entity(Prototype.StoneFurnace, position=furnace_position)

    # Place an inserter to fuel the furnace from the coal belt
    furnace_fuel_inserter_position = Position(x=iron_furnace.position.x + 1, y=iron_furnace.position.y)
    furnace_fuel_inserter = game.place_entity(Prototype.BurnerInserter, position=furnace_fuel_inserter_position,
                                              direction=Direction.LEFT)

    coal_belt_to_furnace = game.connect_entities(iron_drill_fuel_inserter.pickup_position,
                                                 furnace_fuel_inserter.pickup_position,
                                                 connection_type=Prototype.TransportBelt)
    assert coal_belt_to_furnace[-1].position == furnace_fuel_inserter.pickup_position
    assert coal_belt_to_furnace[0].position == iron_drill_fuel_inserter.pickup_position


def test_inserter_pickup_positions(game):
    # Place two inserters
    inserter1_position = Position(x=0, y=0)
    inserter1 = game.place_entity(Prototype.BurnerInserter, position=inserter1_position, direction=Direction.LEFT,
                                  exact=True)

    inserter2_position = Position(x=0, y=-5)
    inserter2 = game.place_entity(Prototype.BurnerInserter, position=inserter2_position, direction=Direction.LEFT)

    # Connect the inserters with a transport belt
    belt = game.connect_entities(inserter1.pickup_position, inserter2.pickup_position,
                                 connection_type=Prototype.TransportBelt)

    assert len(belt) == int(abs(inserter1_position.y - inserter2_position.y) + 1)

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
    poles_in_inventory = game.inspect_inventory()[Prototype.SmallElectricPole]

    poles = game.connect_entities(steam_engine, assembler, connection_type=Prototype.SmallElectricPole)
    poles2 = game.connect_entities(steam_engine, diagonal_assembler, connection_type=Prototype.SmallElectricPole)

    current_poles_in_inventory = game.inspect_inventory()[Prototype.SmallElectricPole]
    spent_poles = (poles_in_inventory - current_poles_in_inventory)

    assert spent_poles == len(poles + poles2)


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
    inspection = game.inspect_entities(position=steam_engine.position)

    assert inspection.get_entity(Prototype.SteamEngine).warning == 'not receiving electricity'

def test_connect_transport_belts_to_inserter_row(game):
    # Find the nearest iron ore patch
    iron_ore_patch = game.get_resource_patch(Resource.IronOre, game.nearest(Resource.IronOre))

    # Move to the center of the iron ore patch
    game.move_to(iron_ore_patch.bounding_box.left_top)

    # Place burner mining drill
    miner = game.place_entity(Prototype.BurnerMiningDrill, Direction.DOWN, iron_ore_patch.bounding_box.left_top)

    # Place a transport belt from the miner's output
    iron_belt_start = game.place_entity_next_to(Prototype.TransportBelt, miner.position, Direction.DOWN, spacing=0)
    assert iron_belt_start.position.is_close(miner.drop_position, 1)
    # Place 5 stone furnaces along the belt with burner inserters facing down from above
    furnace_line_start = game.place_entity_next_to(Prototype.StoneFurnace, miner.drop_position, Direction.DOWN,
                                                   spacing=2)
    # Create a row of burner inserters to fuel the furnaces from the belt
    inserter_line_start = game.place_entity_next_to(Prototype.BurnerInserter, furnace_line_start.position, Direction.UP,
                                                    spacing=0)
    inserter_line_start = game.rotate_entity(inserter_line_start, Direction.DOWN)

    current_furnace = furnace_line_start
    current_inserter = inserter_line_start

    for _ in range(3):
        current_furnace = game.place_entity_next_to(Prototype.StoneFurnace, current_furnace.position, Direction.RIGHT,
                                                    spacing=1)
        current_inserter = game.place_entity_next_to(Prototype.BurnerInserter, current_furnace.position,
                                                     Direction.UP, spacing=0)
        current_inserter = game.rotate_entity(current_inserter, Direction.DOWN)

    # Connect furnaces with transport belt
    above_current_furnace = Position(x=current_furnace.position.x, y=current_furnace.position.y - 2.5)
    game.connect_entities(iron_belt_start.output_position, above_current_furnace, Prototype.TransportBelt)

    pass

def test_ensure_final_belt_is_the_correct_orientation(game):
    # move to 0,0 and Place chest there
    game.move_to(Position(x=0, y=0))

    # place another inserter next to the chest
    chest_inserter2 = game.place_entity_next_to(Prototype.BurnerInserter, reference_position=Position(x=0, y=0),
                                           direction=Direction.LEFT)
    assert chest_inserter2, "Failed to place inserter"
    print(f"Second Inserter placed at {chest_inserter2.position}")

    # Place a drill to copper ore patch
    copper_ore_patch = game.get_resource_patch(Resource.CopperOre, game.nearest(Resource.CopperOre))
    assert copper_ore_patch, "No copper ore patch found"
    print(f"copper ore patch found at {copper_ore_patch.bounding_box.center}")

    # Place burner mining drill on copper ore patch
    game.move_to(copper_ore_patch.bounding_box.center)
    copper_drill = game.place_entity(Prototype.BurnerMiningDrill, direction=Direction.RIGHT,
                                position=copper_ore_patch.bounding_box.center)
    assert copper_drill, "Failed to place burner mining drill"
    print(f"Burner mining drill placed at {copper_drill.position}")

    # place a burner inserter next to the copper drill
    copper_drill_inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                                      reference_position=copper_drill.position,
                                                      direction=Direction.LEFT)
    assert copper_drill_inserter, "Failed to place inserter"
    print(f"Inserter placed at {copper_drill_inserter.position}")

    # rotate the inserter to face the drill
    copper_drill_inserter = game.rotate_entity(copper_drill_inserter, Direction.RIGHT)
    assert copper_drill_inserter.direction.value == Direction.RIGHT.value, "Failed to rotate inserter"

    # add coal to the inserter
    inserter_with_coal = game.insert_item(Prototype.Coal, copper_drill_inserter, quantity=5)
    assert inserter_with_coal.fuel_inventory.get(Prototype.Coal, 0) > 0, "Failed to fuel inserter"

    # connect drill_inserter to chest_inserter with transport belts
    belts = game.connect_entities(chest_inserter2, copper_drill_inserter, connection_type=Prototype.TransportBelt)
    assert belts, "Failed to connect entities with transport belts"