import pytest

from factorio_entities import Position
from factorio_types import Prototype

@pytest.fixture()
def game(instance):
    instance.initial_inventory = {'transport-belt': 12,}
    instance.reset()
    yield instance.namespace
    instance.reset()

def test_dry_run(game):
    position_1 = Position(x=3, y=1)
    position_2 = Position(x=2, y=4)
    belts = game.connect_entities(position_1, position_2, Prototype.TransportBelt, True)
    assert game.inspect_inventory()[Prototype.TransportBelt] == 12
    assert len(game.get_entities()) == 0
    assert isinstance(belts, dict)
    assert belts["number_of_entities_available"] == 12
    assert belts["number_of_entities_required"] < 12

    position_1 = Position(x=30, y=1)
    position_2 = Position(x=-20, y=4)
    belts = game.connect_entities(position_1, position_2, Prototype.TransportBelt, True)
    assert game.inspect_inventory()[Prototype.TransportBelt] == 12
    assert len(game.get_entities()) == 0
    assert isinstance(belts, dict)
    assert belts["number_of_entities_available"] == 12
    assert belts["number_of_entities_required"] > 12


def test_connect_without_enough(game):
    position_1 = Position(x=30, y=1)
    position_2 = Position(x=-20, y=4)
    try:
        belts = game.connect_entities(position_1, position_2, Prototype.TransportBelt)
    except Exception as e:
        pass
    assert game.inspect_inventory()[Prototype.TransportBelt] == 12
    assert len(game.get_entities()) == 0

    position_1 = Position(x=3, y=1)
    position_2 = Position(x=0, y=4)

    belts = game.connect_entities(position_1, position_2, Prototype.TransportBelt)
    assert game.inspect_inventory()[Prototype.TransportBelt] < 12
    assert len(game.get_entities()) != 0
    assert len(belts) != 0


