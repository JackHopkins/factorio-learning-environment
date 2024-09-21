from time import sleep

import pytest

from factorio_entities import Position
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance


def test_move_to(game):
    """
    Move to the nearest coal patch
    Move to the nearest iron patch
    :param game:
    :return:
    """
    size = 5

    # north
    game.move_to(Position(x=0, y=-size*3), laying=Prototype.TransportBelt)
    # northeast
    game.move_to(Position(x=size, y=-size*2), leading=Prototype.TransportBelt)
    # east
    game.move_to(Position(x=size*2, y=-size*2), leading=Prototype.TransportBelt)
    # southeast
    game.move_to(Position(x=size, y=-size), leading=Prototype.TransportBelt)

    game.move_to(Position(x=size*2, y=0), leading=Prototype.TransportBelt)

    entities = game.inspect_entities(Position(x=size, y=size), radius=20)

    print(entities)
    # # north
    # game.move_to(Position(x=0, y=-size), laying=Prototype.TransportBelt)
    # # northeast
    # game.move_to(Position(x=size, y=-size*2), laying=Prototype.TransportBelt)
    # # east
    # game.move_to(Position(x=size*2, y=-size*2), laying=Prototype.TransportBelt)
    # # southeast
    # game.move_to(Position(x=size*3, y=-size), laying=Prototype.TransportBelt)
    # # south
    # game.move_to(Position(x=size*3, y=0), laying=Prototype.TransportBelt)
    # # southwest
    # game.move_to(Position(x=size*2, y=size), laying=Prototype.TransportBelt)
    # # west
    # game.move_to(Position(x=size, y=size), laying=Prototype.TransportBelt)
    # # northwest
    # game.move_to(Position(x=0, y=0), laying=Prototype.TransportBelt)


    # resources = [Resource.Coal, Resource.IronOre, Resource.CopperOre, Resource.Stone]
    #
    # for i in range(10):
    #     for resource in resources:
    #         game.move_to(game.nearest(resource), laying=Prototype.TransportBelt)




