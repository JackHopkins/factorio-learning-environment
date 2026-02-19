"""
Shared fixtures for Factorio 2.0 invariant tests.

These fixtures provide common setup for testing game mechanics invariants
based on Factorio 2.0 API documentation.
"""

import pytest

from fle.env.game_types import Resource


@pytest.fixture()
def game_with_full_inventory(instance):
    """
    Fixture providing a game instance with comprehensive inventory for invariant tests.
    Includes items for fluid systems, power, belts, and production testing.
    """
    instance.initial_inventory = {
        # Basic resources
        "coal": 200,
        "iron-plate": 200,
        "copper-plate": 200,
        "steel-plate": 50,
        "stone": 100,
        # Fluid system entities
        "offshore-pump": 5,
        "pipe": 200,
        "pipe-to-ground": 50,
        "storage-tank": 5,
        "pump": 5,
        # Power system entities
        "boiler": 5,
        "steam-engine": 5,
        "small-electric-pole": 50,
        "medium-electric-pole": 10,
        "solar-panel": 5,
        "accumulator": 5,
        # Production entities
        "assembling-machine-1": 10,
        "assembling-machine-2": 5,
        "stone-furnace": 10,
        "electric-furnace": 5,
        # Mining entities
        "burner-mining-drill": 10,
        "electric-mining-drill": 5,
        # Transport entities
        "transport-belt": 200,
        "fast-transport-belt": 100,
        "express-transport-belt": 50,
        "underground-belt": 20,
        "fast-underground-belt": 10,
        "express-underground-belt": 5,
        "splitter": 10,
        "fast-splitter": 5,
        "express-splitter": 5,
        # Inserters
        "burner-inserter": 50,
        "inserter": 50,
        "fast-inserter": 20,
        "long-handed-inserter": 10,
        # Storage
        "wooden-chest": 20,
        "iron-chest": 10,
        # Research
        "lab": 3,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


@pytest.fixture()
def game_near_water(instance):
    """
    Fixture that positions the player near water for fluid system tests.
    """
    instance.initial_inventory = {
        "offshore-pump": 5,
        "pipe": 100,
        "pipe-to-ground": 20,
        "boiler": 5,
        "steam-engine": 5,
        "coal": 100,
        "small-electric-pole": 20,
        "storage-tank": 3,
    }
    instance.reset()
    game = instance.namespace

    # Move to nearest water
    water_pos = game.nearest(Resource.Water)
    if water_pos:
        game.move_to(water_pos)

    yield game
    instance.reset()


@pytest.fixture()
def game_with_power_setup(instance):
    """
    Fixture providing entities for power network testing.
    """
    instance.initial_inventory = {
        "offshore-pump": 3,
        "pipe": 50,
        "boiler": 3,
        "steam-engine": 3,
        "coal": 100,
        "small-electric-pole": 30,
        "medium-electric-pole": 10,
        "big-electric-pole": 5,
        "solar-panel": 10,
        "accumulator": 5,
        "assembling-machine-1": 5,
        "electric-mining-drill": 5,
        "lab": 3,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


@pytest.fixture()
def game_with_belts(instance):
    """
    Fixture providing comprehensive belt inventory for transport testing.
    """
    instance.initial_inventory = {
        "transport-belt": 200,
        "fast-transport-belt": 100,
        "express-transport-belt": 50,
        "underground-belt": 30,
        "fast-underground-belt": 20,
        "express-underground-belt": 10,
        "splitter": 20,
        "fast-splitter": 10,
        "express-splitter": 5,
        "inserter": 50,
        "wooden-chest": 20,
        "iron-plate": 200,
        "copper-plate": 100,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()
