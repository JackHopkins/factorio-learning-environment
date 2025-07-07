import pytest

from fle.env.entities import Position, Direction
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


def test_place(game):
    """
    Place a boiler at (0, 0)
    :param game:
    :return:
    """
    boilers_in_inventory = game.inspect_inventory()[Prototype.Boiler]
    game.place_entity(Prototype.Boiler, position=(0, 0))
    assert boilers_in_inventory - 1 == game.inspect_inventory()[Prototype.Boiler]


def test_drill_with_expected_resources(game):
    """
    Place a boiler at (0, 0)
    :param game:
    :return:
    """
    game.move_to(game.nearest(Resource.IronOre))
    drill = game.place_entity(
        Prototype.BurnerMiningDrill, position=game.nearest(Resource.IronOre)
    )
    assert drill  # - 1 == game.inspect_inventory()[Prototype.Boiler]


def test_fail_when_placing_on_the_same_place(game):
    """
    Place a boiler at (0, 0)
    :param game:
    :return:
    """
    game.place_entity(Prototype.Pipe, position=(0, 0))
    try:
        game.place_entity(Prototype.Pipe, position=(0, 0))
        assert False
    except:
        assert True


def test_place_transport_belt_next_to_miner(game):
    """
    Place a transport belt next to a burner mining drill
    :param game:
    :return:
    """
    iron_position = game.get_resource_patch(
        Resource.IronOre, game.nearest(Resource.IronOre)
    ).bounding_box.center
    game.move_to(iron_position)
    drill = game.place_entity(
        Prototype.BurnerMiningDrill, position=iron_position, exact=True
    )
    for y in range(-1, 3, 1):
        world_y = y + drill.position.y
        world_x = -1.0 + drill.position.x - 1
        game.move_to(Position(x=world_x, y=world_y))
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=world_x, y=world_y),
            direction=Direction.UP,
            exact=True,
        )

    # belt = game.place_entity(Prototype.TransportBelt, direction=Direction.RIGHT, position=iron_position + Position(x=-1, y=0))
    # assert belt is not None
    # assert belt.direction == Direction.RIGHT
    pass


def test_place_wall(game):
    """
    Place a wall at (0, 0)
    :param game:
    :return:
    """
    walls_in_inventory = game.inspect_inventory()[Prototype.StoneWall]
    game.place_entity(Prototype.StoneWall, position=(0, 0))
    assert walls_in_inventory - 1 == game.inspect_inventory()[Prototype.StoneWall]


def test_place_in_all_directions(game):
    """
    Place a burner inserters in each direction
    :param game:
    :return:
    """
    down = game.place_entity(
        Prototype.BurnerInserter, position=(0, 1), direction=Direction.DOWN
    )
    left = game.place_entity(
        Prototype.BurnerInserter, position=(-1, 0), direction=Direction.LEFT
    )
    right = game.place_entity(
        Prototype.BurnerInserter, position=(1, 0), direction=Direction.RIGHT
    )
    up = game.place_entity(
        Prototype.BurnerInserter, position=(0, -1), direction=Direction.UP
    )

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
    assert boilers_in_inventory == game.inspect_inventory()[Prototype.Boiler]


def test_place_offshore_pumps(game):
    """
    Place offshore pumps at each cardinal direction
    :param game:
    :return:
    """
    # move to the nearest water source
    entity = Prototype.OffshorePump
    water_location = game.nearest(Resource.Water)
    water_patch = game.get_resource_patch(Resource.Water, water_location)

    left_of_water_patch = Position(
        x=water_patch.bounding_box.left_top.x, y=water_patch.bounding_box.center.y
    )
    game.move_to(left_of_water_patch)
    offshore_pump = game.place_entity(
        entity, position=left_of_water_patch, direction=Direction.LEFT
    )
    assert offshore_pump.direction.value == Direction.LEFT.value

    right_of_water_patch = Position(
        x=water_patch.bounding_box.right_bottom.x, y=water_patch.bounding_box.center.y
    )
    game.move_to(right_of_water_patch)
    offshore_pump = game.place_entity(
        entity, position=right_of_water_patch, direction=Direction.RIGHT
    )
    assert offshore_pump.direction.value == Direction.RIGHT.value

    above_water_patch = Position(
        x=water_patch.bounding_box.center.x, y=water_patch.bounding_box.left_top.y
    )
    game.move_to(above_water_patch)
    offshore_pump = game.place_entity(
        entity, position=above_water_patch, direction=Direction.UP
    )
    assert offshore_pump.direction.value == Direction.UP.value

    below_water_patch = Position(
        x=water_patch.bounding_box.center.x, y=water_patch.bounding_box.right_bottom.y
    )
    game.move_to(below_water_patch)
    offshore_pump = game.place_entity(
        entity, position=below_water_patch, direction=Direction.DOWN
    )
    assert offshore_pump.direction.value == Direction.DOWN.value


def test_place_offshore_pumps_no_default_direction(game):
    """
    Place offshore pumps at each cardinal direction
    :param game:
    :return:
    """
    # move to the nearest water source
    entity = Prototype.OffshorePump
    water_location = game.nearest(Resource.Water)
    water_patch = game.get_resource_patch(Resource.Water, water_location)

    left_of_water_patch = Position(
        x=water_patch.bounding_box.left_top.x, y=water_patch.bounding_box.center.y
    )
    game.move_to(left_of_water_patch)
    offshore_pump = game.place_entity(entity, position=left_of_water_patch)
    assert offshore_pump.direction.value == Direction.LEFT.value
    assert offshore_pump.connection_points

    right_of_water_patch = Position(
        x=water_patch.bounding_box.right_bottom.x, y=water_patch.bounding_box.center.y
    )
    game.move_to(right_of_water_patch)
    offshore_pump = game.place_entity(entity, position=right_of_water_patch)
    assert offshore_pump.direction.value == Direction.RIGHT.value
    assert offshore_pump.connection_points

    above_water_patch = Position(
        x=water_patch.bounding_box.center.x, y=water_patch.bounding_box.left_top.y
    )
    game.move_to(above_water_patch)
    offshore_pump = game.place_entity(entity, position=above_water_patch)
    assert offshore_pump.direction.value == Direction.UP.value
    assert offshore_pump.connection_points

    below_water_patch = Position(
        x=water_patch.bounding_box.center.x, y=water_patch.bounding_box.right_bottom.y
    )
    game.move_to(below_water_patch)
    offshore_pump = game.place_entity(entity, position=below_water_patch)
    assert offshore_pump.direction.value == Direction.DOWN.value
    assert offshore_pump.connection_points


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
    offshore_pump = game.place_entity(
        entity, position=location, direction=Direction.LEFT
    )
    assert offshore_pump.direction.value == Direction.LEFT.value
    game.instance.reset()

    game.move_to(Position(x=location.x, y=location.y))
    offshore_pump = game.place_entity(
        entity, position=location, direction=Direction.RIGHT
    )
    assert offshore_pump.direction.value == Direction.RIGHT.value
    game.instance.reset()

    game.move_to(Position(x=location.x, y=location.y))
    offshore_pump = game.place_entity(entity, position=location, direction=Direction.UP)
    assert offshore_pump.direction.value == Direction.UP.value
    game.instance.reset()

    game.move_to(Position(x=location.x, y=location.y))
    offshore_pump = game.place_entity(
        entity, position=location, direction=Direction.DOWN
    )
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
    drill = game.place_entity(entity, position=location, direction=Direction.LEFT)
    assert drill.direction.value == Direction.LEFT.value
    game.instance.reset()

    game.move_to(Position(x=location.x, y=location.y))
    drill = game.place_entity(entity, position=location, direction=Direction.RIGHT)
    assert drill.direction.value == Direction.RIGHT.value
    game.instance.reset()

    game.move_to(Position(x=location.x, y=location.y))
    drill = game.place_entity(entity, position=location, direction=Direction.UP)
    assert drill.direction.value == Direction.UP.value
    game.instance.reset()

    game.move_to(Position(x=location.x, y=location.y))
    drill = game.place_entity(entity, position=location, direction=Direction.DOWN)
    assert drill.direction.value == Direction.DOWN.value
    game.instance.reset()


def test_placed_drill_status(game):
    iron_position = game.nearest(Resource.IronOre)
    game.move_to(iron_position)
    drill = game.place_entity(Prototype.BurnerMiningDrill, position=iron_position)
    game.insert_item(Prototype.Coal, drill, 5)
    game.sleep(1)
    drill = game.get_entity(Prototype.BurnerMiningDrill, drill.position)
    assert drill.energy > 0


def test_place_splitter(game):
    """
    Place a splitter at (0, 0)
    :param game:
    :return:
    """
    splitters_in_inventory = game.inspect_inventory()[Prototype.Splitter]
    splitter = game.place_entity(
        Prototype.Splitter, position=(0, 2), direction=Direction.UP
    )
    assert splitter.direction.value == Direction.UP.value
    splitter = game.place_entity(
        Prototype.Splitter,
        position=splitter.output_positions[0],
        direction=Direction.DOWN,
    )
    assert splitter.direction.value == Direction.DOWN.value
    splitter = game.place_entity(
        Prototype.Splitter, position=(2, 0), direction=Direction.RIGHT
    )
    assert splitter.direction.value == Direction.RIGHT.value
    splitter = game.place_entity(
        Prototype.Splitter,
        position=splitter.output_positions[0],
        direction=Direction.LEFT,
    )
    assert splitter.direction.value == Direction.LEFT.value
    assert splitters_in_inventory - 4 == game.inspect_inventory()[Prototype.Splitter]


def test_place_generator(game):
    """
    Place a steam engine at (0,0)
    """

    game.place_entity(
        Prototype.SteamEngine, position=Position(x=0, y=0), direction=Direction.UP
    )

    pass


def test_place_too_far_away(game):
    try:
        game.place_entity(Prototype.BurnerMiningDrill, position=Position(x=100, y=0))
    except Exception:
        assert True


def test_place_at_drop_position(game):
    iron_ore = game.nearest(Resource.IronOre)
    game.move_to(iron_ore)

    drill = game.place_entity(Prototype.BurnerMiningDrill, position=iron_ore)
    chest = game.place_entity(Prototype.WoodenChest, position=drill.drop_position)

    assert chest.position.is_close(drill.drop_position)


def test_cannot_place_at_water(game):
    steam_engine_pos = Position(x=-20.5, y=8.5)
    game.move_to(steam_engine_pos)
    try:
        engine = game.place_entity(Prototype.SteamEngine, position=steam_engine_pos)  # noqa
        failed = True
    except:
        failed = False
    assert not failed
