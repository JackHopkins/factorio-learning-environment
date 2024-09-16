import pytest

from factorio_entities import Position
from factorio_instance import Direction
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.reset()
    yield instance

def test_place(game):
    """
    Place a boiler at (0, 0)
    :param game:
    :return:
    """
    boilers_in_inventory = game.inspect_inventory()[Prototype.Boiler]
    game.place_entity(Prototype.Boiler, position=(0, 0))
    assert boilers_in_inventory - 1 == game.inspect_inventory()[Prototype.Boiler]

def test_place_in_all_directions(game):
    """
    Place a burner inserters in each direction
    :param game:
    :return:
    """
    left = game.place_entity(Prototype.BurnerInserter, position=(-1, 0), direction=Direction.LEFT)
    right = game.place_entity(Prototype.BurnerInserter, position=(1, 0), direction=Direction.RIGHT)
    up = game.place_entity(Prototype.BurnerInserter, position=(0, -1), direction=Direction.UP)
    down = game.place_entity(Prototype.BurnerInserter, position=(0, 1), direction=Direction.DOWN)

    assert up.direction == Direction.UP
    assert down.direction == Direction.DOWN
    assert left.direction == Direction.LEFT
    assert right.direction == Direction.RIGHT

def test_place_pickup(game):
    """
    Place a boiler at (0, 0) and then pick it up
    :param game:
    :return:
    """
    boilers_in_inventory = game.inspect_inventory()[Prototype.Boiler]
    game.place_entity(Prototype.Boiler, position=(0, 0))
    assert boilers_in_inventory == game.inspect_inventory()[Prototype.Boiler] + 1

    game.pickup_entity(Prototype.Boiler, position=(0, 0))
    assert boilers_in_inventory == game.inspect_inventory()[Prototype.Boiler] - 1

def test_place_overide(game):
    """
    Place an inserter over a transport belt and verify that the transport belt is removed
    :param game:
    :return:
    """

    # Lay belts from intermediate position to iron position (along X-axis)
    iron_position = game.nearest(Resource.IronOre)
    far_left_of_iron = Position(x=iron_position.x + 10, y=iron_position.y)
    left_of_iron = Position(x=iron_position.x + 1, y=iron_position.y)

    coal_belt = game.connect_entities(far_left_of_iron, left_of_iron, connection_type=Prototype.TransportBelt)

    # Place the iron mining drill at iron_position, facing down
    game.move_to(iron_position)
    final_belt = coal_belt[-1]
    # Place an inserter to fuel the iron drill from the coal belt
    inserter_position = Position(x=final_belt.position.x + final_belt.tile_dimensions.tile_width / 2,
                                 y=final_belt.position.y)
    inserter = game.place_entity(Prototype.BurnerInserter, position=left_of_iron, direction=Direction.LEFT, exact=True)

    #assert inserter_position == Position(x=iron_position.x + 0.5, y=iron_position.y - 1)
    inspect_entities = game.inspect_entities(inserter.position, radius=10)

    for entity in inspect_entities:
        if entity["name"] == Prototype.TransportBelt.name:
            assert entity["quantity"] == 9
    pass