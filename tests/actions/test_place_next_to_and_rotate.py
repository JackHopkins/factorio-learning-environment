import pytest

from fle.env.entities import Position, Direction
from fle.env.game_types import Prototype, Resource
from fle.env import DirectionInternal


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "boiler": 1,
        "transport-belt": 1,
        "stone-furnace": 1,
        "burner-mining-drill": 1,
        "burner-inserter": 2,
        "electric-mining-drill": 1,
        "assembling-machine-1": 1,
        "steam-engine": 1,
        "pipe": 1,
        "offshore-pump": 1,
    }
    instance.reset()
    yield instance.namespace


def calculate_expected_position(
    ref_pos, direction, spacing, ref_entity, entity_to_place
):
    ref_dimensions = ref_entity.tile_dimensions
    entity_dimensions = entity_to_place.tile_dimensions

    def align_to_grid(pos):
        return Position(x=round(pos.x * 2) / 2, y=round(pos.y * 2) / 2)

    def should_have_y_offset(entity):
        return entity.tile_dimensions.tile_width % 2 == 1

    y_offset = 0.5 if should_have_y_offset(entity_to_place) else 0

    if direction == Direction.RIGHT:
        return align_to_grid(
            Position(
                x=ref_pos.x
                + ref_dimensions.tile_width / 2
                + entity_dimensions.tile_width / 2
                + spacing,
                y=ref_pos.y + y_offset,
            )
        )
    elif direction == Direction.DOWN:
        return align_to_grid(
            Position(
                x=ref_pos.x,
                y=ref_pos.y
                + ref_dimensions.tile_height / 2
                + entity_dimensions.tile_height / 2
                + spacing
                + y_offset,
            )
        )
    elif direction == Direction.LEFT:
        return align_to_grid(
            Position(
                x=ref_pos.x
                - ref_dimensions.tile_width / 2
                - entity_dimensions.tile_width / 2
                - spacing,
                y=ref_pos.y + y_offset,
            )
        )
    elif direction == Direction.UP:
        return align_to_grid(
            Position(
                x=ref_pos.x,
                y=ref_pos.y
                - ref_dimensions.tile_height / 2
                - entity_dimensions.tile_height / 2
                - spacing
                + y_offset,
            )
        )


def test_place_boiler_next_to_offshore_pump_rotate_and_connect(game):
    # move to the nearest water source
    water_location = game.nearest(Resource.Water)
    game.move_to(water_location)

    offshore_pump = game.place_entity(Prototype.OffshorePump, position=water_location)
    # Get offshore pump direction
    direction = Direction(offshore_pump.direction.value)

    # pump connection point
    offshore_pump.connection_points[0]

    # place the boiler next to the offshore pump
    boiler = game.place_entity_next_to(
        Prototype.Boiler,
        reference_position=offshore_pump.position,
        direction=direction,
        spacing=2,
    )

    # rotate the boiler to face the offshore pump
    boiler = game.rotate_entity(boiler, DirectionInternal.next_clockwise(direction))
