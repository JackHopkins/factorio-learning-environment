import pytest

from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {"assembling-machine-1": 1}
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_get_recipe(game):
    recipe = game.get_prototype_recipe(Prototype.IronGearWheel)

    assert recipe.ingredients[0].name == "iron-plate"
    assert recipe.ingredients[0].count == 2
