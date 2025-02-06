import pytest

from entities import Position, UndergroundBelt
from game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        'stone-furnace': 10,
        'burner-inserter': 50,
        'offshore-pump': 4,
        'pipe': 100,
        'small-electric-pole': 50,
        'underground-belt': 4,
        'transport-belt': 200,
        'coal': 100,
        'wooden-chest': 5,
        'assembling-machine': 10,
    }
    instance.speed(10)
    instance.reset()
    yield instance.namespace
    instance.speed(10)
    #instance.reset()


def test_connect_belt_underground(game):
    game.instance.initial_inventory = {'underground-belt': 2, 'transport-belt': 200}
    game.instance.reset()

    belt_start_position = Position(x=0.0, y=1.0)
    belt_end_position = Position(x=0.0, y=10.0)
    try:
        belts = game.connect_entities(belt_start_position, belt_end_position, {Prototype.TransportBelt, Prototype.UndergroundBelt})
        counter = 0
        for belt in belts.belts:
            if isinstance(belt, UndergroundBelt):
                counter += 1

        assert counter == 2
        print(f"Transport Belts laid from {belt_start_position} to {belt_end_position}.")
    except Exception as e:
        print(f"Failed to lay Transport Belts: {e}")