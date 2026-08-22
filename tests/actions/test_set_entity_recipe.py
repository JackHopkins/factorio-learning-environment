import pytest

from fle.env.entities import Position
from fle.env.game_types import Prototype, RecipeName


@pytest.fixture()
def game(configure_game):
    return configure_game(inventory={"assembling-machine-1": 1})


def test_set_entity_recipe(game):
    # Place an assembling machine
    assembling_machine = game.place_entity(
        Prototype.AssemblingMachine1, position=Position(x=0, y=0)
    )

    # Set a recipe for the assembling machine
    assembling_machine = game.set_entity_recipe(
        assembling_machine, RecipeName.IronGearWheel
    )

    # Assert that the recipe of the assembling machine has been updated
    recipe_name = RecipeName.IronGearWheel.value

    assert assembling_machine.recipe == recipe_name
