import pytest

from factorio_entities import Position
from factorio_instance import Direction
from factorio_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        'stone-furnace': 1, 'boiler': 1, 'steam-engine': 1, 'offshore-pump': 4, 'pipe': 100,
        'iron-plate': 50, 'copper-plate': 20, 'coal': 50, 'burner-inserter': 50, 'burner-mining-drill': 50,
        'transport-belt': 50
    }

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
    down = game.place_entity(Prototype.BurnerInserter, position=(0, 1), direction=Direction.DOWN)
    left = game.place_entity(Prototype.BurnerInserter, position=(-1, 0), direction=Direction.LEFT)
    right = game.place_entity(Prototype.BurnerInserter, position=(1, 0), direction=Direction.RIGHT)
    up = game.place_entity(Prototype.BurnerInserter, position=(0, -1), direction=Direction.UP)


    assert up.direction.value == Direction.UP.value
    assert left.direction.value == Direction.LEFT.value
    assert right.direction.value == Direction.RIGHT.value
    assert down.direction.value == Direction.DOWN.value

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

def test_place_override(game):
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

    belt = game.inspect_entities(inserter.position, radius=10).get_entity(Prototype.TransportBelt)

    assert belt.quantity == 9

def test_place_offshore_pumps(game):
    """
    Place offshore pumps at each cardinal direction
    :param game:
    :return:
    """
    # move to the nearest water source
    entity = Prototype.OffshorePump
    water_location = game.nearest(Resource.Water)
    game.move_to(Position(x=water_location.x - 10, y=water_location.y))
    offshore_pump = game.place_entity(entity,
                                      position=water_location,
                                      direction=Direction.LEFT)
    assert offshore_pump.direction.value == Direction.LEFT.value
    game.move_to(Position(x=water_location.x, y=water_location.y))
    offshore_pump = game.place_entity(entity,
                                        position=water_location,
                                        direction=Direction.RIGHT)
    assert offshore_pump.direction.value == Direction.RIGHT.value
    game.move_to(Position(x=water_location.x, y=water_location.y))
    offshore_pump = game.place_entity(entity,
                                        position=water_location,
                                        direction=Direction.UP)
    assert offshore_pump.direction.value == Direction.UP.value
    game.move_to(Position(x=water_location.x, y=water_location.y))
    offshore_pump = game.place_entity(entity,
                                        position=water_location,
                                        direction=Direction.DOWN)
    assert offshore_pump.direction.value == Direction.DOWN.value

def test_place_burner_inserters(game):
    """
    Place inserters at each cardinal direction
    :param game:
    :return:
    """
    # move to the nearest water source
    entity = Prototype.BurnerInserter
    location = game.nearest(Resource.Coal)
    game.move_to(Position(x=location.x - 10, y=location.y))
    offshore_pump = game.place_entity(entity,
                                      position=location,
                                      direction=Direction.LEFT)
    assert offshore_pump.direction.value == Direction.LEFT.value
    game.move_to(Position(x=location.x, y=location.y))
    offshore_pump = game.place_entity(entity,
                                      position=location,
                                      direction=Direction.RIGHT)
    assert offshore_pump.direction.value == Direction.RIGHT.value
    game.move_to(Position(x=location.x, y=location.y))
    offshore_pump = game.place_entity(entity,
                                      position=location,
                                      direction=Direction.UP)
    assert offshore_pump.direction.value == Direction.UP.value
    game.move_to(Position(x=location.x, y=location.y))
    offshore_pump = game.place_entity(entity,
                                      position=location,
                                      direction=Direction.DOWN)
    assert offshore_pump.direction.value == Direction.DOWN.value

def test_place_burner_mining_drills(game):
    """
    Place mining drills at each cardinal direction
    :param game:
    :return:
    """
    # move to the nearest water source
    entity = Prototype.BurnerMiningDrill
    location = game.nearest(Resource.IronOre)
    game.move_to(Position(x=location.x - 10, y=location.y))
    offshore_pump = game.place_entity(entity,
                                      position=location,
                                      direction=Direction.LEFT)
    assert offshore_pump.direction.value == Direction.LEFT.value
    game.move_to(Position(x=location.x, y=location.y))
    offshore_pump = game.place_entity(entity,
                                      position=location,
                                      direction=Direction.RIGHT)
    assert offshore_pump.direction.value == Direction.RIGHT.value
    game.move_to(Position(x=location.x, y=location.y))
    offshore_pump = game.place_entity(entity,
                                      position=location,
                                      direction=Direction.UP)
    assert offshore_pump.direction.value == Direction.UP.value
    game.move_to(Position(x=location.x, y=location.y))
    offshore_pump = game.place_entity(entity,
                                      position=location,
                                      direction=Direction.DOWN)
    assert offshore_pump.direction.value == Direction.DOWN.value