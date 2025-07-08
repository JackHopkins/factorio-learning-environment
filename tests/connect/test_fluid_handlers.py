import pytest

from fle.env.entities import Position, BuildingBox
from fle.env import DirectionInternal as Direction
from fle.env.game_types import Prototype, Resource


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        "stone-furnace": 10,
        "burner-inserter": 50,
        "offshore-pump": 4,
        "pipe": 300,
        "pipe-to-ground": 100,
        "small-electric-pole": 50,
        "transport-belt": 200,
        "coal": 100,
        "wooden-chest": 1,
        "assembling-machine-1": 10,
        "boiler": 3,
        "steam-engine": 3,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


def create_electricity_connection(game, steam_engine_pos, boiler_pos):
    water_pos = game.nearest(Resource.Water)
    game.move_to(water_pos)
    offshore_pump = game.place_entity(Prototype.OffshorePump, position=water_pos)
    print(offshore_pump)
    game.move_to(boiler_pos)
    boiler = game.place_entity(Prototype.Boiler, position=boiler_pos)
    game.insert_item(Prototype.Coal, boiler, 20)
    water_pipes = game.connect_entities(
        offshore_pump, boiler, {Prototype.Pipe, Prototype.UndergroundPipe}
    )

    game.move_to(steam_engine_pos)
    engine = game.place_entity(Prototype.SteamEngine, position=steam_engine_pos)
    steam_pipes = game.connect_entities(
        boiler, engine, {Prototype.Pipe, Prototype.UndergroundPipe}
    )
    engine = game.get_entity(Prototype.SteamEngine, engine.position)

    assert steam_pipes
    assert water_pipes
    assert engine.energy > 0


def test_electricity_far_west_configuration(game):
    """Test electricity connection with steam engine far west of boiler"""
    boiler_pos = Position(x=-15.5, y=-5.5)
    steam_engine_pos = boiler_pos.left(20).up(10)
    create_electricity_connection(game, steam_engine_pos, boiler_pos)


def test_electricity_vertical_close_configuration(game):
    """Test electricity connection with steam engine directly above boiler"""
    boiler_pos = Position(x=-5.5, y=0.5)
    steam_engine_pos = boiler_pos.up(4)
    create_electricity_connection(game, steam_engine_pos, boiler_pos)
    pass


def test_electricity_northwest_configuration(game):
    """Test electricity connection with steam engine northwest of boiler"""
    boiler_pos = Position(x=-5.5, y=4.5)
    steam_engine_pos = boiler_pos.up(15).left(15)
    create_electricity_connection(game, steam_engine_pos, boiler_pos)


def test_electricity_far_west_horizontal_configuration(game):
    """Test electricity connection with steam engine far west on same y-level"""
    boiler_pos = Position(x=-5.5, y=4.5)
    steam_engine_pos = boiler_pos.left(20)
    create_electricity_connection(game, steam_engine_pos, boiler_pos)


def test_electricity_east_configuration(game):
    """Test electricity connection with steam engine east of boiler"""
    boiler_pos = Position(x=-5.5, y=-2.5)
    steam_engine_pos = boiler_pos.right(5)
    create_electricity_connection(game, steam_engine_pos, boiler_pos)


def test_electricity_vertical_below_configuration(game):
    """Test electricity connection with steam engine below boiler"""
    boiler_pos = Position(x=-5.5, y=-2.5)
    steam_engine_pos = boiler_pos.down(5)
    create_electricity_connection(game, steam_engine_pos, boiler_pos)
    pass


def test_electricity_southwest_configuration(game):
    """Test electricity connection with steam engine southwest of boiler"""
    steam_engine_pos = Position(x=-15.5, y=-7.5)
    boiler_pos = Position(x=-5.5, y=-2.5)
    create_electricity_connection(game, steam_engine_pos, boiler_pos)


def test_electricity_southwest_far_configuration(game):
    """Test electricity connection with steam engine far southwest of boiler"""
    steam_engine_pos = Position(x=-15.5, y=-7.5)
    boiler_pos = Position(x=-5.5, y=5.5)
    create_electricity_connection(game, steam_engine_pos, boiler_pos)


def test_electricity_southwest_offset_configuration(game):
    """Test electricity connection with steam engine southwest of offset boiler"""
    steam_engine_pos = Position(x=-15.5, y=-7.5)
    boiler_pos = Position(x=-8.5, y=5.5)
    create_electricity_connection(game, steam_engine_pos, boiler_pos)
    pass


def test_electricity_south_configuration(game):
    """Test electricity connection with steam engine south of boiler"""
    steam_engine_pos = Position(x=-5.5, y=-7.5)
    boiler_pos = Position(x=-8.5, y=5.5)
    create_electricity_connection(game, steam_engine_pos, boiler_pos)
    pass


def test_electricity_north_configuration(game):
    """Test electricity connection with steam engine north of boiler"""
    steam_engine_pos = Position(x=8.5, y=15.5)
    boiler_pos = Position(x=8.5, y=5.5)
    create_electricity_connection(game, steam_engine_pos, boiler_pos)
    pass


def test_electricity_southwest_horizontal_configuration(game):
    """Test electricity connection with steam engine southwest on same y-level"""
    steam_engine_pos = Position(x=8.5, y=4.5)
    boiler_pos = Position(x=0.5, y=-5.5)
    create_electricity_connection(game, steam_engine_pos, boiler_pos)
    pass


def test_connect_steam_engines(game):
    steam_engine_pos1 = Position(x=0, y=4.5)
    game.move_to(steam_engine_pos1)
    engine1 = game.place_entity(Prototype.SteamEngine, position=steam_engine_pos1)

    steam_engine_pos2 = Position(x=5, y=4.5)
    game.move_to(steam_engine_pos2)
    engine2 = game.place_entity(Prototype.SteamEngine, position=steam_engine_pos2)

    game.connect_entities(engine1, engine2, Prototype.Pipe)
    game.connect_entities(engine1, engine2, Prototype.Pipe)

    assert True


def test_connect_boilers(game):
    pos1 = Position(x=0, y=4.5)
    game.move_to(pos1)
    boiler1 = game.place_entity(Prototype.Boiler, position=pos1)

    pos2 = Position(x=5, y=4.5)
    game.move_to(pos2)
    boiler2 = game.place_entity(Prototype.Boiler, position=pos2)

    game.connect_entities(boiler1, boiler2, Prototype.Pipe)

    assert True


def test_multiple(game):
    # Find water source for power system
    water_pos = Position(x=-1.0, y=28.0)
    print(f"Found water source at {water_pos}")

    # Place offshore pump
    game.move_to(water_pos)
    offshore_pump = game.place_entity(Prototype.OffshorePump, position=water_pos)
    print(f"Placed offshore pump at {offshore_pump.position}")

    # Place boiler next to pump
    building_box = BuildingBox(width=3, height=3)
    buildable_coords = game.nearest_buildable(
        Prototype.Boiler, building_box, offshore_pump.position
    )
    boiler_pos = Position(
        x=buildable_coords.left_top.x + 1.5, y=buildable_coords.left_top.y + 1.5
    )
    game.move_to(boiler_pos)
    boiler = game.place_entity(Prototype.Boiler, position=boiler_pos)
    print(f"Placed boiler at {boiler.position}")

    # Place steam engine next to boiler
    building_box = BuildingBox(width=3, height=5)
    buildable_coords = game.nearest_buildable(
        Prototype.SteamEngine, building_box, boiler.position
    )
    engine_pos = (
        buildable_coords.center
    )  # Position(x=buildable_coords.left_top.x, y=buildable_coords.left_top.y)
    game.move_to(engine_pos)
    steam_engine = game.place_entity(Prototype.SteamEngine, position=engine_pos)
    print(f"Placed steam engine at {steam_engine.position}")

    # Connect offshore pump to boiler with pipes
    pump_to_boiler = game.connect_entities(
        offshore_pump.position, boiler.position, Prototype.Pipe
    )
    print(f"Connected offshore pump to boiler with pipes: {pump_to_boiler}")

    # Connect boiler to steam engine with pipes
    boiler_to_engine = game.connect_entities(
        boiler.position, steam_engine.position, Prototype.Pipe
    )
    print(f"Connected boiler to steam engine with pipes: {boiler_to_engine}")


def test_for_attribute_error(game):
    boiler_position = Position(x=2.5, y=29.5)
    game.move_to(boiler_position)
    boiler = game.place_entity(Prototype.Boiler, position=boiler_position)
    offshore_pump_pos = Position(x=-0, y=29)
    pump = game.place_entity(
        Prototype.OffshorePump, position=offshore_pump_pos, direction=Direction.UP
    )
    game.connect_entities(pump, boiler, Prototype.Pipe)
    try:
        engine = game.place_entity(
            Prototype.SteamEngine, position=Position(x=8.5, y=28.5)
        )
        game.connect_entities(engine, boiler, Prototype.Pipe)
    except Exception as e:
        # fail the test if the exception is an AttributeError
        assert not isinstance(e, AttributeError)
