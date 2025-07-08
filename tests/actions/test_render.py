import pytest

from fle.env.entities import Position, Layer
from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "iron-chest": 1,
        "small-electric-pole": 20,
        "iron-plate": 10,
        "assembling-machine-1": 1,
        "pipe-to-ground": 10,
        "pipe": 30,
        "transport-belt": 50,
        "underground-belt": 30,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_basic_render(game):
    game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))
    game.connect_entities(
        Position(x=0, y=-2),
        Position(x=15, y=5),
        {Prototype.Pipe, Prototype.UndergroundPipe},
    )
    game.connect_entities(
        Position(x=0, y=-10), Position(x=15, y=-10), {Prototype.SmallElectricPole}
    )
    image = game._render(position=Position(x=0, y=5), layers=Layer.ALL)
    image.show()
    pass
