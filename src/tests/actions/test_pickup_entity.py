import pytest

from factorio_entities import Position
from factorio_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        'stone-furnace': 1, 'boiler': 1, 'steam-engine': 1, 'offshore-pump': 4, 'pipe': 100,
        'iron-plate': 50, 'copper-plate': 20, 'coal': 50, 'burner-inserter': 50, 'burner-mining-drill': 50,
        'transport-belt': 50, 'stone-wall': 100, 'splitter': 4, 'wooden-chest': 1
    }

    instance.reset()
    yield instance
    instance.reset()

def test_place_pickup(game):
    """
    Place a boiler at (0, 0) and then pick it up
    :param game:
    :return:
    """
    boilers_in_inventory = game.inspect_inventory()[Prototype.Boiler]
    game.place_entity(Prototype.Boiler, position=Position(x=0, y=0))
    assert boilers_in_inventory == game.inspect_inventory()[Prototype.Boiler] + 1

    game.pickup_entity(Prototype.Boiler, position=Position(x=0, y=0))
    assert boilers_in_inventory == game.inspect_inventory()[Prototype.Boiler] - 1

def test_place_pickup_inventory(game):
    chest = game.place_entity(Prototype.WoodenChest, position=Position(x=0,y=0))
    iron_plate_in_inventory = game.inspect_inventory()[Prototype.IronPlate]
    game.insert_item(Prototype.IronPlate, chest, quantity=5)
    game.pickup_entity(Prototype.WoodenChest, position=chest.position)
    assert game.inspect_inventory()[Prototype.IronPlate] == iron_plate_in_inventory