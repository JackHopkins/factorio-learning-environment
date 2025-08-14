from fle.env.game import FactorioInstance
import pytest

from fle.env.game import Position, EntityStatus
from fle.env.game.game_types import Prototype


@pytest.fixture()
def game(instance: FactorioInstance):
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


def test_not_connected_pipes_is_not_connected(game):
    pipes1 = game.connect_entities(
        Position(x=0, y=0), Position(x=5, y=0), connection_type=Prototype.Pipe
    )
    assert pipes1.status == EntityStatus.EMPTY

    pipes2 = game.connect_entities(
        Position(x=7, y=0), Position(x=12, y=0), connection_type=Prototype.Pipe
    )
    assert pipes2.status == EntityStatus.EMPTY
