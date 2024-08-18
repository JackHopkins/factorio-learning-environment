

import pytest

from factorio_entities import Position
from factorio_types import Prototype


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_save_load(game):

    game._send("/c game.server_save('test')")
    chest = game.place_entity(Prototype.IronChest, position=Position(x=0, y=0))
    game.insert_item(Prototype.Coal, chest, quantity=5)
    game._send("/c game.server_load('test')")