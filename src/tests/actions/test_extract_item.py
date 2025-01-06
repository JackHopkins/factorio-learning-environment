import pytest

from factorio_entities import Position
from factorio_types import Prototype

@pytest.fixture()
def game(instance):
    instance.initial_inventory = {'iron-chest': 1, 'iron-plate': 10}
    instance.reset()
    yield instance
    instance.reset()

def test_extract(game):
    chest = game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))
    game.insert_item(Prototype.IronPlate, chest, quantity=10)
    count = game.extract_item(Prototype.IronPlate, chest.position, quantity=2)
    assert game.inspect_inventory()[Prototype.IronPlate] == 1
