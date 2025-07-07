import math

import pytest

from fle.env import Direction, EntityStatus
from fle.env.game_types import Resource, Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        "stone-furnace": 10,
        "burner-inserter": 50,
        "offshore-pump": 4,
        "pipe": 100,
        "small-electric-pole": 50,
        "transport-belt": 200,
        "coal": 100,
        "wooden-chest": 1,
        "assembling-machine-1": 10,
        "boiler": 3,
        "steam-engine": 3,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_connected_pump_is_working(game):
    game.move_to(game.nearest(Resource.Water))

    offshore_pump = game.place_entity(
        Prototype.OffshorePump,
        position=game.nearest(Resource.Water),
        direction=Direction.DOWN,
        exact=False,
    )
    assert offshore_pump.status == EntityStatus.NOT_CONNECTED

    boiler = game.place_entity_next_to(
        Prototype.Boiler,
        reference_position=offshore_pump.position,
        direction=offshore_pump.direction,
        spacing=5,
    )
    assert boiler.status == EntityStatus.NOT_CONNECTED

    assert boiler.direction.value == offshore_pump.direction.value
    water_pipes = game.connect_entities(
        boiler, offshore_pump, connection_type=Prototype.Pipe
    )
    assert len(water_pipes.pipes) >= math.ceil(
        5
        + boiler.tile_dimensions.tile_height / 2
        + offshore_pump.tile_dimensions.tile_height / 2
        + 1
    )
    boiler = game.get_entity(Prototype.Boiler, boiler.position)
    assert boiler.status == EntityStatus.NO_FUEL

    offshore_pump = game.get_entity(Prototype.OffshorePump, offshore_pump.position)
    assert offshore_pump.status == EntityStatus.WORKING

    pipes = game.get_entities({Prototype.Pipe})
    assert pipes[0].status == EntityStatus.FULL_OUTPUT


def test_not_connected_pump_is_not_connected(game):
    game.move_to(game.nearest(Resource.Water))

    offshore_pump = game.place_entity(
        Prototype.OffshorePump,
        position=game.nearest(Resource.Water),
        direction=Direction.DOWN,
        exact=False,
    )
    assert offshore_pump.status == EntityStatus.NOT_CONNECTED
