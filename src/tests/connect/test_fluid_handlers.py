import math
from typing import List

import pytest

from factorio_entities import Entity, Position, PipeGroup, EntityStatus, ResourcePatch
from factorio_instance import Direction
from factorio_types import Prototype, Resource, PrototypeName


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        **instance.initial_inventory,
        'stone-furnace': 10,
        'burner-inserter': 50,
        'offshore-pump': 4,
        'pipe': 300,
        'small-electric-pole': 50,
        'transport-belt': 200,
        'coal': 100,
        'wooden-chest': 1,
        'assembling-machine-1': 10,
        'boiler': 3,
        'steam-engine': 3
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


def create_electriciy_connection(game, steam_engine_pos, boiler_pos):
    water_pos = game.nearest(Resource.Water)
    game.move_to(water_pos)
    offshore_pump = game.place_entity(Prototype.OffshorePump,position = water_pos)
    print(offshore_pump)
    game.move_to(boiler_pos)
    boiler =  game.place_entity(Prototype.Boiler, position = boiler_pos)
    game.insert_item(Prototype.Coal, boiler, 20)
    water_pipes = game.connect_entities(offshore_pump, boiler, Prototype.Pipe)
    assert len(water_pipes) == 1
    game.move_to(steam_engine_pos)
    engine = game.place_entity(Prototype.SteamEngine, position = steam_engine_pos)
    steam_pipes = game.connect_entities(boiler, engine, Prototype.Pipe)
    assert len(steam_pipes) ==1
    engine=game.get_entity(Prototype.SteamEngine, engine.position)
    assert engine.energy > 0


def test_working_configurations(game):
    position_tuples = [
        (Position(x=-20.5, y=8.5), Position(x=-15.5, y=-5.5)),
        (Position(x=-8.5, y=4.5), Position(x=-15.5, y=-5.5)), 
        (Position(x=-5.5, y=4.5), Position(x=-5.5, y=0.5)),
        (Position(x=-10, y=11.5), Position(x=-5.5, y=4.5)),
        (Position(x=-22, y=4.5),  Position(x=-5.5, y=4.5)),
        (Position(x=10, y=-3.5), Position(x=-5.5, y=-2.5)),
        (Position(x=-5.5, y=-7.5), Position(x=-5.5, y=-2.5)),
        (Position(x=-15.5, y=-7.5), Position(x=-5.5, y=-2.5)),
        (Position(x=-15.5, y=-7.5), Position(x=-5.5, y=5.5)),
        (Position(x=-15.5, y=-7.5), Position(x=-8.5, y=5.5)),
        (Position(x=-5.5, y=-7.5), Position(x=-8.5, y=5.5)),
        (Position(x=-8.5, y=10.5), Position(x=-8.5, y=5.5))
    ]
    
    for steam_engine_pos, boiler_pos in position_tuples:
        create_electriciy_connection(game, steam_engine_pos, boiler_pos)
        game.reset()
        

