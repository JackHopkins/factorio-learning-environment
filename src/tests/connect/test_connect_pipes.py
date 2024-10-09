import math
from typing import List

import pytest

from factorio_entities import Entity, Position
from factorio_instance import Direction
from factorio_types import Prototype, Resource, PrototypeName


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        'stone-furnace': 10,
        'burner-inserter': 50,
        'offshore-pump': 4,
        'pipe': 100,
        'small-electric-pole': 50,
        'transport-belt': 200,
        'coal': 100,
        'wooden-chest': 1,
        PrototypeName.AssemblingMachine.value: 10,
    }
    instance.reset()
    yield instance
    instance.reset()

def test_connect_offshore_pump_to_boiler(game):
    #game.craft_item(Prototype.OffshorePump)

    water_patch = game.get_resource_patch(Resource.Water, game.nearest(Resource.Water))
    game.move_to(water_patch.bounding_box.left_top)
    offshore_pump = game.place_entity(Prototype.OffshorePump,
                                      position=game.nearest(Resource.Water))
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                       reference_position=offshore_pump.position,
                                       direction=offshore_pump.direction,
                                       spacing=5)
    water_pipes = game.connect_entities(boiler, offshore_pump, connection_type=Prototype.Pipe)
    assert len(water_pipes) == 5 + boiler.tile_dimensions.tile_width/2 + offshore_pump.tile_dimensions.tile_width/2 + 1

    game.move_to(water_patch.bounding_box.right_bottom)
    offshore_pump = game.place_entity(Prototype.OffshorePump,
                                      position=game.nearest(Resource.Water),
                                      direction=Direction.RIGHT)
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                        reference_position=offshore_pump.position,
                                        direction=offshore_pump.direction,
                                        spacing=5)
    assert boiler.direction.value == Direction.RIGHT.value
    water_pipes = game.connect_entities(boiler, offshore_pump, connection_type=Prototype.Pipe)
    assert len(water_pipes) == math.ceil(5 + boiler.tile_dimensions.tile_height/2 + offshore_pump.tile_dimensions.tile_height/2 + 1)

    offshore_pump = game.place_entity(Prototype.OffshorePump,
                                      position=game.nearest(Resource.Water),
                                      direction=Direction.DOWN)
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                       reference_position=offshore_pump.position,
                                       direction=offshore_pump.direction,
                                       spacing=5)
    assert boiler.direction.value == Direction.DOWN.value
    water_pipes = game.connect_entities(boiler, offshore_pump, connection_type=Prototype.Pipe)
    assert len(water_pipes) == math.ceil(5 + boiler.tile_dimensions.tile_height / 2 + offshore_pump.tile_dimensions.tile_height / 2 + 1)

    game.move_to(Position(x=-30, y=0))
    offshore_pump = game.place_entity(Prototype.OffshorePump,
                                      position=game.nearest(Resource.Water),
                                      direction=Direction.LEFT)
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                       reference_position=offshore_pump.position,
                                       direction=offshore_pump.direction,
                                       spacing=5)
    assert boiler.direction.value == Direction.LEFT.value
    water_pipes = game.connect_entities(boiler, offshore_pump, connection_type=Prototype.Pipe)
    assert len(water_pipes) == math.ceil(
        5 + boiler.tile_dimensions.tile_width / 2 + offshore_pump.tile_dimensions.tile_width / 2 + 1)

def test_connect_steam_engines_to_boilers_using_pipes(game):
    """
    Place a boiler and a steam engine next to each other in 3 cardinal directions.
    :param game:
    :return:
    """
    boilers_in_inventory = game.inspect_inventory()[Prototype.Boiler]
    steam_engines_in_inventory = game.inspect_inventory()[Prototype.SteamEngine]
    pipes_in_inventory = game.inspect_inventory()[Prototype.Pipe]

    boiler: Entity = game.place_entity(Prototype.Boiler, position=Position(x=0, y=0), direction=Direction.UP)
    assert boiler.direction.value == Direction.UP.value
    game.move_to(Position(x=0, y=10))
    steam_engine: Entity = game.place_entity(Prototype.SteamEngine, position=Position(x=0, y=10), direction=Direction.UP)
    assert steam_engine.direction.value == Direction.UP.value

    connection: List[Entity] = game.connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)
    # check to see if the steam engine has water
    #inspection = game.inspect_entities(position=steam_engine.position)

    #assert inspection.get_entity(Prototype.SteamEngine).warning == 'not receiving electricity'
    assert boilers_in_inventory - 1 == game.inspect_inventory()[Prototype.Boiler]
    assert steam_engines_in_inventory - 1 == game.inspect_inventory()[Prototype.SteamEngine]
    assert pipes_in_inventory - len(connection) == game.inspect_inventory()[Prototype.Pipe]
    assert len(connection) >= 10

    game.reset()

    # Define the offsets for the four cardinal directions
    offsets = [Position(x=10, y=0), Position(x=0, y=-10), Position(x=-10, y=0)]  # Up, Right, Down, Left  (0, -10),
    directions = [Direction.RIGHT, Direction.UP, Direction.LEFT]
    for offset, direction in zip(offsets, directions):
        boiler: Entity = game.place_entity(Prototype.Boiler, position=Position(x=0, y=0),direction=direction)
        game.move_to(offset)

        steam_engine: Entity = game.place_entity(Prototype.SteamEngine, position=offset,direction=direction)

        try:
            connection: List[Entity] = game.connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)
        except Exception as e:
            print(e)
            assert False
        assert boilers_in_inventory - 1 == game.inspect_inventory()[Prototype.Boiler]
        assert steam_engines_in_inventory - 1 == game.inspect_inventory()[Prototype.SteamEngine]

        current_pipes_in_inventory = game.inspect_inventory()[Prototype.Pipe]
        spent_pipes = (pipes_in_inventory - current_pipes_in_inventory)
        assert spent_pipes == len(connection)

        # check to see if the steam engine has water
        inspection = game.inspect_entities(position=steam_engine.position)
        #assert inspection.get_entity(Prototype.SteamEngine).warning == 'not receiving electricity'

        game.reset()  # Reset the game state after each iteration

def test_connect_steam_engine_boiler_nearly_adjacent(game):
    """
    We've had problems with gaps of exactly 2.
    :param game:
    :return:
    """
    # place the offshore pump at nearest water source
    game.move_to(Position(x=-30, y=12))
    game.move_to(game.nearest(Resource.Water))
    offshore_pump = game.place_entity(Prototype.OffshorePump,
                                      position=game.nearest(Resource.Water),
                                      direction=Direction.LEFT)

    # place the boiler next to the offshore pump
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                       reference_position=offshore_pump.position,
                                       direction=offshore_pump.direction,
                                       spacing=2)

    # place the steam engine next to the boiler
    steam_engine = game.place_entity_next_to(Prototype.SteamEngine,
                                             reference_position=boiler.position,
                                             direction=boiler.direction,
                                             spacing=2)

    # place connective pipes between the boiler and steam engine
    game.connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)

    game.connect_entities(offshore_pump, boiler, connection_type=Prototype.Pipe)

    # insert coal into boiler
    game.insert_item(Prototype.Coal, boiler, 50)

    # check to see if the steam engine has water
    inspection = game.inspect_entities(position=steam_engine.position)

    assert inspection.get_entity(Prototype.SteamEngine).warning == 'not connected to power network'