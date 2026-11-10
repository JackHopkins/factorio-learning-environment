import pytest

from fle.env.game_types import Prototype


@pytest.fixture()
def game(configure_game):
    return configure_game(inventory={"assembling-machine-1": 1})


def test_get_recipe(game):
    recipe = game.get_prototype_recipe(Prototype.IronGearWheel)

    assert recipe.ingredients[0].name == "iron-plate"
    assert recipe.ingredients[0].count == 2


def test_get_recipe_time_category_and_enabled(game):
    recipe = game.get_prototype_recipe(Prototype.IronGearWheel)
    assert recipe.energy == 0.5
    assert recipe.category == "crafting"
    assert recipe.enabled is True

    recipe = game.get_prototype_recipe(Prototype.EngineUnit)
    assert recipe.energy == 10
    assert recipe.category == "advanced-crafting"
