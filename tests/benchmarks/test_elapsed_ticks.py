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

    instance.reset(all_technologies_researched=True)

    yield instance.namespace
    instance.reset(all_technologies_researched=True)


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
    Test that crafting a composite item (with auto-crafted prerequisites) takes the same
    number of ticks as manually crafting the prerequisites first.
    :param game:
    :return:
    """
    # First approach: craft electronic circuits directly (auto-crafts copper cable)
    game.instance._reset_elapsed_ticks()
    game.craft_item(Prototype.ElectronicCircuit, quantity=10)
    ticks_auto = game.instance.get_elapsed_ticks()

    # Reset game state and elapsed ticks
    game.instance.reset(all_technologies_researched=True)
    game.instance._reset_elapsed_ticks()

    # Second approach: manually craft copper cable first, then electronic circuits
    game.craft_item(Prototype.CopperCable, quantity=10)
    game.craft_item(Prototype.ElectronicCircuit, quantity=10)
    ticks_manual = game.instance.get_elapsed_ticks()

    assert ticks_manual == ticks_auto, (
        f"The tick count should be invariant to whether the prerequisites are intentionally crafted or not. "
        f"Auto: {ticks_auto}, Manual: {ticks_manual}"
    )


def test_harvesting_wood_accumulate_ticks(game):
    wood_pos = game.nearest(Resource.Wood)
    if wood_pos is None:
        pytest.skip("No wood (trees) available in the test environment")

    game.move_to(wood_pos)
    game.instance._reset_elapsed_ticks()

    # Harvest smaller quantities to avoid exhausting a single tree
    game.harvest_resource(game.nearest(Resource.Wood), quantity=5)
    ticks = game.instance.get_elapsed_ticks()

    # Find nearest wood again (may have moved to another tree if first was exhausted)
    wood_pos2 = game.nearest(Resource.Wood)
    if wood_pos2 is None:
        pytest.skip("Insufficient wood resources in the test environment")

    game.harvest_resource(wood_pos2, quantity=5)
    nticks = game.instance.get_elapsed_ticks()

    assert ticks > 25, f"Expected ticks > 25 but got {ticks}"
    assert nticks - ticks == ticks, (
        f"The tick count should be proportional to the amount of wood harvested. "
        f"First harvest: {ticks} ticks, second: {nticks - ticks} ticks"
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
    # Reset elapsed ticks to start fresh
    game.instance._reset_elapsed_ticks()

    ticks_ = []
    for i in range(10):
        game.move_to(Position(x=i, y=0))
        ticks_.append(game.instance.get_elapsed_ticks())

    nticks = game.instance.get_elapsed_ticks()
    assert nticks > 70, "The tick count should be proportional to the distance moved."
    # Verify ticks are accumulating (each move should add ticks)
    assert all(ticks_[i] <= ticks_[i + 1] for i in range(len(ticks_) - 1)), (
        "The tick count should accumulate with each move."
    )


def test_long_mine(game):
    game.move_to(game.nearest(Resource.Coal))
    game.instance._reset_elapsed_ticks()

    for i in range(100):
        game.harvest_resource(game.nearest(Resource.Coal), quantity=10)

    ticks = game.instance.get_elapsed_ticks()
    assert ticks == 60000


def test_sleep_ticks(game):
    game.sleep(10)  # sleep for 10 seconds = 600 ticks (at 60 ticks/second)
    assert game.instance.get_elapsed_ticks() >= 600, (
        "The tick count should be proportional to the amount of time slept."
    )
