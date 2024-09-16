import pytest

from factorio_entities import Position
from factorio_instance import Direction
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        'boiler': 1,
        'transport-belt': 1,
        'stone-furnace': 1,
        'burner-mining-drill': 1,
        'burner-inserter': 2,
        'electric-mining-drill': 1,
        'assembling-machine-1': 1,
        'steam-engine': 1,
        'pipe': 1,
        'offshore-pump': 1,
    }
    instance.reset()
    yield instance

@pytest.fixture
def entity_prototype():
    return Prototype.Boiler

@pytest.fixture
def surrounding_entity_prototype():
    return Prototype.TransportBelt


def calculate_expected_position(ref_pos, direction, spacing, ref_entity, entity_to_place):
    ref_dimensions = ref_entity.tile_dimensions
    entity_dimensions = entity_to_place.tile_dimensions

    def align_to_grid(pos):
        return Position(x=round(pos.x * 2) / 2, y=round(pos.y * 2) / 2)

    def should_have_y_offset(entity):
        return entity.tile_dimensions.tile_width % 2 == 1

    y_offset = 0.5 if should_have_y_offset(entity_to_place) else 0

    if direction == Direction.RIGHT:
        return align_to_grid(Position(x=ref_pos.x + ref_dimensions.tile_width / 2 + entity_dimensions.tile_width / 2 + spacing, y=ref_pos.y + y_offset))
    elif direction == Direction.DOWN:
        return align_to_grid(Position(x=ref_pos.x, y=ref_pos.y + ref_dimensions.tile_height / 2 + entity_dimensions.tile_height / 2 + spacing + y_offset))
    elif direction == Direction.LEFT:
        return align_to_grid(Position(x=ref_pos.x - ref_dimensions.tile_width / 2 - entity_dimensions.tile_width / 2 - spacing, y=ref_pos.y + y_offset))
    elif direction == Direction.UP:
        return align_to_grid(Position(x=ref_pos.x, y=ref_pos.y - ref_dimensions.tile_height / 2 - entity_dimensions.tile_height / 2 - spacing + y_offset))


def test_place_entities_of_different_sizes(game):
    entity_pairs = [
        (Prototype.SteamEngine, Prototype.Pipe),
        (Prototype.AssemblingMachine1, Prototype.BurnerInserter),
        (Prototype.Boiler, Prototype.TransportBelt),
        (Prototype.Boiler, Prototype.AssemblingMachine1),
        (Prototype.ElectricMiningDrill, Prototype.StoneFurnace),
    ]

    for ref_proto, placed_proto in entity_pairs:

        if ref_proto != Prototype.OffshorePump:
            starting_position = game.nearest(Resource.IronOre)
        else:
            starting_position = game.nearest(Resource.Water)
        nearby_position = Position(x=starting_position.x + 1, y=starting_position.y - 1)
        game.move_to(nearby_position)

        for direction in [Direction.RIGHT, Direction.DOWN, Direction.LEFT, Direction.UP]:

            for spacing in range(3):
                ref_entity = game.place_entity(ref_proto, position=starting_position)
                placed_entity = game.place_entity_next_to(placed_proto, ref_entity.position, direction, spacing)

                expected_position = calculate_expected_position(ref_entity.position, direction, spacing, ref_entity,
                                                                placed_entity)
                assert placed_entity.position.is_close(expected_position, tolerance=1), \
                    f"Misplacement: {ref_proto.value[0]} -> {placed_proto.value[0]}, " \
                    f"Direction: {direction}, Spacing: {spacing}, " \
                    f"Expected: {expected_position}, Got: {placed_entity.position}"

                # Check direction unless we are dealing with a pipe, which has no direction
                if placed_proto != Prototype.Pipe:
                    assert placed_entity.direction == direction.value, f"Expected direction {direction}, got {placed_entity.direction}"

                game.reset()
                game.move_to(nearby_position)


def test_place_pipe_next_to_offshore_pump(game):
    ref_proto = Prototype.OffshorePump
    placed_proto = Prototype.Pipe

    starting_position = game.nearest(Resource.Water)
    nearby_position = Position(x=starting_position.x + 1, y=starting_position.y - 1)
    game.move_to(nearby_position)

    for direction in [Direction.RIGHT, Direction.DOWN, Direction.UP]:

        for spacing in range(3):
            ref_entity = game.place_entity(ref_proto, position=starting_position)
            placed_entity = game.place_entity_next_to(placed_proto, ref_entity.position, direction, spacing)

            expected_position = calculate_expected_position(ref_entity.position, direction, spacing, ref_entity,
                                                            placed_entity)
            assert placed_entity.position.is_close(expected_position, tolerance=1), \
                f"Misplacement: {ref_proto.value[0]} -> {placed_proto.value[0]}, " \
                f"Direction: {direction}, Spacing: {spacing}, " \
                f"Expected: {expected_position}, Got: {placed_entity.position}"

            # Check direction unless we are dealing with a pipe, which has no direction
            if placed_proto != Prototype.Pipe:
                assert placed_entity.direction == direction.value, f"Expected direction {direction}, got {placed_entity.direction}"

            game.reset()
            game.move_to(nearby_position)

def test_place_drill_and_furnace_next_to_iron_ore(game):
    iron_position = game.nearest(Resource.IronOre)
    game.move_to(iron_position)
    entity = game.place_entity(Prototype.BurnerMiningDrill, position=iron_position, direction=Direction.DOWN)
    print(f"Burner Mining Drill position: {entity.position}")
    print(f"Burner Mining Drill dimensions: {entity.tile_dimensions}")

    furnace = game.place_entity_next_to(Prototype.StoneFurnace, reference_position=entity.position,
                                        direction=Direction.DOWN)
    print(f"Stone Furnace position: {furnace.position}")

    expected_position = calculate_expected_position(entity.position, Direction.DOWN, 0, entity, furnace)
    print(f"Expected position: {expected_position}")

    assert furnace.position == expected_position, f"Expected {expected_position}, got {furnace.position}"
    game.reset()


def test_place_entity_next_to(game, entity_prototype, surrounding_entity_prototype):
    for spacing in range(0, 3):  # Test with spacings 0, 1, and 2
        entity = game.place_entity(entity_prototype, position=Position(x=0, y=0))
        assert entity
        print(f"\nReference entity: {entity_prototype.value[0]}")
        print(f"Reference entity position: {entity.position}")
        print(f"Reference entity dimensions: {entity.tile_dimensions}")

        directions = [Direction.RIGHT, Direction.DOWN, Direction.LEFT, Direction.UP]
        tolerance = 0.5

        for direction in directions:
            surrounding_entity = game.place_entity_next_to(surrounding_entity_prototype,
                                                           reference_position=entity.position,
                                                           direction=direction,
                                                           spacing=spacing)
            assert surrounding_entity, f"Failed to place entity in direction {direction} with spacing {spacing}"
            print(f"\nDirection: {direction}, Spacing: {spacing}")
            print(f"Placed entity: {surrounding_entity_prototype.value[0]}")
            print(f"Placed entity position: {surrounding_entity.position}")
            print(f"Placed entity dimensions: {surrounding_entity.tile_dimensions}")

            expected_position = calculate_expected_position(entity.position, direction, spacing,
                                                            entity, surrounding_entity)
            print(f"Expected position: {expected_position}")
            x_diff = surrounding_entity.position.x - expected_position.x
            y_diff = surrounding_entity.position.y - expected_position.y
            print(f"Difference: x={x_diff}, y={y_diff}")

            try:
                assert abs(x_diff) <= tolerance and abs(y_diff) <= tolerance, \
                    f"Entity not in expected position for direction {direction} with spacing {spacing}. " \
                    f"Expected {expected_position}, got {surrounding_entity.position}. " \
                    f"Difference: x={x_diff}, y={y_diff}"
            except AssertionError as e:
                print(f"Assertion failed: {str(e)}")
                print(f"Calculated position details:")
                print(f"  Direction: {direction}")
                print(f"  Spacing: {spacing}")
                raise

        game.reset()

    # Specific test for boiler and transport belt
    boiler = game.place_entity(Prototype.Boiler, position=Position(x=0, y=0))
    print(f"\nBoiler position: {boiler.position}")
    print(f"Boiler dimensions: {boiler.tile_dimensions}")

    belt = game.place_entity_next_to(Prototype.TransportBelt, reference_position=boiler.position,
                                     direction=Direction.RIGHT, spacing=0)
    print(f"Transport belt position: {belt.position}")
    print(f"Transport belt dimensions: {belt.tile_dimensions}")

    expected_belt_position = calculate_expected_position(boiler.position, Direction.RIGHT, 0, boiler, belt)
    print(f"Expected belt position: {expected_belt_position}")
    x_diff = belt.position.x - expected_belt_position.x
    y_diff = belt.position.y - expected_belt_position.y
    print(f"Difference: x={x_diff}, y={y_diff}")

    assert abs(x_diff) <= tolerance and abs(y_diff) <= tolerance, \
        f"Transport belt not in expected position. Expected {expected_belt_position}, got {belt.position}. " \
        f"Difference: x={x_diff}, y={y_diff}"