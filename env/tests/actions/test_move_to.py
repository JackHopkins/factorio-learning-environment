from time import sleep

import pytest

from entities import Position
from instance import FactorioInstance
from game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance.namespace
    #instance.reset()


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
    position = game.move_to(game.nearest(Resource.Stone))
    game.harvest_resource(game.nearest(Resource.Stone), quantity=5)

    # Check if we got the stone
    inventory = game.inspect_inventory()
    assert inventory.get(Prototype.Stone) >= 5, "Failed to get enough stone"

def test_move_to_check_position(game):
    target_pos = Position(x=-9.5, y=-11.5)

    # Move to target position
    game.move_to(target_pos)

    # Verify we're within range by inspecting entities
    inspection = game.inspect_entities(target_pos, radius=10)
    player_pos = Position(x=inspection.player_position[0], y=inspection.player_position[1])
    distance = ((player_pos.x - target_pos.x) ** 2 + (player_pos.y - target_pos.y) ** 2) ** 0.5

    assert distance <= 10, f"Failed to move within range. Distance: {distance} units"

def test_move_to_laying_leading(game):
    """
    Move to the nearest coal patch
    Move to the nearest iron patch
    :param game:
    :return:
    """
    size = 5

    # north
    game.move_to(Position(x=0, y=-size*3), laying=Prototype.TransportBelt)
    # northeast
    game.move_to(Position(x=size, y=-size*2), leading=Prototype.TransportBelt)
    # east
    game.move_to(Position(x=size*2, y=-size*2), leading=Prototype.TransportBelt)
    # southeast
    game.move_to(Position(x=size, y=-size), leading=Prototype.TransportBelt)

    game.move_to(Position(x=size*2, y=0), leading=Prototype.TransportBelt)

    entities = game.inspect_entities(Position(x=size, y=size), radius=20)

    print(entities)
    # # north
    # game.move_to(Position(x=0, y=-size), laying=Prototype.TransportBelt)
    # # northeast
    # game.move_to(Position(x=size, y=-size*2), laying=Prototype.TransportBelt)
    # # east
    # game.move_to(Position(x=size*2, y=-size*2), laying=Prototype.TransportBelt)
    # # southeast
    # game.move_to(Position(x=size*3, y=-size), laying=Prototype.TransportBelt)
    # # south
    # game.move_to(Position(x=size*3, y=0), laying=Prototype.TransportBelt)
    # # southwest
    # game.move_to(Position(x=size*2, y=size), laying=Prototype.TransportBelt)
    # # west
    # game.move_to(Position(x=size, y=size), laying=Prototype.TransportBelt)
    # # northwest
    # game.move_to(Position(x=0, y=0), laying=Prototype.TransportBelt)


    # resources = [Resource.Coal, Resource.IronOre, Resource.CopperOre, Resource.Stone]
    #
    # for i in range(10):
    #     for resource in resources:
    #         game.move_to(game.nearest(resource), laying=Prototype.TransportBelt)

def test_long_way(game):
    position = Position(x=300, y=300)

    game.move_to(position)


if __name__ == '__main__':
    factorio = FactorioInstance(address='localhost',
                            bounding_box=200,
                            tcp_port=27000,
                            cache_scripts=True,
                            fast=True,
                            inventory={
                                'coal': 50,
                                'copper-plate': 50,
                                'iron-plate': 50,
                                'iron-chest': 2,
                                'burner-mining-drill': 3,
                                'electric-mining-drill': 1,
                                'assembling-machine-1': 1,
                                'stone-furnace': 9,
                                'transport-belt': 50,
                                'boiler': 1,
                                'burner-inserter': 32,
                                'pipe': 15,
                                'steam-engine': 1,
                                'small-electric-pole': 10
                        })

    @factorio.run_func_in_factorio_env
    def test_create_coal_transportation_system():
        coal_position = nearest(Resource.Coal)
        assert coal_position, "No coal found nearby"

        move_to(coal_position)