import pytest

from entities import Position, Layer
from game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {'iron-chest': 1,
                                  'small-electric-pole': 20,
                                  'iron-plate': 10,
                                  'assembling-machine-1': 1,
                                  'pipe-to-ground': 10,
                                  'pipe': 30, 'transport-belt': 50, 'underground-belt': 30}
    instance.reset()
    yield instance.namespace
    instance.reset()

def test_basic_render(game):
    chest = game.place_entity(Prototype.AssemblingMachine1, position=Position(x=0, y=0))
    belts = game.connect_entities(Position(x=0, y=-2), Position(x=15, y=5), {Prototype.Pipe, Prototype.UndergroundPipe})
    poles = game.connect_entities(Position(x=0, y=-10), Position(x=15, y=-10), { Prototype.SmallElectricPole })
    image = game._render(position=Position(x=0, y=5), layers=Layer.ALL)
    image.show()
    pass