import pytest

from fle.env.entities import Position
from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    game.initial_inventory = {"assembling-machine-1": 1}
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_set_entity_recipe(game):
    # Place an assembling machine
    assembling_machine = game.place_entity(
        Prototype.AssemblingMachine1, position=Position(x=0, y=0)
    )

    # Set a recipe for the assembling machine
    assembling_machine = game.set_entity_recipe(
        assembling_machine, Prototype.IronGearWheel
    )

    # Assert that the recipe of the assembling machine has been updated
    prototype_name, _ = Prototype.IronGearWheel.value

    assert assembling_machine.recipe == prototype_name
