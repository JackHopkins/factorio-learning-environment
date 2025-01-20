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
        'assembling-machine': 10,
    }
    instance.speed(10)
    instance.reset()
    yield instance.namespace
    #instance.reset()
    instance.speed(1)



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
    #game.reset()

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