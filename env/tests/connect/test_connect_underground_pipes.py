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
        'assembling-machine-1': 10,
        'pipe-to-ground': 4
    }
    instance.speed(10)
    instance.reset()
    yield instance.namespace
    instance.speed(10)
    #instance.reset()


def test_connect_pipes_with_underground_pipes(game):
    """
    This should ensure that pipe groups are always returned - instead of pipes themselves.
    """
    position_1 = Position(x=0.5, y=0.5)
    position_2 = Position(x=0, y=20)
    pipes = game.connect_entities(position_1, position_2, { Prototype.Pipe, Prototype.UndergroundPipe })
    assert len(pipes.pipes) == 2



def test_connect_pipes_with_underground_pipes_loop(game):
    """
    This should ensure that pipe groups are always returned - instead of pipes themselves.
    """
    position_1 = Position(x=0, y=0)
    position_2 = Position(x=0, y=10)
    position_3 = Position(x=10, y=10)
    position_4 = Position(x=10, y=0)
    pipes = game.connect_entities(position_1, position_2, { Prototype.Pipe, Prototype.UndergroundPipe })
    assert len(pipes.pipes) == 2