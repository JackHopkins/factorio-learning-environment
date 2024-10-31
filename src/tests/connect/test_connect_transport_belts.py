import math
from time import sleep
from typing import List

import pytest

from factorio_entities import Entity, Position, ResourcePatch
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
    yield instance
    instance.speed(1)
    #instance.reset()


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
    inserter_position = Position(x=coal_belt[0].belts[-1].position.x,
                                 y=coal_belt[0].belts[-1].position.y)

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
    assert coal_belt_to_furnace[0].belts[-1].position == furnace_fuel_inserter.pickup_position
    assert coal_belt_to_furnace[0].belts[0].position == iron_drill_fuel_inserter.pickup_position

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
                                         spacing=0)
    inserter = game.rotate_entity(inserter, Direction.LEFT)

    game.move_to(coal)
    miner = game.place_entity(Prototype.BurnerMiningDrill, position=coal)

    belts_in_inventory = game.inspect_inventory()[Prototype.TransportBelt]

    connection = game.connect_entities(miner, inserter, connection_type=Prototype.TransportBelt)

    current_belts_in_inventory = game.inspect_inventory()[Prototype.TransportBelt]
    spent_belts = (belts_in_inventory - current_belts_in_inventory)
    assert spent_belts == len(connection[0].belts)

def test_failure_to_connect_adjacent_furnaces(game):
    """
    Place adjacent furnaces and fail to connect them with transport belts.
    :param game:
    :return:
    """
    iron_position = game.nearest(Resource.IronOre)
    game.move_to(iron_position)

    drill = game.place_entity(Prototype.BurnerMiningDrill, position=iron_position, direction=Direction.UP, exact=False)
    furnace = game.place_entity_next_to(Prototype.StoneFurnace, reference_position=drill.position, direction=Direction.LEFT, spacing=2)
    inserter = game.place_entity_next_to(Prototype.BurnerInserter, reference_position=furnace.position, direction=Direction.RIGHT, spacing=0)
    inserter = game.rotate_entity(inserter, Direction.LEFT)
    result = game.connect_entities(target=inserter, source=drill, connection_type=Prototype.TransportBelt)

    # insert coal in the drill
    game.insert_item(Prototype.Coal, drill, 50)

    # wait for the iron to be mined
    sleep(5)

    # check if the coal was inserted in the furnace
    assert game.inspect_inventory(entity=furnace)[Prototype.IronOre] > 0

def test_inserter_pickup_positions2(game):
    # Place two inserters
    inserter1_position = Position(x=0, y=0)
    inserter1 = game.place_entity(Prototype.BurnerInserter, position=inserter1_position, direction=Direction.LEFT,
                                  exact=True)

    inserter2_position = Position(x=0, y=-5)
    inserter2 = game.place_entity(Prototype.BurnerInserter, position=inserter2_position, direction=Direction.LEFT)

    # Connect the inserters with a transport belt
    belt = game.connect_entities(inserter1.pickup_position, inserter2.pickup_position,
                                 connection_type=Prototype.TransportBelt)

    assert len(belt[0].belts) == int(abs(inserter1_position.y - inserter2_position.y) + 1)

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
    belt_group = game.connect_entities(iron_belt_start.output_position, current_inserter.pickup_position, Prototype.TransportBelt)

    assert belt_group[0].belts[-1].position.is_close(current_inserter.pickup_position, 0.5), f"Final belt position: {belt_group[0].belts[-1].position}, expected: {current_inserter.pickup_position}"

def test_ensure_final_belt_is_the_correct_orientation(game):
    # Place a drill to copper ore patch
    copper_ore_patch = game.get_resource_patch(Resource.CopperOre, game.nearest(Resource.CopperOre))
    assert copper_ore_patch, "No copper ore patch found"
    print(f"copper ore patch found at {copper_ore_patch.bounding_box.center}")

    # move to 0,0 and Place chest there
    #game.move_to(copper_ore_patch.bounding_box.top_left)

    # place another inserter next to the chest
    chest_inserter2 = game.place_entity_next_to(Prototype.BurnerInserter, reference_position=Position(x=0, y=0),
                                           direction=Direction.LEFT)
    assert chest_inserter2, "Failed to place inserter"
    print(f"Second Inserter placed at {chest_inserter2.position}")


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
    assert inserter_with_coal.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel inserter"

    # connect drill_inserter to chest_inserter with transport belts
    beltgroup = game.connect_entities(chest_inserter2, copper_drill_inserter, connection_type=Prototype.TransportBelt)
    assert beltgroup[0].belts[-1].direction.value == Direction.DOWN.value, "Final belt is not facing down"

def test_no_broken_edges(game):
    """
    There is a weird issue where the full path is missing a point in the middle, and so the belt is broken.
    :param game:
    :return:
    """
    # For this we need to first put 2 drills at copper and iron ore patches
    # then we need to put a chest at a central location with burner inserters
    # Finally we need to connect the drills to the burner inserters with transport belts.
    # Find a copper ore patch
    copper_ore_patch = game.get_resource_patch(Resource.CopperOre, game.nearest(Resource.CopperOre))
    assert copper_ore_patch, "No copper ore patch found"
    print(f"copper ore patch found at {copper_ore_patch.bounding_box.center}")

    # Place burner mining drill on copper ore patch
    game.move_to(copper_ore_patch.bounding_box.center)
    drill = game.place_entity(Prototype.BurnerMiningDrill, direction=Direction.RIGHT,
                         position=copper_ore_patch.bounding_box.center)
    assert drill, "Failed to place burner mining drill"
    print(f"Burner mining drill placed at {drill.position}")

    # Fuel the burner mining drill
    copper_ore_drill_with_coal = game.insert_item(Prototype.Coal, drill, quantity=5)
    assert copper_ore_drill_with_coal.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel burner mining drill"
    print(f"Inserted {copper_ore_drill_with_coal.fuel.get(Prototype.Coal, 0)} coal into burner mining drill")

    # move to 0,0 and Place chest there
    game.move_to(Position(x=0, y=0))
    chest = game.place_entity(Prototype.WoodenChest, position=Position(x=0, y=0))
    assert chest, "Failed to place chest"

    # place a burner inserter next to the chest for copper plates
    chest_copper_inserter = game.place_entity_next_to(Prototype.BurnerInserter, reference_position=chest.position,
                                                 direction=Direction.RIGHT)
    assert chest_copper_inserter, "Failed to place inserter"
    print(f"Inserter placed at {chest_copper_inserter.position}")

    # We need to rotate the inserter to face the chest as by default it takes from the chest not puts to it
    chest_copper_inserter = game.rotate_entity(chest_copper_inserter, Direction.LEFT)
    assert chest_copper_inserter.direction.value == Direction.LEFT.value, "Failed to rotate inserter"

    # add coal to the copper inserter
    inserter_with_coal = game.insert_item(Prototype.Coal, chest_copper_inserter, quantity=5)
    assert inserter_with_coal.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel inserter"

    # connect copper_furnace_inserter to chest_copper_inserter with transport belts
    # use the drop and pickup positions of the drills and inserters
    belt_group = game.connect_entities(copper_ore_drill_with_coal.drop_position,
                                       chest_copper_inserter.pickup_position,
                                       connection_type=Prototype.TransportBelt)
    assert belt_group, "Failed to connect entities with transport belts"

    # Verify all belts are facing either UP or LEFT
    for belt in belt_group[0].belts:
        assert belt.direction.value in [Direction.UP.value, Direction.LEFT.value], f"Found belt with direction {belt.direction}"

def test_connecting_transport_belts_around_sharp_edges(game):
    water_patch: ResourcePatch = game.get_resource_patch(Resource.Water, game.nearest(Resource.Water))

    # move to the water patch
    game.move_to(water_patch.bounding_box.left_top)

    # connect transport belts around the water patch
    belts = game.connect_entities(water_patch.bounding_box.left_top, water_patch.bounding_box.right_bottom,
                                  connection_type=Prototype.TransportBelt)

    assert len(belts) == 1, "Failed to connect transport belts around the water patch"

def test_connecting_transport_belts_around_sharp_edges2(game):
    iron_patch: ResourcePatch = game.get_resource_patch(Resource.IronOre, game.nearest(Resource.IronOre))

    right_top = Position(x=iron_patch.bounding_box.right_bottom.x, y=iron_patch.bounding_box.left_top.y)
    left_bottom = Position(x=iron_patch.bounding_box.left_top.x, y=iron_patch.bounding_box.right_bottom.y)
    positions = [left_bottom, iron_patch.bounding_box.left_top, right_top, iron_patch.bounding_box.right_bottom]

    for position in positions:
        # move to the iron patch
        game.move_to(position)

        # place a miner
        miner = game.place_entity(Prototype.BurnerMiningDrill, position=position, direction=Direction.LEFT)

        # connect transport belts around the water patch
        belts = game.connect_entities(miner, Position(x=0, y=0), connection_type=Prototype.TransportBelt)

        assert len(belts) == 1, "Failed to connect transport belts around the water patch"

        game.reset()


def test_connect_belt_groups_horizontally(game):

    # Create a horizontal belt group
    belt_group_right = game.connect_entities(Position(x=0, y=0), Position(x=5, y=0), Prototype.TransportBelt)

    # Loop the belt back around
    belt_group_right = game.connect_entities(belt_group_right[0], belt_group_right[0], Prototype.TransportBelt)

    # This should result in a single contiguous group
    assert len(belt_group_right) == 1

    belt_group_left = game.connect_entities(Position(x=0, y=-10), Position(x=-5, y=-10), Prototype.TransportBelt)

    # Loop the belt back around
    belt_group_left = game.connect_entities(belt_group_left[0], belt_group_left[0], Prototype.TransportBelt)

    # This should result in a single contiguous group
    assert len(belt_group_left) == 1

def test_connect_belt_groups_vertically(game):

    # Create a vertical belt group
    belt_group_down = game.connect_entities(Position(x=0, y=0), Position(x=0, y=5), Prototype.TransportBelt)

    # Loop the belt back around
    belt_group_down = game.connect_entities(belt_group_down[0], belt_group_down[0], Prototype.TransportBelt)

    # This should result in a single contiguous group
    assert len(belt_group_down) == 1

    belt_group_up = game.connect_entities(Position(x=-2, y=0), Position(x=-2, y=-5), Prototype.TransportBelt)

    # Loop the belt back around
    belt_group_up = game.connect_entities(belt_group_up[0], belt_group_up[0], Prototype.TransportBelt)

    # This should result in a single contiguous group
    assert len(belt_group_up) == 1

def test_connect_belt_groups_diagonally(game):
        belt_group_up_left = game.connect_entities(Position(x=0, y=0), Position(x=-5, y=-5), Prototype.TransportBelt)

        # Loop the belt back around
        belt_group_up_left = game.connect_entities(belt_group_up_left[0], belt_group_up_left[0], Prototype.TransportBelt)

        # This should result in a single contiguous group
        assert len(belt_group_up_left) == 1

def test_connect_belt_groups_into_a_square(game):
    # Create a square belt group
    belt_group = game.connect_entities(Position(x=0, y=0), Position(x=5, y=0), Prototype.TransportBelt)
    belt_group = game.connect_entities(belt_group[0], Position(x=5, y=5), Prototype.TransportBelt)
    belt_group = game.connect_entities(belt_group[0], Position(x=0, y=5), Prototype.TransportBelt)
    belt_group = game.connect_entities(belt_group[0], belt_group[0], Prototype.TransportBelt)

    # This should result in a single contiguous group
    assert len(belt_group) == 1

def test_connect_betl_groups_into_an_octagon(game):
    # Create an octagon belt group
    belt_group = game.connect_entities(Position(x=0, y=0), Position(x=5, y=0), Prototype.TransportBelt)
    belt_group = game.connect_entities(belt_group[0], Position(x=7, y=2), Prototype.TransportBelt)
    belt_group = game.connect_entities(belt_group[0], Position(x=7, y=5), Prototype.TransportBelt)
    belt_group = game.connect_entities(belt_group[0], Position(x=5, y=7), Prototype.TransportBelt)
    belt_group = game.connect_entities(belt_group[0], Position(x=0, y=7), Prototype.TransportBelt)
    belt_group = game.connect_entities(belt_group[0], Position(x=-2, y=5), Prototype.TransportBelt)
    belt_group = game.connect_entities(belt_group[0], Position(x=-2, y=2), Prototype.TransportBelt)
    belt_group = game.connect_entities(belt_group[0], belt_group[0], Prototype.TransportBelt)

    # This should result in a single contiguous group
    assert len(belt_group) == 1
