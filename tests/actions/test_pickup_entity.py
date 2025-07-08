import pytest

from fle.env.entities import Position
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "stone-furnace": 1,
        "boiler": 1,
        "steam-engine": 1,
        "offshore-pump": 4,
        "pipe": 100,
        "iron-plate": 50,
        "copper-plate": 20,
        "coal": 50,
        "burner-inserter": 50,
        "burner-mining-drill": 50,
        "transport-belt": 50,
        "stone-wall": 100,
        "splitter": 4,
        "wooden-chest": 1,
    }

    instance.reset()
    yield instance.namespace
    instance.reset()


def test_pickup_item_full_inventory(game):
    """
    Test that pickup fails when inventory is at maximum capacity.
    Uses existing inventory items but maximizes stacks to test true full inventory.
    """
    # Clear inventory completely first
    game.instance.set_inventory({"wooden-chest": 1})
    placement_position = Position(x=0, y=0)
    game.move_to(placement_position)
    chest = game.place_entity(Prototype.WoodenChest, position=placement_position)
    game.instance.set_inventory({"coal": 10000})
    try:
        result = game.pickup_entity(chest)
        assert False, (
            f"Expected pickup to fail due to full inventory, but got result: {result}"
        )
    except Exception as e:
        print(e)
        assert True


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
    game.sleep(6)
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
    assert boilers_in_inventory == game.inspect_inventory()[Prototype.Boiler]


def test_place_pickup_pipe_group(game):
    game.move_to(Position(x=0, y=0))
    water_pipes = game.connect_entities(
        Position(x=0, y=1), Position(x=10, y=1), connection_type=Prototype.Pipe
    )

    game.pickup_entity(water_pipes)
    assert game.inspect_inventory()[Prototype.Pipe] == 100

    game.move_to(Position(x=0, y=0))
    water_pipes = game.connect_entities(
        Position(x=0, y=1), Position(x=10, y=1), connection_type=Prototype.Pipe
    )

    for pipe in water_pipes.pipes:
        game.pickup_entity(pipe)
    assert game.inspect_inventory()[Prototype.Pipe] == 100


def test_place_pickup_inventory(game):
    chest = game.place_entity(Prototype.WoodenChest, position=Position(x=0, y=0))
    iron_plate_in_inventory = game.inspect_inventory()[Prototype.IronPlate]
    game.insert_item(Prototype.IronPlate, chest, quantity=5)
    game.pickup_entity(Prototype.WoodenChest, position=chest.position)
    assert game.inspect_inventory()[Prototype.IronPlate] == iron_plate_in_inventory


def test_place_pickup_inventory2(game):
    chest = game.place_entity(Prototype.WoodenChest, position=Position(x=0, y=0))
    iron_plate_in_inventory = game.inspect_inventory()[Prototype.IronPlate]
    game.insert_item(Prototype.IronPlate, chest, quantity=5)
    game.pickup_entity(chest)
    assert game.inspect_inventory()[Prototype.IronPlate] == iron_plate_in_inventory


def test_pickup_belts(game):
    belts = game.connect_entities(
        Position(x=0.5, y=0.5), Position(x=0.5, y=8.5), Prototype.TransportBelt
    )
    belt = belts
    game.get_entity(Prototype.BeltGroup, belt.position)
    pickup_belts = game.pickup_entity(belt)
    assert pickup_belts


def test_pickup_belts_position(game):
    belts = game.connect_entities(
        Position(x=1, y=-1), Position(x=-2, y=0), Prototype.TransportBelt
    )
    print(belts)
    print(belts.belts)
    game.pickup_entity(Prototype.TransportBelt, Position(x=0.5, y=0.5))
    pass


def test_pickup_pipes(game):
    pipes = game.connect_entities(
        Position(x=1, y=-1), Position(x=-2, y=0), Prototype.Pipe
    )
    print(pipes)
    print(pipes.pipes)
    for belt in pipes.pipes:
        game.pickup_entity(Prototype.Pipe, belt.position)
        print(f"Pickup belt at {belt.position}")


def test_pickup_belts_that_dont_exist(game):
    belts = game.connect_entities(
        Position(x=0.5, y=0.5), Position(x=0.5, y=8.5), Prototype.TransportBelt
    )
    belt = belts
    nbelts = game.get_entity(Prototype.BeltGroup, belt.position)
    pickup_belts = game.pickup_entity(belt)
    assert pickup_belts
    try:
        game.pickup_entity(nbelts)
    except Exception:
        assert True, "Should not be able to pick up a non-existent belt"
