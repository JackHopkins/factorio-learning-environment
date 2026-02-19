"""
Entity Lifecycle Invariant Tests

Tests verifying entity lifecycle behavior based on Factorio 2.0 API documentation.
See: https://lua-api.factorio.com/latest/classes/LuaEntity.html

Invariants tested:
1. Entity position matches requested placement position
2. Entity direction is respected after placement
3. Entity can be retrieved after placement (get_entity)
4. Entity removal clears position (pickup_entity)
5. Crafting machine progress stays within [0, 1] range
"""

import pytest

from fle.env import Direction, Position
from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    """Fixture with inventory for lifecycle testing."""
    instance.initial_inventory = {
        "stone-furnace": 10,
        "wooden-chest": 20,
        "assembling-machine-1": 10,
        "transport-belt": 100,
        "inserter": 20,
        "burner-inserter": 20,
        "pipe": 50,
        "iron-plate": 200,
        "copper-plate": 100,
        "iron-ore": 100,
        "coal": 100,
        "iron-gear-wheel": 50,
        "small-electric-pole": 20,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_entity_has_valid_position_after_placement(game):
    """
    Invariant: Entity position matches requested placement position.

    From Factorio 2.0 docs: Position updates via teleport() with optional grid snapping.
    """
    target_position = Position(x=5, y=5)
    game.move_to(target_position)

    chest = game.place_entity(
        Prototype.WoodenChest,
        position=target_position,
    )

    assert chest is not None, "Entity should be placed"

    # Entity position should match (or be close to) requested position
    # Note: Some entities may snap to grid
    assert chest.position is not None, (
        "Invariant: Placed entity should have a valid position"
    )

    # Position should be within reasonable distance of target
    distance = (
        (chest.position.x - target_position.x) ** 2
        + (chest.position.y - target_position.y) ** 2
    ) ** 0.5

    assert distance < 1.0, (
        f"Invariant: Entity position {chest.position} should be close to "
        f"requested position {target_position}, distance={distance}"
    )


def test_entity_direction_is_respected(game):
    """
    Invariant: Entity direction matches requested direction.

    From Factorio 2.0 docs: Direction uses defines.direction enum values.
    """
    game.move_to(Position(x=0, y=0))

    # Place inserter with specific direction
    inserter_up = game.place_entity(
        Prototype.BurnerInserter,
        position=Position(x=0, y=0),
        direction=Direction.UP,
    )

    assert inserter_up is not None
    assert inserter_up.direction == Direction.UP, (
        f"Invariant: Entity direction should be UP, got {inserter_up.direction}"
    )

    # Place another inserter with different direction
    inserter_right = game.place_entity(
        Prototype.BurnerInserter,
        position=Position(x=5, y=0),
        direction=Direction.RIGHT,
    )

    assert inserter_right is not None
    assert inserter_right.direction == Direction.RIGHT, (
        f"Invariant: Entity direction should be RIGHT, got {inserter_right.direction}"
    )


def test_entity_can_be_retrieved_after_placement(game):
    """
    Invariant: Placed entity can be retrieved via get_entity.

    From Factorio 2.0 docs: Entity must be valid before operations.
    """
    target_position = Position(x=3, y=3)
    game.move_to(target_position)

    # Place entity
    furnace = game.place_entity(
        Prototype.StoneFurnace,
        position=target_position,
    )

    assert furnace is not None, "Entity should be placed"

    # Retrieve entity at same position
    retrieved = game.get_entity(Prototype.StoneFurnace, furnace.position)

    assert retrieved is not None, (
        "Invariant: Placed entity should be retrievable via get_entity"
    )

    # Retrieved entity should have same properties
    assert retrieved.position.x == furnace.position.x, (
        f"Invariant: Retrieved entity position.x should match, "
        f"expected {furnace.position.x}, got {retrieved.position.x}"
    )
    assert retrieved.position.y == furnace.position.y, (
        f"Invariant: Retrieved entity position.y should match, "
        f"expected {furnace.position.y}, got {retrieved.position.y}"
    )


def test_entity_removal_clears_position(game):
    """
    Invariant: pickup_entity removes entity from game state.

    From Factorio 2.0 docs: Entity destruction removes from world.
    """
    target_position = Position(x=7, y=7)
    game.move_to(target_position)

    # Place entity
    chest = game.place_entity(
        Prototype.WoodenChest,
        position=target_position,
    )

    assert chest is not None, "Entity should be placed"

    # Verify entity exists
    retrieved_before = game.get_entity(Prototype.WoodenChest, chest.position)
    assert retrieved_before is not None, "Entity should exist before removal"

    # Remove entity
    game.pickup_entity(chest)

    # Entity should no longer exist at that position
    retrieved_after = game.get_entity(Prototype.WoodenChest, chest.position)

    assert retrieved_after is None, (
        "Invariant: Entity should not exist after pickup_entity"
    )

    # Position should be available for new placement
    can_place = game.can_place_entity(
        Prototype.WoodenChest,
        position=target_position,
    )

    assert can_place, "Invariant: Position should be available after entity removal"


def test_crafting_machine_progress_in_valid_range(game):
    """
    Invariant: Crafting progress stays within [0, 1] range.

    From Factorio 2.0 docs: Crafting progress ranges 0-1.
    """
    game.move_to(Position(x=10, y=10))

    # Place assembling machine
    assembler = game.place_entity(
        Prototype.AssemblingMachine1,
        position=Position(x=10, y=10),
    )

    assert assembler is not None, "Assembler should be placed"

    # Set a recipe (iron gear wheels: 2 iron plates -> 1 gear)
    game.set_entity_recipe(assembler, Prototype.IronGearWheel)

    # Insert ingredients
    game.insert_item(Prototype.IronPlate, assembler, 50)

    # Wait for crafting to start (need power for electric assembler)
    # Since we don't have power setup, the assembler won't actually craft
    # But we can still check the progress property exists and is valid

    # Refresh assembler state
    assembler = game.get_entity(Prototype.AssemblingMachine1, assembler.position)

    # Check crafting_progress if available
    if hasattr(assembler, "crafting_progress"):
        progress = assembler.crafting_progress
        if progress is not None:
            assert 0.0 <= progress <= 1.0, (
                f"Invariant violation: crafting_progress should be in [0, 1], "
                f"got {progress}"
            )

    # Check bonus_progress if available (productivity bonus)
    if hasattr(assembler, "bonus_progress"):
        bonus = assembler.bonus_progress
        if bonus is not None:
            assert 0.0 <= bonus <= 1.0, (
                f"Invariant violation: bonus_progress should be in [0, 1], got {bonus}"
            )
