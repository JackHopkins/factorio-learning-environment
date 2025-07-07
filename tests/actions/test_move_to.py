import pytest

from fle.env.entities import Position
from fle.env import FactorioInstance
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance.namespace
    # instance.reset()


def test_move_to(game):
    """
    Move to the nearest coal patch
    Move to the nearest iron patch
    :param game:
    :return:
    """
    resources = [Resource.Coal, Resource.IronOre, Resource.CopperOre, Resource.Stone]

    for i in range(10):
        for resource in resources:
            game.move_to(game.nearest(resource))
            pass


def test_move_to_bug(game):
    # Get stone for stone furnace
    game.move_to(game.nearest(Resource.Stone))
    game.harvest_resource(game.nearest(Resource.Stone), quantity=5)

    # Check if we got the stone
    inventory = game.inspect_inventory()
    assert inventory.get(Prototype.Stone) >= 5, "Failed to get enough stone"


def test_move_to_check_position(game):
    target_pos = Position(x=-9.5, y=-11.5)

    # Move to target position
    game.move_to(target_pos)


if __name__ == "__main__":
    factorio = FactorioInstance(
        address="localhost",
        bounding_box=200,
        tcp_port=27000,
        cache_scripts=True,
        fast=True,
        inventory={
            "coal": 50,
            "copper-plate": 50,
            "iron-plate": 50,
            "iron-chest": 2,
            "burner-mining-drill": 3,
            "electric-mining-drill": 1,
            "assembling-machine-1": 1,
            "stone-furnace": 9,
            "transport-belt": 50,
            "boiler": 1,
            "burner-inserter": 32,
            "pipe": 15,
            "steam-engine": 1,
            "small-electric-pole": 10,
        },
    )
