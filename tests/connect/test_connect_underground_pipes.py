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
        "assembling-machine-1": 10,
        "pipe-to-ground": 4,
    }
    instance.speed(10)
    instance.reset()
    yield instance.namespace
    instance.speed(10)
    # instance.reset()


def test_connect_pipes_underground_limited_inventory(game):
    game.instance.initial_inventory = {"pipe-to-ground": 2, "pipe": 200}
    game.instance.reset()

    belt_start_position = Position(x=0, y=-5.0)
    belt_end_position = Position(x=0.0, y=15.0)
    try:
        belts = game.connect_entities(
            belt_start_position,
            belt_end_position,
            {Prototype.UndergroundPipe, Prototype.Pipe},
        )
        counter = 0
        for belt in belts.belts:
            if isinstance(belt, UndergroundBelt):
                counter += 1

        assert counter == 2
        print(
            f"Transport Belts laid from {belt_start_position} to {belt_end_position}."
        )
    except Exception as e:
        print(f"Failed to lay Transport Belts: {e}")


def test_connect_pipes_with_underground_pipes(game):
    """
    This should ensure that pipe groups are always returned - instead of pipes themselves.
    """
    position_1 = Position(x=0.5, y=0.5)
    position_2 = Position(x=0, y=20)
    pipes = game.connect_entities(
        position_1, position_2, {Prototype.Pipe, Prototype.UndergroundPipe}
    )

    # game.pickup_entity(pipes)
    assert len(pipes.pipes) > 5


def test_connect_pipes_with_underground_pipes_loop(game):
    """
    This should ensure that pipe groups are always returned - instead of pipes themselves.
    """
    position_1 = Position(x=10, y=0)
    position_2 = Position(x=10, y=10)
    position_3 = Position(x=20, y=10)
    position_4 = Position(x=20, y=0)
    pipes = game.connect_entities(
        position_1,
        position_2,
        position_3,
        position_4,
        {Prototype.Pipe, Prototype.UndergroundPipe},
    )
    assert len(pipes.pipes) == 18
