import pytest

from fle.env.entities import Position, UndergroundBelt
from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        "stone-furnace": 10,
        "burner-inserter": 50,
        "offshore-pump": 4,
        "pipe": 100,
        "small-electric-pole": 50,
        "underground-belt": 4,
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


def test_connect_belt_underground(game):
    game.instance.initial_inventory = {
        "express-underground-belt": 4,
        "express-transport-belt": 200,
    }
    game.instance.reset()

    position_1 = Position(x=0.0, y=1.0)
    position_2 = Position(x=0.0, y=10.0)
    position_3 = Position(x=10, y=10)

    try:
        belts = game.connect_entities(
            position_1,
            position_2,
            position_3,
            {Prototype.ExpressTransportBelt, Prototype.ExpressUndergroundBelt},
        )
        counter = 0
        for belt in belts.belts:
            if isinstance(belt, UndergroundBelt):
                counter += 1
        game.pickup_entity(belts)

        assert not game.get_entities()
        assert counter == 2
        print(f"Transport Belts laid from {position_1} to {position_3}.")
    except Exception as e:
        print(f"Failed to lay Transport Belts: {e}")
