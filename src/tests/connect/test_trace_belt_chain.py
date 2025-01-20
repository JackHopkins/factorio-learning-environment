import pytest

from factorio_entities import Position, Direction
from factorio_types import Prototype
from utilities.groupable_entities import agglomerate_groupable_entities


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        'transport-belt': 100,
    }
    instance.reset()
    yield instance.namespace
    #instance.reset()


def test_connect_trace_belt_chain(game):
    belts = []
    for i in range(5):
        t = game.place_entity(Prototype.TransportBelt, Direction.RIGHT, Position(x=i, y=0))
        belts.append(t)
        #assert t.position.x == i+0.5

    groups = agglomerate_groupable_entities(belts)
    assert len(groups[0].belts) == 5, "Should have 5 belts in the first group"




