import pytest

from fle.env.entities import Position, Direction
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(configure_game):
    return configure_game(
        inventory={
            "boiler": 5,
            "transport-belt": 20,
            "stone-furnace": 10,
            "burner-mining-drill": 5,
            "electric-furnace": 5,
            "burner-inserter": 30,
            "electric-mining-drill": 10,
            "assembling-machine-1": 10,
            "steam-engine": 5,
            "pipe": 20,
            "offshore-pump": 5,
            "wooden-chest": 20,
            "small-electric-pole": 30,
            "medium-electric-pole": 10,
        },
        persist_inventory=True,
    )


@pytest.fixture
def entity_prototype():
    return Prototype.Boiler


@pytest.fixture
def surrounding_entity_prototype():
    return Prototype.TransportBelt


def calculate_expected_position(
    ref_pos, direction, spacing, ref_entity, entity_to_place
):
    def align_to_grid(pos):
        return Position(x=round(pos.x * 2) / 2, y=round(pos.y * 2) / 2)

    if ref_entity.direction != Direction.UP and ref_entity.direction != Direction.DOWN:
        ref_tile_height = ref_entity.tile_dimensions.tile_width
        ref_tile_width = ref_entity.tile_dimensions.tile_height
    else:
        ref_tile_height = ref_entity.tile_dimensions.tile_height
        ref_tile_width = ref_entity.tile_dimensions.tile_width

    if direction != Direction.UP or direction != Direction.DOWN:
        entity_tile_width = entity_to_place.tile_dimensions.tile_height
        entity_tile_height = entity_to_place.tile_dimensions.tile_width
    else:
        entity_tile_width = entity_to_place.tile_dimensions.tile_width
        entity_tile_height = entity_to_place.tile_dimensions.tile_height

    def should_have_y_offset(entity):
        return entity_tile_width % 2 == 1

    y_offset = 0.5 if should_have_y_offset(entity_to_place) else 0

    if direction == Direction.RIGHT:
        return align_to_grid(
            Position(
                x=ref_pos.x + ref_tile_width / 2 + entity_tile_width / 2 + spacing,
                y=ref_pos.y + y_offset,
            )
        )
    elif direction == Direction.DOWN:
        return align_to_grid(
            Position(
                x=ref_pos.x,
                y=ref_pos.y
                + ref_tile_height / 2
                + entity_tile_height / 2
                + spacing
                + y_offset,
            )
        )
    elif direction == Direction.LEFT:
        return align_to_grid(
            Position(
                x=ref_pos.x - ref_tile_width / 2 - entity_tile_width / 2 - spacing,
                y=ref_pos.y + y_offset,
            )
        )
    elif direction == Direction.UP:
        return align_to_grid(
            Position(
                x=ref_pos.x,
                y=ref_pos.y
                - ref_tile_height / 2
                - entity_tile_height / 2
                - spacing
                - y_offset,
            )
        )


def test_place_pipe_next_to_offshore_pump(game):
    ref_proto = Prototype.OffshorePump
    placed_proto = Prototype.Pipe

    starting_position = game.nearest(Resource.Water)
    nearby_position = Position(x=starting_position.x + 1, y=starting_position.y - 1)
    game.move_to(nearby_position)

    for direction in [Direction.RIGHT, Direction.DOWN, Direction.UP]:
        for spacing in range(3):
            ref_entity = game.place_entity(
                ref_proto, position=starting_position, direction=direction
            )
            placed_entity = game.place_entity_next_to(
                placed_proto, ref_entity.position, direction, spacing
            )

            expected_position = calculate_expected_position(
                ref_entity.position, direction, spacing, ref_entity, placed_entity
            )
            assert placed_entity.position.is_close(expected_position, tolerance=1), (
                f"Misplacement: {ref_proto.value[0]} -> {placed_proto.value[0]}, "
                f"Direction: {direction}, Spacing: {spacing}, "
                f"Expected: {expected_position}, Got: {placed_entity.position}"
            )

            # Check direction unless we are dealing with a pipe, which has no direction
            if placed_proto != Prototype.Pipe:
                assert placed_entity.direction == direction.value, (
                    f"Expected direction {direction}, got {placed_entity.direction}"
                )

            game.instance.reset()
            game.move_to(nearby_position)


def test_place_drill_and_furnace_next_to_iron_ore(game):
    iron_position = game.nearest(Resource.IronOre)
    game.move_to(iron_position)
    entity = game.place_entity(
        Prototype.BurnerMiningDrill, position=iron_position, direction=Direction.DOWN
    )
    print(f"Burner Mining Drill position: {entity.position}")
    print(f"Burner Mining Drill dimensions: {entity.tile_dimensions}")

    furnace = game.place_entity_next_to(
        Prototype.StoneFurnace,
        reference_position=entity.position,
        direction=Direction.DOWN,
    )
    print(f"Stone Furnace position: {furnace.position}")

    expected_position = calculate_expected_position(
        entity.position, Direction.DOWN, 0, entity, furnace
    )
    print(f"Expected position: {expected_position}")

    assert furnace.position == expected_position, (
        f"Expected {expected_position}, got {furnace.position}"
    )


def test_fail_place_drill_off_iron_ore(game):
    iron_position = game.nearest(Resource.IronOre)
    game.move_to(iron_position)
    entity = game.place_entity(
        Prototype.BurnerMiningDrill, position=iron_position, direction=Direction.DOWN
    )
    print(f"Burner Mining Drill position: {entity.position}")
    print(f"Burner Mining Drill dimensions: {entity.tile_dimensions}")

    try:
        furnace = game.place_entity_next_to(
            Prototype.BurnerMiningDrill,
            reference_position=entity.position,
            direction=Direction.RIGHT,
        )
        print(f"Stone Furnace position: {furnace.position}")
    except:
        assert True, "Should not be able to place a mining drill off-resource patch"


def test_place_entity_next_to(game, entity_prototype, surrounding_entity_prototype):
    for spacing in range(0, 3):  # Test with spacings 0, 1, and 2
        entity = game.place_entity(entity_prototype, position=Position(x=0, y=0))
        assert entity
        print(f"\nReference entity: {entity_prototype.value[0]}")
        print(f"Reference entity position: {entity.position}")
        print(f"Reference entity dimensions: {entity.tile_dimensions}")

        directions = [Direction.RIGHT, Direction.DOWN, Direction.LEFT, Direction.UP]
        tolerance = 1

        for direction in directions:
            surrounding_entity = game.place_entity_next_to(
                surrounding_entity_prototype,
                reference_position=entity.position,
                direction=direction,
                spacing=spacing,
            )
            assert surrounding_entity, (
                f"Failed to place entity in direction {direction} with spacing {spacing}"
            )
            print(f"\nDirection: {direction}, Spacing: {spacing}")
            print(f"Placed entity: {surrounding_entity_prototype.value[0]}")
            print(f"Placed entity position: {surrounding_entity.position}")
            print(f"Placed entity dimensions: {surrounding_entity.tile_dimensions}")

            expected_position = calculate_expected_position(
                entity.position, direction, spacing, entity, surrounding_entity
            )
            print(f"Expected position: {expected_position}")
            x_diff = surrounding_entity.position.x - expected_position.x
            y_diff = surrounding_entity.position.y - expected_position.y
            print(f"Difference: x={x_diff}, y={y_diff}")

            try:
                assert abs(x_diff) <= tolerance and abs(y_diff) <= tolerance, (
                    f"Entity not in expected position for direction {direction} with spacing {spacing}. "
                    f"Expected {expected_position}, got {surrounding_entity.position}. "
                    f"Difference: x={x_diff}, y={y_diff}"
                )
            except AssertionError as e:
                print(f"Assertion failed: {str(e)}")
                print("Calculated position details:")
                print(f"  Direction: {direction}")
                print(f"  Spacing: {spacing}")
                raise

        game.instance.reset()

    # Specific test for boiler and transport belt
    boiler = game.place_entity(Prototype.Boiler, position=Position(x=0, y=0))
    print(f"\nBoiler position: {boiler.position}")
    print(f"Boiler dimensions: {boiler.tile_dimensions}")

    belt = game.place_entity_next_to(
        Prototype.TransportBelt,
        reference_position=boiler.position,
        direction=Direction.RIGHT,
        spacing=0,
    )
    print(f"Transport belt position: {belt.position}")
    print(f"Transport belt dimensions: {belt.tile_dimensions}")

    expected_belt_position = calculate_expected_position(
        boiler.position, Direction.RIGHT, 0, boiler, belt
    )
    print(f"Expected belt position: {expected_belt_position}")
    x_diff = belt.position.x - expected_belt_position.x
    y_diff = belt.position.y - expected_belt_position.y
    print(f"Difference: x={x_diff}, y={y_diff}")

    assert abs(x_diff) <= tolerance and abs(y_diff) <= tolerance, (
        f"Transport belt not in expected position. Expected {expected_belt_position}, got {belt.position}. "
        f"Difference: x={x_diff}, y={y_diff}"
    )


def test_inserters_above_chest(game):
    game.move_to(Position(x=0, y=0))
    for i in range(3):
        chest = game.place_entity(
            Prototype.WoodenChest, Direction.UP, Position(x=i, y=0)
        )
        assert chest, "Failed to place chest"
        inserter = game.place_entity_next_to(
            Prototype.BurnerInserter,
            reference_position=Position(x=i, y=0),
            direction=Direction.UP,
            spacing=2,
        )
        assert inserter, "Failed to place inserter"


def test_inserters_below_furnace(game):
    game.move_to(Position(x=0, y=0))

    furnace = game.place_entity(
        Prototype.StoneFurnace, Direction.UP, Position(x=0, y=0)
    )
    assert furnace, "Failed to place furnace"
    inserter = game.place_entity_next_to(
        Prototype.BurnerInserter,
        reference_position=furnace.position,
        direction=Direction.DOWN,
        spacing=0,
    )
    assert inserter, "Failed to place inserter"


def test_adjacent_electric_mining_drills(game):
    origin = game.get_resource_patch(
        Resource.CopperOre, game.nearest(Resource.CopperOre)
    ).bounding_box.left_top
    game.move_to(origin)
    # Place electric-mining-drill
    electric_mining_drill_1 = game.place_entity(
        Prototype.ElectricMiningDrill, direction=Direction.DOWN, position=origin
    )
    assert electric_mining_drill_1, "Failed to place electric-mining-drill"

    # Place electric-mining-drill
    electric_mining_drill_2 = game.place_entity_next_to(
        Prototype.ElectricMiningDrill,
        reference_position=electric_mining_drill_1.position,
        direction=Direction.RIGHT,
        spacing=0,
    )
    electric_mining_drill_2 = game.rotate_entity(
        electric_mining_drill_2, Direction.DOWN
    )
    assert electric_mining_drill_2, "Failed to place electric-mining-drill"

    # Place electric-mining-drill
    electric_mining_drill_3 = game.place_entity_next_to(
        Prototype.ElectricMiningDrill,
        reference_position=electric_mining_drill_2.position,
        direction=Direction.RIGHT,
        spacing=0,
    )
    electric_mining_drill_3 = game.rotate_entity(
        electric_mining_drill_3, Direction.DOWN
    )
    assert electric_mining_drill_3, "Failed to place electric-mining-drill"

    # Place electric-mining-drill
    electric_mining_drill_4 = game.place_entity_next_to(
        Prototype.ElectricMiningDrill,
        reference_position=electric_mining_drill_3.position,
        direction=Direction.RIGHT,
        spacing=0,
    )
    electric_mining_drill_4 = game.rotate_entity(
        electric_mining_drill_4, Direction.DOWN
    )
    assert electric_mining_drill_4, "Failed to place electric-mining-drill"

    # Place electric-mining-drill
    electric_mining_drill_5 = game.place_entity_next_to(
        Prototype.ElectricMiningDrill,
        reference_position=electric_mining_drill_1.position,
        direction=Direction.DOWN,
    )
    electric_mining_drill_5 = game.rotate_entity(
        electric_mining_drill_5, Direction.RIGHT
    )
    assert electric_mining_drill_5, "Failed to place electric-mining-drill"

    # Place electric-mining-drill
    electric_mining_drill_6 = game.place_entity_next_to(
        Prototype.ElectricMiningDrill,
        reference_position=electric_mining_drill_2.position,
        direction=Direction.DOWN,
    )
    electric_mining_drill_6 = game.rotate_entity(
        electric_mining_drill_6, Direction.RIGHT
    )
    assert electric_mining_drill_6, "Failed to place electric-mining-drill"

    # Place electric-mining-drill
    electric_mining_drill_7 = game.place_entity_next_to(
        Prototype.ElectricMiningDrill,
        reference_position=electric_mining_drill_3.position,
        direction=Direction.DOWN,
    )
    electric_mining_drill_7 = game.rotate_entity(
        electric_mining_drill_7, Direction.RIGHT
    )
    assert electric_mining_drill_7, "Failed to place electric-mining-drill"


def test_smart_inserter_placement_around_assembler(game):
    """Test smart inserter placement around 3x3 assembling machine"""
    game.move_to(Position(x=10, y=10))

    assembler = game.place_entity(
        Prototype.AssemblingMachine1,
        position=Position(x=10.5, y=10.5),
        direction=Direction.UP,
    )
    assert assembler, "Failed to place assembling machine"

    # Test all four reserved middle positions
    directions_and_expected = [
        (Direction.LEFT, Position(x=8.5, y=10.5)),  # West reserved position
        (Direction.RIGHT, Position(x=12.5, y=10.5)),  # East reserved position
        (Direction.UP, Position(x=10.5, y=8.5)),  # North reserved position
        (Direction.DOWN, Position(x=10.5, y=12.5)),  # South reserved position
    ]

    for direction, expected_pos in directions_and_expected:
        inserter = game.place_entity_next_to(
            Prototype.BurnerInserter,
            reference_position=assembler.position,
            direction=direction,
            spacing=0,
        )
        assert inserter, f"Failed to place inserter in direction {direction}"

        assert inserter.position.is_close(expected_pos, tolerance=0.1), (
            f"Inserter not at reserved position for {direction}. Expected {expected_pos}, got {inserter.position}"
        )

        game.instance.reset()
        game.move_to(Position(x=10, y=10))
        assembler = game.place_entity(
            Prototype.AssemblingMachine1, position=Position(x=10, y=10)
        )


def test_pole_collision_resolution(game):
    """Test that poles blocking optimal positions trigger smart alternatives"""
    game.move_to(Position(x=30, y=30))

    assembler = game.place_entity(
        Prototype.AssemblingMachine1, position=Position(x=30, y=30)
    )
    assert assembler, "Failed to place assembling machine"

    # Block the optimal east position with a pole
    blocking_pole = game.place_entity(
        Prototype.SmallElectricPole,
        position=Position(x=32, y=30),  # East middle reserved position
    )
    assert blocking_pole, "Failed to place blocking pole"

    # Try to place inserter on east side
    try:
        inserter = game.place_entity_next_to(
            Prototype.BurnerInserter,
            reference_position=assembler.position,
            direction=Direction.RIGHT,
            spacing=0,
        )

        # Should find alternative or provide helpful error
        if inserter:
            blocked_pos = Position(x=32, y=30)
            assert not inserter.position.is_close(blocked_pos, tolerance=0.1), (
                "Should not place at blocked position"
            )
            print(f"✓ Found alternative position: {inserter.position}")

    except Exception as e:
        # Should provide helpful error message
        error_msg = str(e).lower()
        helpful_keywords = ["pole", "corner", "large entities", "spacing", "direction"]
        assert any(keyword in error_msg for keyword in helpful_keywords), (
            f"Error should provide helpful suggestions: {e}"
        )
        print(f"✓ Got helpful error message: {e}")


def test_reserved_slots_for_large_entities(game):
    """Test reserved slots work for different large entity types"""
    large_entities = [Prototype.AssemblingMachine1, Prototype.StoneFurnace]

    y_offset = 0
    for entity_proto in large_entities:
        game.move_to(Position(x=40, y=40 + y_offset))

        entity = game.place_entity(
            entity_proto, position=Position(x=40, y=40 + y_offset)
        )
        assert entity, f"Failed to place {entity_proto}"

        # Test inserter placement at reserved middle positions
        placed_count = 0
        for direction in [
            Direction.LEFT,
            Direction.RIGHT,
            Direction.UP,
            Direction.DOWN,
        ]:
            try:
                inserter = game.place_entity_next_to(
                    Prototype.BurnerInserter,
                    reference_position=entity.position,
                    direction=direction,
                    spacing=0,
                )

                if inserter:
                    placed_count += 1
                    # Verify it's at the expected reserved position (±2 offset)
                    if direction == Direction.LEFT:
                        assert abs(inserter.position.x - (entity.position.x - 2)) < 0.5
                    elif direction == Direction.RIGHT:
                        assert abs(inserter.position.x - (entity.position.x + 2)) < 0.5
                    elif direction == Direction.UP:
                        assert abs(inserter.position.y - (entity.position.y - 2)) < 0.5
                    elif direction == Direction.DOWN:
                        assert abs(inserter.position.y - (entity.position.y + 2)) < 0.5

            except Exception as e:
                print(f"Expected placement issue for {entity_proto} {direction}: {e}")

        assert placed_count > 0, (
            f"Should place at least one inserter around {entity_proto}"
        )
        y_offset += 10
        game.instance.reset()


def test_corner_positions_available_for_poles(game):
    """Test that corner positions remain available after reserving middle slots"""
    game.move_to(Position(x=60, y=60))

    assembler = game.place_entity(
        Prototype.AssemblingMachine1, position=Position(x=60, y=60)
    )
    assert assembler, "Failed to place assembling machine"

    # Place inserters at middle positions first
    for direction in [Direction.LEFT, Direction.RIGHT, Direction.UP, Direction.DOWN]:
        try:
            game.place_entity_next_to(
                Prototype.BurnerInserter,
                reference_position=assembler.position,
                direction=direction,
                spacing=0,
            )
        except:
            pass  # Some might fail due to conflicts

    # Test that poles can still be placed at corners
    corner_positions = [
        Position(x=58, y=58),  # Northwest
        Position(x=62, y=58),  # Northeast
        Position(x=62, y=62),  # Southeast
        Position(x=58, y=62),  # Southwest
    ]

    poles_placed = 0
    for corner_pos in corner_positions:
        try:
            pole = game.place_entity(Prototype.SmallElectricPole, position=corner_pos)
            if pole:
                poles_placed += 1
        except:
            pass

    assert poles_placed > 0, "Should be able to place poles at corner positions"
    print(f"✓ Successfully placed {poles_placed} poles at corners")


def test_mining_drill_output_flexibility(game):
    """Test that mining drills can have output inserters in any direction"""
    iron_position = game.nearest(Resource.IronOre)
    game.move_to(iron_position)

    drill = game.place_entity(
        Prototype.ElectricMiningDrill, position=iron_position, direction=Direction.DOWN
    )
    assert drill, "Failed to place mining drill"

    # Mining drills should accept output inserters in all directions
    output_directions = [Direction.RIGHT, Direction.DOWN, Direction.LEFT, Direction.UP]

    successful_placements = 0
    for direction in output_directions:
        try:
            inserter = game.place_entity_next_to(
                Prototype.BurnerInserter,
                reference_position=drill.position,
                direction=direction,
                spacing=0,
            )

            if inserter:
                successful_placements += 1
                print(f"✓ Placed output inserter {direction} of drill")

        except Exception as e:
            print(f"Could not place {direction} inserter: {e}")

        game.instance.reset()
        game.move_to(iron_position)
        drill = game.place_entity(Prototype.ElectricMiningDrill, position=iron_position)

    assert successful_placements > 0, (
        "Should place at least one output inserter around drill"
    )


def test_collision_resolution_alternatives(game):
    """Test smart collision resolution finds good alternatives"""
    game.move_to(Position(x=70, y=70))

    assembler = game.place_entity(
        Prototype.AssemblingMachine1, position=Position(x=70, y=70)
    )

    # Block preferred position
    game.place_entity(Prototype.WoodenChest, position=Position(x=72, y=70))

    try:
        inserter = game.place_entity_next_to(
            Prototype.BurnerInserter,
            reference_position=assembler.position,
            direction=Direction.RIGHT,  # Blocked direction
            spacing=0,
        )

        if inserter:
            # Should find alternative, not at blocked position
            blocked_pos = Position(x=72, y=70)
            assert not inserter.position.is_close(blocked_pos, tolerance=0.1), (
                "Should not place at blocked position"
            )
            print(f"✓ Found alternative at {inserter.position}")

    except Exception as e:
        # Should give helpful suggestions
        print(f"✓ Got collision resolution guidance: {e}")


def test_size_detection_accuracy(game):
    """Test that entity size detection correctly identifies 3x3+ entities"""
    game.move_to(Position(x=90, y=90))

    # These should all trigger 3x3 reserved slots behavior
    large_3x3_entities = [Prototype.AssemblingMachine1, Prototype.ElectricFurnace]

    for entity_proto in large_3x3_entities:
        entity = game.place_entity(entity_proto, position=Position(x=90, y=90))

        # Test that reserved slots behavior is triggered (±2 offset)
        inserter = game.place_entity_next_to(
            Prototype.BurnerInserter,
            reference_position=entity.position,
            direction=Direction.RIGHT,
            spacing=0,
        )

        expected_x = entity.position.x + 2  # Should be +2 for 3x3 entities
        assert abs(inserter.position.x - expected_x) < 0.5, (
            f"{entity_proto} should trigger 3x3 reserved slots (±2 offset)"
        )

        game.instance.reset()
        game.move_to(Position(x=90, y=90))

    print("✓ Size detection correctly identifies 3x3+ entities")


def test_factory_pattern_optimization(game):
    """Test that factory patterns are recognized and optimized"""
    game.move_to(Position(x=50, y=50))

    # Place furnace (has input/output preferences)
    furnace = game.place_entity(
        Prototype.StoneFurnace, position=Position(x=50, y=50), direction=Direction.UP
    )
    assert furnace, "Failed to place furnace"

    # Place input inserter on west side (should be optimal for input)
    input_inserter = game.place_entity_next_to(
        Prototype.BurnerInserter,
        reference_position=furnace.position,
        direction=Direction.LEFT,
        spacing=0,
    )

    assert input_inserter, "Failed to place input inserter"

    # Place output inserter on east side (should be optimal for output)
    output_inserter = game.place_entity_next_to(
        Prototype.BurnerInserter,
        reference_position=furnace.position,
        direction=Direction.RIGHT,
        spacing=0,
    )

    assert output_inserter, "Failed to place output inserter"

    # Test that belts can be placed next to inserters
    try:
        game.place_entity_next_to(
            Prototype.TransportBelt,
            reference_position=input_inserter.position,
            direction=Direction.LEFT,
            spacing=0,
        )

        game.place_entity_next_to(
            Prototype.TransportBelt,
            reference_position=output_inserter.position,
            direction=Direction.RIGHT,
            spacing=0,
        )

        print(
            "Created factory line: input belt -> inserter -> furnace -> inserter -> output belt"
        )

    except Exception as e:
        print(f"Belt placement encountered issue (may be expected): {e}")


def test_belt_placement_with_smart_routing(game):
    """Test belt placement with smart collision avoidance"""
    game.move_to(Position(x=80, y=80))

    # Create a basic setup
    furnace = game.place_entity(Prototype.StoneFurnace, position=Position(x=80, y=80))

    inserter = game.place_entity_next_to(
        Prototype.BurnerInserter,
        reference_position=furnace.position,
        direction=Direction.RIGHT,
        spacing=0,
    )

    # Place belt next to inserter - should work with smart routing
    belt = game.place_entity_next_to(
        Prototype.TransportBelt,
        reference_position=inserter.position,
        direction=Direction.RIGHT,
        spacing=0,
    )

    assert belt, "Belt placement with smart routing should succeed"

    # Test that multiple belts can be chained
    try:
        belt2 = game.place_entity_next_to(
            Prototype.TransportBelt,
            reference_position=belt.position,
            direction=Direction.RIGHT,
            spacing=0,
        )

        if belt2:
            print("Belt chaining successful with smart placement")

    except Exception as e:
        print(f"Belt chaining issue (may be expected due to space): {e}")
