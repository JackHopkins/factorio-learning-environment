import pytest

from factorio_types import Resource

@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance
    instance.reset()

def test_harvest_resource(game):
    """
    Find the nearest coal resource patch and harvest 5 coal from it.
    :param game:
    :return:
    """
    quantity = 50
    inventory = game.inspect_inventory()
    # Check initial inventory
    initial_coal = inventory[Resource.Coal]
    # Find nearest coal resource
    nearest_coal = game.nearest(Resource.Coal)
    # Move to the coal resource
    game.move_to(nearest_coal)
    try:
        # Harvest coal
        game.harvest_resource(nearest_coal, quantity=quantity)  # Assuming there is a coal resource at (10, 10)
    except Exception as e:
        print(e)
    # Check the inventory after harvesting
    final_coal = game.inspect_inventory()[Resource.Coal]
    # Assert that the coal has been added to the inventory
    assert quantity == final_coal - initial_coal

def test_harvest_trees(game):
    """
    Find the nearest tree resource patch and harvest 5 wood from it.
    :param game:
    :return:
    """
    quantity = 50
    inventory = game.inspect_inventory()
    # Check initial inventory
    initial_wood = inventory[Resource.Wood]
    # Find nearest wood resource
    nearest_wood = game.nearest(Resource.Wood)
    # Move to the wood resource
    game.move_to(nearest_wood)
    # Harvest coal
    game.harvest_resource(nearest_wood, quantity=quantity, radius=50)  # Assuming there is a wood resource here

    # Check the inventory after harvesting
    final_wood = game.inspect_inventory()[Resource.Wood]
    # Assert that the coal has been added to the inventory
    assert quantity == final_wood - initial_wood