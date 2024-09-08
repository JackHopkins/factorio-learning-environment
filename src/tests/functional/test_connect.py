from time import sleep
from typing import List

import pytest

from factorio_entities import Entity, Position
from factorio_instance import Direction
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance


def test_connect_steam_engines_to_boilers_using_pipes(game):
    """
    Place a boiler and a steam engine next to each other in 3 cardinal directions.
    :param game:
    :return:
    """
    boilers_in_inventory = game.inspect_inventory()[Prototype.Boiler]
    steam_engines_in_inventory = game.inspect_inventory()[Prototype.SteamEngine]
    pipes_in_inventory = game.inspect_inventory()[Prototype.Pipe]

    boiler: Entity = game.place_entity(Prototype.Boiler, position=Position(x=0, y=0))
    game.move_to(Position(x=0, y=10))
    steam_engine: Entity = game.place_entity(Prototype.SteamEngine, position=Position(x=0, y=10))

    try:
        connection: List[Entity] = game.connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)
        assert False
    except Exception as e:
        print(e)
        assert True
    game.reset()

    # Define the offsets for the four cardinal directions
    offsets = [Position(x=10, y=0), Position(x=0, y=-10), Position(x=-10, y=0)]  # Up, Right, Down, Left  (0, -10),

    for offset in offsets:
        boiler: Entity = game.place_entity(Prototype.Boiler, position=Position(x=0, y=0))
        game.move_to(offset)

        steam_engine: Entity = game.place_entity(Prototype.SteamEngine, position=offset)

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

        game.reset()  # Reset the game state after each iteration

def test_place_and_connect_entities_in_grid(game):
    """
    Place a grid of furnaces and connect them with burner inserters.
    :param game:
    :return:
    """
    furnaces_in_inventory = game.inspect_inventory()[Prototype.StoneFurnace]
    inserters_in_inventory = game.inspect_inventory()[Prototype.BurnerInserter]


    grid_size = 3
    furnaces = [[None for _ in range(grid_size)] for _ in range(grid_size)]

    for i in range(grid_size):
        for j in range(grid_size):
            furnaces[i][j] = game.place_entity(Prototype.StoneFurnace, position=Position(x=1+(i*3), y=1+(j*3)))

    for i in range(grid_size):
        for j in range(grid_size - 1):
            try:
                connection = game.connect_entities(furnaces[i][j], furnaces[i][j+1], connection_type=Prototype.BurnerInserter)
            except Exception as e:
                print(e)
                assert False

    for i in range(grid_size - 1):
        for j in range(grid_size):
            try:
                connection = game.connect_entities(furnaces[i][j], furnaces[i+1][j], connection_type=Prototype.BurnerInserter)
            except Exception as e:
                print(e)
                assert False

    current_furnaces_in_inventory = game.inspect_inventory()[Prototype.StoneFurnace]
    current_inserters_in_inventory = game.inspect_inventory()[Prototype.BurnerInserter]

    spent_furnaces = (furnaces_in_inventory - current_furnaces_in_inventory)
    spent_inserters = (inserters_in_inventory - current_inserters_in_inventory)

    assert spent_furnaces == grid_size * grid_size
    assert spent_inserters == 4 * grid_size * (grid_size - 1)

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
    game.move_to(coal)
    miner = game.place_entity(Prototype.BurnerMiningDrill, position=coal)

    belts_in_inventory = game.inspect_inventory()[Prototype.TransportBelt]
    try:
        connection = game.connect_entities(miner, inserter, connection_type=Prototype.TransportBelt)
    except Exception as e:
        pass

    current_belts_in_inventory = game.inspect_inventory()[Prototype.TransportBelt]
    spent_belts = (belts_in_inventory - current_belts_in_inventory)
    assert spent_belts == len(connection)


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
                                                    position=(i, j),
                                                    direction=game.RIGHT)
            except Exception as e:
                pass

    for i in range(1, grid_size, 2):
        for j in range(1, grid_size, 2):
            # Place burner inserters with orientation to pass items to the left and up
            # Assuming the orientation is controlled by a parameter in place_entity
            try:
                inserters[i][j] = game.place_entity(Prototype.BurnerInserter,
                                                    position=Position(x=i, y=j),
                                                    direction=game.UP)
            except Exception as e:
                pass

    try:
        # Place coal at the bottom right inserter
        source = game.place_entity(Prototype.IronChest, position=inserters[-1][-1].pickup_position)
        target = game.place_entity(Prototype.IronChest, position=inserters[0][0].drop_position)
        game.insert_item(Prototype.Coal, source, 50)
        # Wait for some time to allow coal to move, assuming there's a method to wait in game
        sleep(60)  # Wait for 200 ticks or adjust as needed based on game speed

        # Now check if the coal has reached the top left point (i.e., the first inserter in the grid)
        # Assuming there's a method to inspect the contents of an inserter
        target_inventory = game.inspect_inventory(entity=target)

        current_inserters_in_inventory = game.inspect_inventory()[Prototype.BurnerInserter]

        spent_inserters = (inserters_in_inventory - current_inserters_in_inventory)

        # Assert the spent inserters and if the coal reached its destination
        assert spent_inserters == 18

        coal_in_final_chest = target_inventory[Prototype.Coal]

        assert coal_in_final_chest > 20
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

    drill = game.place_entity(Prototype.BurnerMiningDrill, position=iron_position, direction=Direction.UP)
    furnace = game.place_entity_next_to(Prototype.StoneFurnace, reference_position=drill.position, direction=Direction.LEFT, spacing=1)
    game.connect_entities(source=drill, target=furnace, connection_type=Prototype.TransportBelt)

    print()