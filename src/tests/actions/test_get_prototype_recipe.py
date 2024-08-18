import pytest

from factorio_types import Prototype

@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_get_recipe(game):

    recipe = game.get_prototype_recipe(Prototype.IronGearWheel)

    # Assert that the recipe of the assembling machine has been updated
    prototype_name, _ = Prototype.IronGearWheel

    game.reset()