from time import sleep

import pytest

from fle.env.entities import Position, ResourcePatch, BeltGroup, Direction
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
        "underground-belt": 2,
        "transport-belt": 200,
        "coal": 100,
        "wooden-chest": 5,
        "assembling-machine": 10,
    }
    instance.speed(10)
    instance.reset()
    yield instance.namespace
    instance.speed(10)
    # instance.reset()


def test_multiple_inserter_connections(game):
    """
    Tests placing multiple pairs of burner inserters and connecting them with transport belts.
    Verifies the belt positions and connections for each iteration.
    """
    test_iterations = 5  # Number of inserter pairs to test

    for i in range(test_iterations):
        # Place first inserter at position with some offset from origin
        position_1 = Position(x=i * 5, y=i * 3)
        game.move_to(position_1)
        inserter_1 = game.place_entity(
            Prototype.BurnerInserter,
            position=position_1,
            direction=Direction.LEFT,
            exact=True,
        )

        # Place second inserter at a different position
        position_2 = Position(x=i * 5 + 10, y=i * 3 + 8)
        game.move_to(position_2)
        inserter_2 = game.place_entity(
            Prototype.BurnerInserter,
            position=position_2,
            direction=Direction.LEFT,
            exact=True,
        )

        # Connect the inserters with transport belts
        belt_groups = game.connect_entities(
            inserter_1, inserter_2, connection_type=Prototype.TransportBelt
        )

        # Verify we got exactly one belt group
        assert belt_groups, (
            f"Iteration {i}: Expected 1 belt group, got {len(belt_groups)}"
        )

        belt_group = belt_groups

        # Verify the belt group has belts
        assert len(belt_group.belts) >= 20, f"Iteration {i}: Belt group has no belts"

        # Verify the number of belts matches the Manhattan distance between inserters
        expected_belt_count = (
            int(abs(position_1.x - position_2.x) + abs(position_1.y - position_2.y)) + 1
        )  # +1 because we need to include both end points

        assert len(belt_group.belts) >= expected_belt_count, (
            f"Iteration {i}: Expected at least {expected_belt_count} belts, "
            f"got {len(belt_group.belts)}"
        )

        # Clean up for next iteration
        game.instance.reset()


def test_inserter_pickup_positions(game):
    # Lay belts from intermediate position to iron position (along X-axis)
    iron = game.get_resource_patch(Resource.IronOre, game.nearest(Resource.IronOre))
    left_of_iron = iron.bounding_box.left_top.up().right(10)
    far_left_of_iron = iron.bounding_box.left_top.up().right(2)

    coal_belt = game.connect_entities(
        left_of_iron, far_left_of_iron, connection_type=Prototype.TransportBelt
    )

    # Place the iron mining drill at iron_position, facing down
    game.move_to(far_left_of_iron.down())
    iron_drill = game.place_entity(
        Prototype.BurnerMiningDrill,
        position=far_left_of_iron.down(3),
        direction=Direction.DOWN,
        exact=True,
    )

    # Place an inserter to fuel the iron drill from the coal belt
    inserter_position = Position(
        x=coal_belt.inputs[0].input_position.x, y=coal_belt.inputs[0].input_position.y
    )

    iron_drill_fuel_inserter = game.place_entity(
        Prototype.BurnerInserter,
        position=inserter_position,
        direction=Direction.LEFT,
        exact=True,
    )
    # Extend coal belt to pass next to the furnace position
    furnace_position = Position(
        x=iron_drill.drop_position.x, y=iron_drill.drop_position.y
    )

    # Place the furnace at the iron drill's drop position
    iron_furnace = game.place_entity(Prototype.StoneFurnace, position=furnace_position)

    # Place an inserter to fuel the furnace from the coal belt
    furnace_fuel_inserter_position = Position(
        x=iron_furnace.position.x + 1, y=iron_furnace.position.y
    )
    furnace_fuel_inserter = game.place_entity(
        Prototype.BurnerInserter,
        position=furnace_fuel_inserter_position,
        direction=Direction.LEFT,
    )

    coal_belt_to_furnace = game.connect_entities(
        iron_drill_fuel_inserter.pickup_position,
        furnace_fuel_inserter.pickup_position,
        connection_type=Prototype.TransportBelt,
    )
    assert (
        coal_belt_to_furnace.outputs[0].position
        == furnace_fuel_inserter.pickup_position
    )
    assert (
        coal_belt_to_furnace.inputs[0].position
        == iron_drill_fuel_inserter.pickup_position
    )


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
    inserter = game.place_entity_next_to(
        Prototype.BurnerInserter,
        reference_position=furnace.position,
        direction=game.RIGHT,
        spacing=0,
    )
    inserter = game.rotate_entity(inserter, Direction.LEFT)

    game.move_to(coal)
    miner = game.place_entity(Prototype.BurnerMiningDrill, position=coal)

    belts_in_inventory = game.inspect_inventory()[Prototype.TransportBelt]

    connection = game.connect_entities(
        miner, inserter, connection_type=Prototype.TransportBelt
    )

    current_belts_in_inventory = game.inspect_inventory()[Prototype.TransportBelt]
    spent_belts = belts_in_inventory - current_belts_in_inventory
    assert spent_belts == len(connection.belts)


def test_failure_to_connect_adjacent_furnaces(game):
    """
    Place adjacent furnaces and fail to connect them with transport belts.
    :param game:
    :return:
    """
    iron_position = game.nearest(Resource.IronOre)
    game.move_to(iron_position)

    drill = game.place_entity(
        Prototype.BurnerMiningDrill,
        position=iron_position,
        direction=Direction.UP,
        exact=False,
    )
    furnace = game.place_entity_next_to(
        Prototype.StoneFurnace,
        reference_position=drill.position,
        direction=Direction.LEFT,
        spacing=2,
    )
    inserter = game.place_entity_next_to(
        Prototype.BurnerInserter,
        reference_position=furnace.position,
        direction=Direction.RIGHT,
        spacing=0,
    )
    inserter = game.rotate_entity(inserter, Direction.LEFT)
    game.connect_entities(
        target=inserter, source=drill, connection_type=Prototype.TransportBelt
    )

    # insert coal in the drill
    game.insert_item(Prototype.Coal, drill, 50)

    # wait for the iron to be mined
    sleep(5)

    # check if the coal was inserted in the furnace
    assert game.inspect_inventory(entity=furnace)[Prototype.IronOre] > 0


def test_inserter_pickup_positions2(game):
    # Place two inserters
    inserter1_position = Position(x=0, y=0)
    inserter1 = game.place_entity(
        Prototype.BurnerInserter,
        position=inserter1_position,
        direction=Direction.LEFT,
        exact=True,
    )

    inserter2_position = Position(x=0, y=-5)
    inserter2 = game.place_entity(
        Prototype.BurnerInserter, position=inserter2_position, direction=Direction.LEFT
    )

    # Connect the inserters with a transport belt
    belt = game.connect_entities(
        inserter1.pickup_position,
        inserter2.pickup_position,
        connection_type=Prototype.TransportBelt,
    )

    assert len(belt.belts) == int(abs(inserter1_position.y - inserter2_position.y) + 1)


def test_connect_transport_belts_to_inserter_row(game):
    # Find the nearest iron ore patch
    iron_ore_patch = game.get_resource_patch(
        Resource.IronOre, game.nearest(Resource.IronOre)
    )

    # Move to the center of the iron ore patch
    game.move_to(iron_ore_patch.bounding_box.left_top)

    # Place burner mining drill
    miner = game.place_entity(
        Prototype.BurnerMiningDrill,
        Direction.DOWN,
        iron_ore_patch.bounding_box.left_top,
    )

    # Place a transport belt from the miner's output
    iron_belt_start = game.place_entity_next_to(
        Prototype.TransportBelt, miner.position, Direction.DOWN, spacing=0
    )
    assert iron_belt_start.position.is_close(miner.drop_position, 1)
    # Place 5 stone furnaces along the belt with burner inserters facing down from above
    furnace_line_start = game.place_entity_next_to(
        Prototype.StoneFurnace, miner.drop_position, Direction.DOWN, spacing=2
    )
    # Create a row of burner inserters to fuel the furnaces from the belt
    inserter_line_start = game.place_entity_next_to(
        Prototype.BurnerInserter, furnace_line_start.position, Direction.UP, spacing=0
    )
    inserter_line_start = game.rotate_entity(inserter_line_start, Direction.DOWN)

    current_furnace = furnace_line_start
    current_inserter = inserter_line_start

    for _ in range(3):
        current_furnace = game.place_entity_next_to(
            Prototype.StoneFurnace, current_furnace.position, Direction.RIGHT, spacing=1
        )
        current_inserter = game.place_entity_next_to(
            Prototype.BurnerInserter, current_furnace.position, Direction.UP, spacing=0
        )
        current_inserter = game.rotate_entity(current_inserter, Direction.DOWN)

    # Connect furnaces with transport belt
    belt_group = game.connect_entities(
        iron_belt_start.output_position,
        current_inserter.pickup_position,
        Prototype.TransportBelt,
    )

    assert belt_group.outputs[0].position.is_close(
        current_inserter.pickup_position, 0.5
    ), (
        f"Final belt position: {belt_group.outputs[0].position}, expected: {current_inserter.pickup_position}"
    )


def test_ensure_final_belt_is_the_correct_orientation(game):
    # Place a drill to copper ore patchd
    copper_ore_patch = game.get_resource_patch(
        Resource.CopperOre, game.nearest(Resource.CopperOre)
    )
    assert copper_ore_patch, "No copper ore patch found"
    print(f"copper ore patch found at {copper_ore_patch.bounding_box}")

    # move to 0,0 and Place chest there
    # game.move_to(copper_ore_patch.bounding_box.top_left)

    # place another inserter next to the chest
    chest_inserter2 = game.place_entity_next_to(
        Prototype.BurnerInserter,
        reference_position=Position(x=0, y=0),
        direction=Direction.LEFT,
    )
    assert chest_inserter2, "Failed to place inserter"
    print(f"Second Inserter placed at {chest_inserter2.position}")

    # Place burner mining drill on copper ore patch
    game.move_to(copper_ore_patch.bounding_box.center)
    copper_drill = game.place_entity(
        Prototype.BurnerMiningDrill,
        direction=Direction.RIGHT,
        position=copper_ore_patch.bounding_box.center,
    )
    assert copper_drill, "Failed to place burner mining drill"
    print(f"Burner mining drill placed at {copper_drill.position}")

    # place a burner inserter next to the copper drill
    copper_drill_inserter = game.place_entity_next_to(
        Prototype.BurnerInserter,
        reference_position=copper_drill.position,
        direction=Direction.LEFT,
    )
    assert copper_drill_inserter, "Failed to place inserter"
    print(f"Inserter placed at {copper_drill_inserter.position}")

    # rotate the inserter to face the drill
    copper_drill_inserter = game.rotate_entity(copper_drill_inserter, Direction.RIGHT)
    assert copper_drill_inserter.direction.value == Direction.RIGHT.value, (
        "Failed to rotate inserter"
    )

    # add coal to the inserter
    inserter_with_coal = game.insert_item(
        Prototype.Coal, copper_drill_inserter, quantity=5
    )
    assert inserter_with_coal.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel inserter"

    # connect drill_inserter to chest_inserter with transport belts
    beltgroup = game.connect_entities(
        chest_inserter2, copper_drill_inserter, connection_type=Prototype.TransportBelt
    )
    assert beltgroup.belts[-1].direction.value == Direction.DOWN.value, (
        "Final belt is not facing down"
    )


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
    copper_ore_patch = game.get_resource_patch(
        Resource.CopperOre, game.nearest(Resource.CopperOre)
    )
    assert copper_ore_patch, "No copper ore patch found"
    print(f"copper ore patch found at {copper_ore_patch.bounding_box.center}")

    # Place burner mining drill on copper ore patch
    game.move_to(copper_ore_patch.bounding_box.center)
    drill = game.place_entity(
        Prototype.BurnerMiningDrill,
        direction=Direction.RIGHT,
        position=copper_ore_patch.bounding_box.center,
    )
    assert drill, "Failed to place burner mining drill"
    print(f"Burner mining drill placed at {drill.position}")

    # Fuel the burner mining drill
    copper_ore_drill_with_coal = game.insert_item(Prototype.Coal, drill, quantity=5)
    assert copper_ore_drill_with_coal.fuel.get(Prototype.Coal, 0) > 0, (
        "Failed to fuel burner mining drill"
    )
    print(
        f"Inserted {copper_ore_drill_with_coal.fuel.get(Prototype.Coal, 0)} coal into burner mining drill"
    )

    # move to 0,0 and Place chest there
    game.move_to(Position(x=0, y=0))
    chest = game.place_entity(Prototype.WoodenChest, position=Position(x=0, y=0))
    assert chest, "Failed to place chest"

    # place a burner inserter next to the chest for copper plates
    chest_copper_inserter = game.place_entity_next_to(
        Prototype.BurnerInserter,
        reference_position=chest.position,
        direction=Direction.RIGHT,
    )
    assert chest_copper_inserter, "Failed to place inserter"
    print(f"Inserter placed at {chest_copper_inserter.position}")

    # We need to rotate the inserter to face the chest as by default it takes from the chest not puts to it
    chest_copper_inserter = game.rotate_entity(chest_copper_inserter, Direction.LEFT)
    assert chest_copper_inserter.direction.value == Direction.LEFT.value, (
        "Failed to rotate inserter"
    )

    # add coal to the copper inserter
    inserter_with_coal = game.insert_item(
        Prototype.Coal, chest_copper_inserter, quantity=5
    )
    assert inserter_with_coal.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel inserter"

    # connect copper_furnace_inserter to chest_copper_inserter with transport belts
    # use the drop and pickup positions of the drills and inserters
    belt_group = game.connect_entities(
        copper_ore_drill_with_coal.drop_position,
        chest_copper_inserter.pickup_position,
        connection_type=Prototype.TransportBelt,
    )
    assert belt_group, "Failed to connect entities with transport belts"

    game.sleep(60)
    chest = game.get_entity(Prototype.WoodenChest, chest.position)
    assert chest.inventory.get(Prototype.CopperOre, 0) > 0, "Chest is empty"


def test_connecting_transport_belts_around_sharp_edges(game):
    water_patch: ResourcePatch = game.get_resource_patch(
        Resource.Water, game.nearest(Resource.Water)
    )

    # move to the water patch
    game.move_to(water_patch.bounding_box.left_top)

    # connect transport belts around the water patch
    belts = game.connect_entities(
        water_patch.bounding_box.left_top,
        water_patch.bounding_box.right_bottom,
        connection_type=Prototype.TransportBelt,
    )

    assert belts, "Failed to connect transport belts around the water patch"


def test_connecting_transport_belts_around_sharp_edges2(game):
    iron_patch: ResourcePatch = game.get_resource_patch(
        Resource.IronOre, game.nearest(Resource.IronOre)
    )

    right_top = Position(
        x=iron_patch.bounding_box.right_bottom.x, y=iron_patch.bounding_box.left_top.y
    )
    left_bottom = Position(
        x=iron_patch.bounding_box.left_top.x, y=iron_patch.bounding_box.right_bottom.y
    )
    positions = [
        left_bottom,
        iron_patch.bounding_box.left_top,
        right_top,
        iron_patch.bounding_box.right_bottom,
    ]

    for position in positions:
        # move to the iron patch
        game.move_to(position)

        # place a miner
        miner = game.place_entity(
            Prototype.BurnerMiningDrill, position=position, direction=Direction.LEFT
        )

        # connect transport belts around the water patch
        belts = game.connect_entities(
            miner, Position(x=0, y=0), connection_type=Prototype.TransportBelt
        )

        assert belts, "Failed to connect transport belts around the water patch"

        game.instance.reset()


def test_connect_belt_groups_horizontally(game):
    # Create a horizontal belt group
    belt_group_right = game.connect_entities(
        Position(x=0, y=0), Position(x=5, y=0), Prototype.TransportBelt
    )

    # Loop the belt back around
    belt_group_right = game.connect_entities(
        belt_group_right, belt_group_right, Prototype.TransportBelt
    )

    # This should result in a single contiguous group
    assert belt_group_right

    belt_group_left = game.connect_entities(
        Position(x=0, y=-10), Position(x=-5, y=-10), Prototype.TransportBelt
    )

    # Loop the belt back around
    belt_group_left = game.connect_entities(
        belt_group_left, belt_group_left, Prototype.TransportBelt
    )

    # This should result in a single contiguous group
    assert belt_group_left


def test_connect_belt_groups_vertically(game):
    # Create a vertical belt group
    belt_group_down = game.connect_entities(
        Position(x=0, y=0), Position(x=0, y=5), Prototype.TransportBelt
    )

    # Loop the belt back around
    belt_group_down = game.connect_entities(
        belt_group_down, belt_group_down, Prototype.TransportBelt
    )

    # This should result in a single contiguous group
    assert belt_group_down
    assert len(belt_group_down.inputs) == 0
    assert len(belt_group_down.outputs) == 0

    belt_group_up = game.connect_entities(
        Position(x=-2, y=0), Position(x=-2, y=-5), Prototype.TransportBelt
    )

    # Loop the belt back around
    belt_group_up = game.connect_entities(
        belt_group_up, belt_group_up, Prototype.TransportBelt
    )

    # This should result in a single contiguous group
    assert belt_group_up
    assert len(belt_group_up.inputs) == 0
    assert len(belt_group_up.outputs) == 0


def test_connect_belt_groups_diagonally(game):
    belt_group_up_left = game.connect_entities(
        Position(x=0, y=0), Position(x=-5, y=-5), Prototype.TransportBelt
    )

    # Loop the belt back around
    belt_group_up_left = game.connect_entities(
        belt_group_up_left, belt_group_up_left, Prototype.TransportBelt
    )

    # This should result in a single contiguous group
    assert belt_group_up_left
    assert len(belt_group_up_left.inputs) == 0
    assert len(belt_group_up_left.outputs) == 0


def test_connect_belt_groups_into_a_square(game):
    # Create a square belt group
    belt_group = game.connect_entities(
        Position(x=0, y=0), Position(x=5, y=0), Prototype.TransportBelt
    )
    belt_group = game.connect_entities(
        belt_group, Position(x=5, y=5), Prototype.TransportBelt
    )
    belt_group = game.connect_entities(
        belt_group, Position(x=0, y=5), Prototype.TransportBelt
    )
    belt_group = game.connect_entities(belt_group, belt_group, Prototype.TransportBelt)

    # This should result in a single contiguous group
    assert belt_group
    assert len(belt_group.inputs) == 0
    assert len(belt_group.outputs) == 0


def test_connect_belt_groups_into_a_square_waypoints(game):
    # Create a square belt group
    belt_group = game.connect_entities(
        Position(x=0, y=0),
        Position(x=5, y=0),
        Position(x=5, y=5),
        Position(x=0, y=5),
        Position(x=0, y=0),
        Prototype.TransportBelt,
    )
    # This should result in a single contiguous group
    assert belt_group
    assert len(belt_group.inputs) == 1
    assert len(belt_group.outputs) == 1


def test_connect_belt_groups_into_an_octagon(game):
    # Create an octagon belt group
    belt_group = game.connect_entities(
        Position(x=0, y=0), Position(x=5, y=0), Prototype.TransportBelt
    )
    belt_group = game.connect_entities(
        belt_group, Position(x=7, y=2), Prototype.TransportBelt
    )
    belt_group = game.connect_entities(
        belt_group, Position(x=7, y=5), Prototype.TransportBelt
    )
    belt_group = game.connect_entities(
        belt_group, Position(x=5, y=7), Prototype.TransportBelt
    )
    belt_group = game.connect_entities(
        belt_group, Position(x=0, y=7), Prototype.TransportBelt
    )
    belt_group = game.connect_entities(
        belt_group, Position(x=-2, y=5), Prototype.TransportBelt
    )
    belt_group = game.connect_entities(
        belt_group, Position(x=-2, y=2), Prototype.TransportBelt
    )

    assert len(belt_group.inputs) == 1, "There must be a single input"
    assert len(belt_group.outputs) == 1, "There must be a single output"
    belt_group = game.connect_entities(belt_group, belt_group, Prototype.TransportBelt)

    # This should result in a single contiguous group
    assert belt_group
    assert len(belt_group.inputs) == 0
    assert len(belt_group.outputs) == 0


def test_belt_group(game):
    game.connect_entities(
        Position(x=0, y=0), Position(x=5, y=0), Prototype.TransportBelt
    )
    entities = game.get_entities()
    print(entities)
    belt_groups = [
        entity for entity in game.get_entities() if isinstance(entity, BeltGroup)
    ]
    assert belt_groups
    pass


def test_connect_belts_with_end_rotation(game):
    iron_pos = game.nearest(Resource.IronOre)
    game.move_to(iron_pos)
    # Place drills individually with smaller building boxes
    drill2 = game.place_entity(
        Prototype.BurnerMiningDrill, position=iron_pos, direction=Direction.LEFT
    )
    # Place chest about 10 spaces away from the middle drill
    chest_pos = Position(x=iron_pos.x - 10, y=iron_pos.y)
    game.move_to(chest_pos)
    collection_chest = game.place_entity(Prototype.WoodenChest, position=chest_pos)
    print(f"Placed collection chest at {collection_chest.position}")

    # Place inserter next to chest
    chest_inserter = game.place_entity_next_to(
        Prototype.BurnerInserter,
        reference_position=collection_chest.position,
        direction=Direction.LEFT,
        spacing=0,
    )
    # Rotate inserter to put items into chest
    chest_inserter = game.rotate_entity(chest_inserter, Direction.RIGHT)
    print(f"Placed chest inserter at {chest_inserter.position}")

    chest_2_pos = Position(x=chest_pos.x - 10, y=chest_pos.y)
    game.move_to(chest_2_pos)
    collection_chest2 = game.place_entity(Prototype.WoodenChest, position=chest_2_pos)
    print(f"Placed collection chest at {collection_chest2.position}")

    # Place inserter next to chest
    chest_inserter2 = game.place_entity_next_to(
        Prototype.BurnerInserter,
        reference_position=collection_chest2.position,
        direction=Direction.LEFT,
        spacing=0,
    )
    # Rotate inserter to put items into chest
    chest_inserter2 = game.rotate_entity(chest_inserter2, Direction.RIGHT)
    print(f"Placed chest inserter at {chest_inserter2.position}")
    # connect the first drill to the connection system
    main_connection = game.connect_entities(
        drill2.drop_position, chest_inserter2.pickup_position, Prototype.TransportBelt
    )
    # extend connection
    main_connection2 = game.connect_entities(
        main_connection, chest_inserter.pickup_position, Prototype.TransportBelt
    )

    assert len(main_connection2.belts) > 20


def test_merge_belt_into_another_belt(game):
    belt_start_position = Position(x=0.0, y=0.0)
    belt_end_position = Position(x=10.0, y=0.0)
    belts = game.connect_entities(
        belt_start_position, belt_end_position, Prototype.TransportBelt
    )

    game.move_to(Position(x=0.0, y=0.0))
    nbelt_start = Position(x=5.0, y=5.0)
    nbelt_midpoint = belts.belts[len(belts.belts) // 2]
    merge = game.connect_entities(
        nbelt_start, nbelt_midpoint.position, Prototype.TransportBelt
    )

    assert len(merge.inputs) == 2
    assert len(merge.outputs) == 1


def test_merge_multiple_belts(game):
    # Use available transport belts to route iron plates from furnaces to a central location:
    belt_start_position = Position(x=0.0, y=0.0)  # Position near the first furnace
    belt_end_position = Position(x=10.0, y=0.0)  # Position leading to an assembly area
    belts = game.connect_entities(
        belt_start_position, belt_end_position, Prototype.TransportBelt
    )

    game.move_to(Position(x=0.0, y=0.0))
    nbelt_start = Position(x=5.0, y=5.0)
    nbelt_midpoint = belts.belts[len(belts.belts) // 2]
    merge = game.connect_entities(nbelt_start, nbelt_midpoint, Prototype.TransportBelt)

    game.move_to(Position(x=0.0, y=0.0))
    nbelt_start = Position(x=5.0, y=-5.0)
    nbelt_midpoint = belts.belts[len(belts.belts) // 2]
    merge = game.connect_entities(nbelt_start, nbelt_midpoint, Prototype.TransportBelt)

    assert len(merge.inputs) == 3
    assert len(merge.outputs) == 1


def test_multi_belt_join(game):
    iron_pos = game.nearest(Resource.IronOre)
    print(f"Found iron ore at {iron_pos}")

    # Place drills individually with smaller building boxes
    game.move_to(Position(x=15.5, y=70.5))
    drill1 = game.place_entity(
        Prototype.BurnerMiningDrill,
        position=Position(x=15.5, y=70.5),
        direction=Direction.LEFT,
    )
    print(f"placed drill at {drill1.position}")
    game.move_to(Position(x=11.5, y=69.5))
    drill2 = game.place_entity(
        Prototype.BurnerMiningDrill,
        position=Position(x=19.5, y=72.5),
        direction=Direction.LEFT,
    )
    print(f"placed drill at {drill2.position}")
    game.move_to(Position(x=22.5, y=75.5))
    drill3 = game.place_entity(
        Prototype.BurnerMiningDrill,
        position=Position(x=22.5, y=75.5),
        direction=Direction.LEFT,
    )
    print(f"placed drill at {drill3.position}")
    game.move_to(Position(x=-0.5, y=66.5))
    collection_chest = game.place_entity(
        Prototype.WoodenChest, position=Position(x=-0.5, y=66.5)
    )
    print(f"Placed collection chest at {collection_chest.position}")

    # Place inserter next to chest
    chest_inserter = game.place_entity_next_to(
        Prototype.BurnerInserter,
        reference_position=collection_chest.position,
        direction=Direction.LEFT,
        spacing=0,
    )
    # Rotate inserter to put items into chest
    chest_inserter = game.rotate_entity(chest_inserter, Direction.RIGHT)
    print(f"Placed chest inserter at {chest_inserter.position}")

    # Add fuel to inserter
    chest_inserter = game.insert_item(Prototype.Coal, chest_inserter, quantity=50)

    # Connect all drills to the inserter\'s pickup position using transport belts
    belts = game.connect_entities(
        drill3.drop_position, chest_inserter.pickup_position, Prototype.TransportBelt
    )
    print(f"Connected drill at {drill2.position} to collection")
    belts = game.connect_entities(drill1.drop_position, belts, Prototype.TransportBelt)
    print(f"Connected drill at {drill1.position} to collection system")
    belts = game.connect_entities(drill2.drop_position, belts, Prototype.TransportBelt)

    assert len(belts.belts) > 25


def test_ensure_final_belt_rotation_correct(game):
    iron_ore_loc = game.nearest(Resource.IronOre)
    print(f"found iron ore at {iron_ore_loc}")
    game.move_to(iron_ore_loc)
    print("Moved to iron ore location")
    furnace = game.place_entity(Prototype.StoneFurnace, position=iron_ore_loc)
    print(f"Placed a drill at location ({furnace.position}) and inserted coal")

    # put a inserter next to the furnace
    furnace_output_inserter = game.place_entity_next_to(
        Prototype.BurnerInserter, reference_position=furnace.position, spacing=0
    )
    # no need to rotate as inserter takes from furnace
    print(f"Placed inserter at {furnace_output_inserter.position} and inserted coal")

    chest_pos = Position(x=furnace.position.x - 9, y=furnace.position.y)
    game.move_to(chest_pos)
    chest = game.place_entity(Prototype.WoodenChest, position=chest_pos)
    print(f"Placed chest to pickup plates at ({chest.position})")

    belts = game.connect_entities(
        furnace_output_inserter.drop_position,
        chest.position.right(1),
        Prototype.TransportBelt,
    )
    print(
        f"Connected furnace_output_inserter at {furnace_output_inserter.position} to chest at {chest.position} with belts {belts}"
    )
    assert len(belts.belts) > 10
    assert True, "Could not create belt"


def test_connect_furnace(game):
    furnace = game.place_entity(Prototype.StoneFurnace, position=Position(x=2, y=0))
    try:
        game.connect_entities(
            Position(x=0, y=0), furnace.position, Prototype.TransportBelt
        )
        assert False, (
            "Should not be able to connect here, as it is blocked by the furnace"
        )
    except:
        assert True


def test_failure_to_connect_furnace(game):
    furnace = game.place_entity(Prototype.StoneFurnace, position=Position(x=2, y=0))
    try:
        game.connect_entities(Position(x=0, y=-10), furnace, Prototype.TransportBelt)
        assert False, (
            "Should not be able to connect here, as it is blocked by the furnace"
        )
    except Exception:
        assert True
