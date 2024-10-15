# inserter_with_coal = insert_item(Prototype.Coal, inserter, quantity=2)
# print(inserter_with_coal.fuel_inventory)
# -->{'coal': 2}
# furnace = get_entity(Prototype.StoneFurnace, furnace.position)
# print(furnace.fuel_inventory)
# --> [{'name': 'coal', 'count': 5}]

import pytest

from factorio_entities import Position
from factorio_types import Prototype

@pytest.fixture()
def game(instance):
    instance.initial_inventory = {'iron-chest': 1, 'iron-plate': 10, 'burner-inserter': 1, 'stone-furnace': 1, 'coal': 5}
    instance.reset()
    yield instance
    instance.reset()

def test_fuel_inventory_equivalence(game):
    """
    Test that the fuel_inventory of an inserter is equivalent to
    :param game:
    :return:
    """
    inserter = game.place_entity(Prototype.BurnerInserter, position=Position(x=0, y=0))
    inserter_with_coal = game.insert_item(Prototype.Coal, inserter, quantity=2)
    print(inserter_with_coal.fuel_inventory)

    same_inserter_with_coal = game.get_entity(Prototype.BurnerInserter, inserter.position)
    assert same_inserter_with_coal.fuel_inventory == inserter_with_coal.fuel_inventory
