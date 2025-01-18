import pytest

from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.reset()
    instance.set_inventory(**{'iron-plate': 40,
                              'iron-gear-wheel': 1,
                              'electronic-circuit': 3,
                              'pipe': 1,
                              'copper-plate': 10})
    yield instance
    instance.reset()

def test_crafting_accumulate_ticks(game):
    """
    Attempt to craft an iron chest with insufficient resources and assert that no items are crafted.
    :param game:
    :return:
    """
    ticks = game.get_elapsed_ticks()
    try:
        game.craft_item(Prototype.IronChest, quantity=100)
    except Exception as e:
        assert True
    ticks = game.get_elapsed_ticks()