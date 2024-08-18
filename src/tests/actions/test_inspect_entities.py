import pytest

from factorio_entities import Position
from factorio_types import Prototype


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_inspect_entities(game):
    inventory = game.inspect_inventory()
    coal_count = inventory[Prototype.Coal]
    assert coal_count != 0
    chest = game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))
    game.insert_item(Prototype.Coal, chest, quantity=5)

    inspected = game.inspect_entities(radius=1, position=Position(x=chest.position.x, y=chest.position.y))

    assert len(inspected) == 2