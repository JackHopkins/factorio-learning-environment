import pytest

from fle.env.game_types import Prototype


@pytest.fixture()
def game(configure_game):
    return configure_game(inventory={"assembling-machine-1": 1})


def test_get_recipe(game):
    recipe = game.get_prototype_recipe(Prototype.IronGearWheel)

    assert recipe.ingredients[0].name == "iron-plate"
    assert recipe.ingredients[0].count == 2
