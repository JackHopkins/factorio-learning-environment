import math
from time import sleep
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
def test_connect_steam_engine_to_assembler_with_electricity_poles(game):
    """
    Place a steam engine and an assembling machine next to each other.
    Connect them with electricity poles.
    :param game:
    :return:
    """
    steam_engine = game.place_entity(Prototype.SteamEngine, position=Position(x=0, y=0))
    assembler = game.place_entity_next_to(Prototype.AssemblingMachine1, reference_position=steam_engine.position,
                                          direction=game.RIGHT, spacing=10)
    game.move_to(Position(x=5, y=5))
    diagonal_assembler = game.place_entity(Prototype.AssemblingMachine1, position=Position(x=10, y=10))

    # check to see if the assemblers are connected to the electricity network
    inspected_assemblers = game.inspect_entities(position=diagonal_assembler.position, radius=50).get_entities(
        Prototype.AssemblingMachine1)

    for a in inspected_assemblers:
        assert a.warning == 'not connected to power network'

    poles_in_inventory = game.inspect_inventory()[Prototype.SmallElectricPole]

    poles = game.connect_entities(steam_engine, assembler, connection_type=Prototype.SmallElectricPole)
    poles2 = game.connect_entities(steam_engine, diagonal_assembler, connection_type=Prototype.SmallElectricPole)

    current_poles_in_inventory = game.inspect_inventory()[Prototype.SmallElectricPole]
    spent_poles = (poles_in_inventory - current_poles_in_inventory)

    assert spent_poles == len(poles + poles2)

    # check to see if the assemblers are connected to the electricity network
    inspected_assemblers = game.inspect_entities(position=diagonal_assembler.position, radius=50).get_entities(Prototype.AssemblingMachine1)

    for assembler in inspected_assemblers:
        assert assembler.warning == 'not receiving electricity'
