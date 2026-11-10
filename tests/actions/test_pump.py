import pytest

from fle.env.entities import Direction, Position
from fle.env.game_types import Prototype


@pytest.fixture()
def game(configure_game):
    return configure_game(inventory={"pump": 2}, reset_position=True)


def test_place_pump_serializes_input_and_output(game):
    pumps_before = game.inspect_inventory()[Prototype.Pump]
    pump = game.place_entity(
        Prototype.Pump, direction=Direction.UP, position=Position(x=0, y=3)
    )

    assert game.inspect_inventory()[Prototype.Pump] == pumps_before - 1
    # A north-facing pump takes fluid in from the south and pushes it north
    assert pump.input_position.y > pump.position.y
    assert pump.output_position.y < pump.position.y
    assert pump.input_position.x == pump.output_position.x


def test_get_entities_returns_placed_pump(game):
    game.place_entity(
        Prototype.Pump, direction=Direction.UP, position=Position(x=0, y=3)
    )

    pumps = game.get_entities({Prototype.Pump})
    assert len(pumps) == 1
    assert game.get_entity(Prototype.Pump, pumps[0].position).name == "pump"
