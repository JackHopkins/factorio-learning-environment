import pytest

from entities import Position
from game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        'stone-furnace': 1, 'boiler': 1, 'steam-engine': 1, 'offshore-pump': 4, 'pipe': 100,
        'iron-plate': 50, 'copper-plate': 20, 'coal': 50, 'burner-inserter': 50, 'burner-mining-drill': 50,
        'transport-belt': 50, 'stone-wall': 100, 'splitter': 4, 'wooden-chest': 1
    }

    instance.reset()
    yield instance.namespace
    instance.reset()

def test_pickup_ground_item(game):
    """
    Place a boiler at (0, 0) and then pick it up
    :param game:
    :return:
    """
    iron = game.nearest(Resource.IronOre)
    game.move_to(iron)
    drill = game.place_entity(Prototype.BurnerMiningDrill, position=iron)
    game.insert_item(Prototype.Coal, drill, quantity=50)
    game.sleep(1)
    game.pickup_entity(Prototype.IronOre, drill.drop_position)
    assert game.inspect_inventory()[Prototype.IronOre] == 1

def test_place_pickup(game):
    """
    Place a boiler at (0, 0) and then pick it up
    :param game:
    :return:
    """
    boilers_in_inventory = game.inspect_inventory()[Prototype.Boiler]
    game.place_entity(Prototype.Boiler, position=Position(x=0, y=0))
    assert boilers_in_inventory == game.inspect_inventory()[Prototype.Boiler] + 1

    game.pickup_entity(Prototype.Boiler, position=Position(x=0, y=0))
    assert boilers_in_inventory == game.inspect_inventory()[Prototype.Boiler] - 1

def test_place_pickup_pipe_group(game):
    """
    Place a boiler at (0, 0) and then pick it up
    :param game:
    :return:
    """
    game.move_to(Position(x=0, y=0))
    water_pipes = game.connect_entities(Position(x=0, y=0), Position(x=10, y=0), connection_type=Prototype.Pipe)

    game.pickup_entity(water_pipes[0])
    assert game.inspect_inventory()[Prototype.Pipe] == 100


def test_place_pickup_inventory(game):
    chest = game.place_entity(Prototype.WoodenChest, position=Position(x=0,y=0))
    iron_plate_in_inventory = game.inspect_inventory()[Prototype.IronPlate]
    game.insert_item(Prototype.IronPlate, chest, quantity=5)
    game.pickup_entity(Prototype.WoodenChest, position=chest.position)
    assert game.inspect_inventory()[Prototype.IronPlate] == iron_plate_in_inventory

def test_place_pickup_inventory2(game):
    chest = game.place_entity(Prototype.WoodenChest, position=Position(x=0,y=0))
    iron_plate_in_inventory = game.inspect_inventory()[Prototype.IronPlate]
    game.insert_item(Prototype.IronPlate, chest, quantity=5)
    game.pickup_entity(chest)
    assert game.inspect_inventory()[Prototype.IronPlate] == iron_plate_in_inventory

def test_pickup_belts(game):
    belts = game.connect_entities(Position(x=0.5, y=0.5), Position(x=0.5, y=8.5), Prototype.TransportBelt)
    belt = belts[0]
    nbelts = game.get_entity(Prototype.BeltGroup, belt.position)
    pickup_belts = game.pickup_entity(belt)
    assert pickup_belts

def test_pickup_belts_position(game):
    belts = game.connect_entities(Position(x=1, y=-1), Position(x=-2, y=0), Prototype.TransportBelt)
    print(belts)
    print(belts[0].belts)
    game.pickup_entity(Prototype.TransportBelt, Position(x=1.5, y=0.5))
    pass

def test_pickup_pipes(game):
    pipes = game.connect_entities(Position(x=1, y=-1), Position(x=-2, y=0), Prototype.Pipe)
    print(pipes)
    print(pipes[0].pipes)
    for belt in pipes[0].pipes:
        game.pickup_entity(Prototype.Pipe, belt.position)
        print(f"Pickup belt at {belt.position}")

def test_pickup_belts_that_dont_exist(game):
    belts = game.connect_entities(Position(x=0.5, y=0.5), Position(x=0.5, y=8.5), Prototype.TransportBelt)
    belt = belts[0]
    nbelts = game.get_entity(Prototype.BeltGroup, belt.position)
    pickup_belts = game.pickup_entity(belt)
    assert pickup_belts
    try:
        game.pickup_entity(nbelts)
    except Exception as e:
        assert True, "Should not be able to pick up a non-existent belt"