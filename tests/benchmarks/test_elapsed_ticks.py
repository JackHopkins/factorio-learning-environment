import pytest

from fle.env.entities import Position
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "iron-plate": 400,
        "iron-gear-wheel": 1,
        "electronic-circuit": 3,
        "pipe": 1,
        "copper-plate": 100,
    }

    instance.reset()

    yield instance.namespace
    instance.reset()


def test_crafting_accumulate_ticks(game):
    """
    Attempt to craft an iron chest with insufficient resources and assert that no items are crafted.
    :param game:
    :return:
    """

    game.craft_item(Prototype.IronChest, quantity=50)
    ticks = game.instance.get_elapsed_ticks()
    assert ticks == 1500


def test_crafting_composite_accumulate_ticks(game):
    """
    Attempt to craft an iron chest with insufficient resources and assert that no items are crafted.
    :param game:
    :return:
    """
    _ = game.instance.get_elapsed_ticks()
    game.craft_item(Prototype.ElectronicCircuit, quantity=10)

    ticks = game.instance.get_elapsed_ticks()

    game.instance.reset()

    game.craft_item(Prototype.CopperCable, quantity=10)
    game.craft_item(Prototype.ElectronicCircuit, quantity=10)
    nticks = game.instance.get_elapsed_ticks() - ticks

    assert nticks == ticks, (
        "The tick count should be invariant to whether the prerequisites are intentionally crafted or not."
    )


def test_harvesting_wood_accumulate_ticks(game):
    game.move_to(game.nearest(Resource.Wood))
    game.instance._reset_elapsed_ticks()

    game.harvest_resource(game.nearest(Resource.Wood), quantity=10)
    ticks = game.instance.get_elapsed_ticks()
    game.harvest_resource(game.nearest(Resource.Wood), quantity=10)
    nticks = game.instance.get_elapsed_ticks()

    assert ticks > 50
    assert nticks - ticks == ticks, (
        "The tick count should be proportional to the amount of wood harvested."
    )


def test_harvesting_coal_accumulate_ticks(game):
    game.move_to(game.nearest(Resource.Coal))
    game.instance._reset_elapsed_ticks()

    game.harvest_resource(game.nearest(Resource.Coal), quantity=10)
    ticks = game.instance.get_elapsed_ticks()
    game.harvest_resource(game.nearest(Resource.Coal), quantity=10)
    nticks = game.instance.get_elapsed_ticks()

    assert ticks == 600
    assert nticks - ticks == ticks, (
        "The tick count should be proportional to the amount of wood harvested."
    )


def test_moving_accumulate_ticks(game):
    # game.move_to(game.nearest(Resource.Coal))
    ticks = game.instance.get_elapsed_ticks()
    # assert ticks > 150, "The tick count should be proportional to the distance moved."
    ticks_ = []
    for i in range(10):
        game.move_to(Position(x=i, y=0))
        ticks_.append(game.instance.get_elapsed_ticks())

    nticks = game.instance.get_elapsed_ticks()
    assert nticks > 80, "The tick count should be proportional to the distance moved."
    assert nticks - ticks == ticks, (
        "The tick count should be invariant to the number of moves made."
    )


def test_long_mine(game):
    game.move_to(game.nearest(Resource.Coal))
    game.instance._reset_elapsed_ticks()

    for i in range(100):
        game.harvest_resource(game.nearest(Resource.Coal), quantity=10)

    ticks = game.instance.get_elapsed_ticks()
    assert ticks == 60000


def test_sleep_ticks(game):
    game.sleep(10)  # sleep for 10 seconds ~= 6000 ticks
    assert game.instance.get_elapsed_ticks() >= 5000, (
        "The tick count should be proportional to the amount of time slept."
    )
