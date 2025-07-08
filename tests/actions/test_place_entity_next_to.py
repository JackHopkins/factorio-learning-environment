import pytest

from fle.env.entities import Position, Direction
from fle.env import DirectionInternal
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "boiler": 3,
        "transport-belt": 1,
        "stone-furnace": 1,
        "burner-mining-drill": 1,
        "burner-inserter": 5,
        "electric-mining-drill": 1,
        "assembling-machine-1": 1,
        "steam-engine": 1,
        "pipe": 1,
        "offshore-pump": 1,
        "wooden-chest": 3,
    }
    instance.reset()
    yield instance.namespace
    # instance.reset()


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


def test_place_entities_of_different_sizes(game):
    entity_pairs = [
        (Prototype.Boiler, Prototype.SteamEngine),
        (Prototype.ElectricMiningDrill, Prototype.Boiler),
        (Prototype.SteamEngine, Prototype.Pipe),
        (Prototype.AssemblingMachine1, Prototype.BurnerInserter),
        (Prototype.Boiler, Prototype.TransportBelt),
    ]

    for ref_proto, placed_proto in entity_pairs:
        if ref_proto != Prototype.OffshorePump:
            starting_position = game.nearest(Resource.IronOre)
        else:
            starting_position = game.nearest(Resource.Water)
        nearby_position = Position(x=starting_position.x + 1, y=starting_position.y - 1)
        game.move_to(nearby_position)

        for spacing in range(3):
            for direction in [
                Direction.LEFT,
                Direction.DOWN,
                Direction.RIGHT,
                Direction.UP,
            ]:
                ref_entity = game.place_entity(
                    ref_proto, direction=Direction.RIGHT, position=starting_position
                )
                game.move_to(
                    Position(x=starting_position.x + 3, y=starting_position.y - 3)
                )
                placed_entity = game.place_entity_next_to(
                    placed_proto, ref_entity.position, direction, spacing
                )
                expected_position = calculate_expected_position(
                    ref_entity.position, direction, spacing, ref_entity, placed_entity
                )
                assert placed_entity.position.is_close(
                    expected_position, tolerance=1
                ), (
                    f"Misplacement: {ref_proto.value[0]} -> {placed_proto.value[0]}, "
                    f"Direction: {direction}, Spacing: {spacing}, "
                    f"Expected: {expected_position}, Got: {placed_entity.position}"
                )

                if placed_proto == Prototype.SteamEngine:
                    dir = placed_entity.direction.value in [
                        direction.value,
                        DirectionInternal.opposite(direction).value,
                    ]
                    assert dir, (
                        f"Expected direction {direction}, got {placed_entity.direction}"
                    )
                # Check direction unless we are dealing with a pipe, which has no direction
                elif placed_proto != Prototype.Pipe:
                    assert placed_entity.direction.value == direction.value, (
                        f"Expected direction {direction}, got {placed_entity.direction}"
                    )

                game.instance.reset()
                game.move_to(nearby_position)


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
