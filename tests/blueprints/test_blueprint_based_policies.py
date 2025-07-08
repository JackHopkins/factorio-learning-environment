import pytest

from fle.env.entities import Position, BoundingBox  # , Direction
from fle.env import DirectionInternal as Direction
from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "burner-mining-drill": 5,
        "electric-mining-drill": 20,
        "small-electric-pole": 10,
        "underground-belt": 10,
        "small-lamp": 10,
        "stone-furnace": 10,
        "burner-inserter": 10,
        "transport-belt": 100,
        "iron-chest": 1,
        "wooden-chest": 2,
        "coal": 50,
        "assembling-machine-1": 1,
        "inserter": 10,
    }
    instance.reset()
    yield instance.namespace


def test_mining_blueprint_1(game):
    # Calculate bounding box
    left_top = Position(x=0, y=0)
    right_bottom = Position(x=2, y=9)
    left_bottom = Position(x=left_top.x, y=right_bottom.y)
    right_top = Position(x=right_bottom.x, y=left_top.y)
    miner_box = BoundingBox(
        left_top=left_top,
        right_bottom=right_bottom,
        left_bottom=left_bottom,
        right_top=right_top,
    )
    # Find valid position using nearest_buildable
    origin = game.nearest_buildable(
        Prototype.BurnerMiningDrill, miner_box, center_position=Position(x=0, y=0)
    )
    assert origin, "Could not find valid position"
    origin = origin + left_top + Position(x=0.5, y=0.5)
    game.move_to(origin)
    # Place transport-belt vertically at x=0.0
    for i in range(10):
        world_y = 0.0 + (1.0 * i) + origin.y
        world_x = 0.0 + origin.x
        game.move_to(Position(x=world_x, y=world_y))
        game.place_entity(
            Prototype.TransportBelt,
            position=Position(x=world_x, y=world_y),
            direction=Direction.UP,
        )
    # Place burner-inserter vertically at x=2.0
    for i in range(3):
        world_y = 1.0 + (3.0 * i) + origin.y
        world_x = 2.0 + origin.x
        game.move_to(Position(x=world_x, y=world_y))
        game.place_entity(
            Prototype.BurnerInserter,
            position=Position(x=world_x, y=world_y),
            direction=Direction.UP,
        )
    # Place burner-mining-drill vertically at x=1.5
    for i in range(3):
        world_y = 2.5 + (3.0 * i) + origin.y
        world_x = 1.5 + origin.x
        game.move_to(Position(x=world_x, y=world_y))
        game.place_entity(
            Prototype.BurnerMiningDrill,
            position=Position(x=world_x, y=world_y),
            direction=Direction.LEFT,
        )
    # Place individual burner-inserter
    game.move_to(Position(x=origin.x + 1.0, y=origin.y + 1.0))
    game.place_entity(
        Prototype.BurnerInserter,
        position=Position(x=origin.x + 1.0, y=origin.y + 1.0),
        direction=Direction.DOWN,
    )
    # Place individual wooden-chest
    game.move_to(Position(x=origin.x + 2.0, y=origin.y + 0.0))
    game.place_entity(
        Prototype.WoodenChest,
        position=Position(x=origin.x + 2.0, y=origin.y + 0.0),
        direction=Direction.UP,
    )
    # Place individual burner-inserter
    game.move_to(Position(x=origin.x + 1.0, y=origin.y + 0.0))
    game.place_entity(
        Prototype.BurnerInserter,
        position=Position(x=origin.x + 1.0, y=origin.y + 0.0),
        direction=Direction.LEFT,
    )


def test_mining_blueprint_2(game):
    # Calculate bounding box
    left_top = Position(x=0, y=0)
    right_bottom = Position(x=29.0, y=4.0)
    left_bottom = Position(x=left_top.x, y=right_bottom.y)
    right_top = Position(x=right_bottom.x, y=left_top.y)
    miner_box = BoundingBox(
        left_top=left_top,
        right_bottom=right_bottom,
        left_bottom=left_bottom,
        right_top=right_top,
    )
    # Find valid position using nearest_buildable
    origin = game.nearest_buildable(
        Prototype.ElectricMiningDrill, miner_box, center_position=Position(x=0, y=0)
    )
    assert origin, "Could not find valid position"
    origin = origin + left_top + Position(x=0.5, y=0.5)
    game.move_to(origin)
    # Place electric-mining-drill horizontally at y=0.0
    for i in range(4):
        world_x = 6.0 + (6.0 * i) + origin.x
        world_y = 0.0 + origin.y
        game.move_to(Position(x=world_x, y=world_y))
        game.place_entity(
            Prototype.ElectricMiningDrill,
            position=Position(x=world_x, y=world_y),
            direction=Direction.DOWN,
        )
    # Place electric-mining-drill horizontally at y=2.0
    for i in range(5):
        world_x = 3.0 + (6.0 * i) + origin.x
        world_y = 2.0 + origin.y
        game.move_to(Position(x=world_x, y=world_y))
        game.place_entity(
            Prototype.ElectricMiningDrill,
            position=Position(x=world_x, y=world_y),
            direction=Direction.RIGHT,
        )
    # Place small-electric-pole horizontally at y=2.0
    for i in range(5):
        world_x = 1.0 + (6.0 * i) + origin.x
        world_y = 2.0 + origin.y
        game.move_to(Position(x=world_x, y=world_y))
        game.place_entity(
            Prototype.SmallElectricPole,
            position=Position(x=world_x, y=world_y),
            direction=Direction.UP,
        )
    # Place electric-mining-drill horizontally at y=4.0
    for i in range(4):
        world_x = 6.0 + (6.0 * i) + origin.x
        world_y = 4.0 + origin.y
        game.move_to(Position(x=world_x, y=world_y))
        game.place_entity(
            Prototype.ElectricMiningDrill,
            position=Position(x=world_x, y=world_y),
            direction=Direction.UP,
        )
    # Place individual underground-belt
    game.move_to(Position(x=origin.x + 0.0, y=origin.y + 2.0))
    game.place_entity(
        Prototype.UndergroundBelt,
        position=Position(x=origin.x + 0.0, y=origin.y + 2.0),
        direction=Direction.RIGHT,
    )
    # Place individual underground-belt
    game.move_to(Position(x=origin.x + 5.0, y=origin.y + 2.0))
    game.place_entity(
        Prototype.UndergroundBelt,
        position=Position(x=origin.x + 5.0, y=origin.y + 2.0),
        direction=Direction.RIGHT,
    )
    # Place individual underground-belt
    game.move_to(Position(x=origin.x + 6.0, y=origin.y + 2.0))
    game.place_entity(
        Prototype.UndergroundBelt,
        position=Position(x=origin.x + 6.0, y=origin.y + 2.0),
        direction=Direction.RIGHT,
    )
    # Place individual underground-belt
    game.move_to(Position(x=origin.x + 11.0, y=origin.y + 2.0))
    game.place_entity(
        Prototype.UndergroundBelt,
        position=Position(x=origin.x + 11.0, y=origin.y + 2.0),
        direction=Direction.RIGHT,
    )
    # Place individual underground-belt
    game.move_to(Position(x=origin.x + 12.0, y=origin.y + 2.0))
    game.place_entity(
        Prototype.UndergroundBelt,
        position=Position(x=origin.x + 12.0, y=origin.y + 2.0),
        direction=Direction.RIGHT,
    )
    # Place individual underground-belt
    game.move_to(Position(x=origin.x + 17.0, y=origin.y + 2.0))
    game.place_entity(
        Prototype.UndergroundBelt,
        position=Position(x=origin.x + 17.0, y=origin.y + 2.0),
        direction=Direction.RIGHT,
    )
    # Place individual underground-belt
    game.move_to(Position(x=origin.x + 18.0, y=origin.y + 2.0))
    game.place_entity(
        Prototype.UndergroundBelt,
        position=Position(x=origin.x + 18.0, y=origin.y + 2.0),
        direction=Direction.RIGHT,
    )
    # Place individual underground-belt
    game.move_to(Position(x=origin.x + 23.0, y=origin.y + 2.0))
    game.place_entity(
        Prototype.UndergroundBelt,
        position=Position(x=origin.x + 23.0, y=origin.y + 2.0),
        direction=Direction.RIGHT,
    )
    # Place individual underground-belt
    game.move_to(Position(x=origin.x + 24.0, y=origin.y + 2.0))
    game.place_entity(
        Prototype.UndergroundBelt,
        position=Position(x=origin.x + 24.0, y=origin.y + 2.0),
        direction=Direction.RIGHT,
    )
    # Place individual underground-belt
    game.move_to(Position(x=origin.x + 29.0, y=origin.y + 2.0))
    game.place_entity(
        Prototype.UndergroundBelt,
        position=Position(x=origin.x + 29.0, y=origin.y + 2.0),
        direction=Direction.RIGHT,
    )


def test_mining_blueprint_3(game):
    # Find suitable origin position for miners on ore

    # Calculate bounding box for miners
    left_top = Position(x=-6.0, y=0.0)
    right_bottom = Position(x=23.0, y=4.0)
    left_bottom = Position(x=left_top.x, y=right_bottom.y)
    right_top = Position(x=right_bottom.x, y=left_top.y)

    miner_box = BoundingBox(
        left_top=left_top,
        right_bottom=right_bottom,
        left_bottom=left_bottom,
        right_top=right_top,
    )

    # Find valid position for miners using nearest_buildable
    origin = game.nearest_buildable(
        Prototype.ElectricMiningDrill, miner_box, center_position=Position(x=0, y=0)
    )

    assert origin, "Could not find valid position for miners"

    # Move to origin position
    game.move_to(origin)

    # Place electric-mining-drill horizontally at y=-0.5
    for x in range(-9, 10, 6):
        world_x = x + 14.5 + origin.x + left_top.x
        world_y = -0.5 + origin.y
        game.move_to(Position(x=world_x, y=world_y))
        game.place_entity(
            Prototype.ElectricMiningDrill,
            position=Position(x=world_x, y=world_y),
            direction=Direction.DOWN,
        )

    # Place electric-mining-drill horizontally at y=1.5
    for x in range(-12, 13, 6):
        world_x = x + 14.5 + origin.x + left_top.x
        world_y = 1.5 + origin.y
        game.move_to(Position(x=world_x, y=world_y))
        game.place_entity(
            Prototype.ElectricMiningDrill,
            position=Position(x=world_x, y=world_y),
            direction=Direction.RIGHT,
        )

    # Place electric-mining-drill horizontally at y=3.5
    for x in range(-9, 10, 6):
        world_x = x + 14.5 + origin.x + left_top.x
        world_y = 3.5 + origin.y
        game.move_to(Position(x=world_x, y=world_y))
        game.place_entity(
            Prototype.ElectricMiningDrill,
            position=Position(x=world_x, y=world_y),
            direction=Direction.UP,
        )

    # Place underground-belt horizontally at y=1.5
    for x in range(-15, -9, 5):
        world_x = x + 14.5 + origin.x + left_top.x
        world_y = 1.5 + origin.y
        game.move_to(Position(x=world_x, y=world_y))
        game.place_entity(
            Prototype.UndergroundBelt,
            position=Position(x=world_x, y=world_y),
            direction=Direction.RIGHT,
        )

    # Place underground-belt horizontally at y=1.5
    for x in range(-9, -3, 5):
        world_x = x + 14.5 + origin.x + left_top.x
        world_y = 1.5 + origin.y
        game.move_to(Position(x=world_x, y=world_y))
        game.place_entity(
            Prototype.UndergroundBelt,
            position=Position(x=world_x, y=world_y),
            direction=Direction.RIGHT,
        )

    # Place underground-belt horizontally at y=1.5
    for x in range(-3, 3, 5):
        world_x = x + 14.5 + origin.x + left_top.x
        world_y = 1.5 + origin.y
        game.move_to(Position(x=world_x, y=world_y))
        game.place_entity(
            Prototype.UndergroundBelt,
            position=Position(x=world_x, y=world_y),
            direction=Direction.RIGHT,
        )

    # Place underground-belt horizontally at y=1.5
    for x in range(3, 9, 5):
        world_x = x + 14.5 + origin.x + left_top.x
        world_y = 1.5 + origin.y
        game.move_to(Position(x=world_x, y=world_y))
        game.place_entity(
            Prototype.UndergroundBelt,
            position=Position(x=world_x, y=world_y),
            direction=Direction.RIGHT,
        )

    # Place underground-belt horizontally at y=1.5
    for x in range(9, 15, 5):
        world_x = x + 14.5 + origin.x + left_top.x
        world_y = 1.5 + origin.y
        game.move_to(Position(x=world_x, y=world_y))
        game.place_entity(
            Prototype.UndergroundBelt,
            position=Position(x=world_x, y=world_y),
            direction=Direction.RIGHT,
        )

    # Place small-electric-pole horizontally at y=1.5
    for x in range(-14, 11, 6):
        world_x = x + 14.5 + origin.x + left_top.x
        world_y = 1.5 + origin.y
        game.move_to(Position(x=world_x, y=world_y))
        game.place_entity(
            Prototype.SmallElectricPole,
            position=Position(x=world_x, y=world_y),
            direction=Direction.UP,
        )


def test_minig_blueprint_4(game):
    # Calculate bounding box
    left_top = Position(x=0, y=0)
    right_bottom = Position(x=5, y=5.5)
    left_bottom = Position(x=left_top.x, y=right_bottom.y)
    right_top = Position(x=right_bottom.x, y=left_top.y)

    miner_box = BoundingBox(
        left_top=left_top,
        right_bottom=right_bottom,
        left_bottom=left_bottom,
        right_top=right_top,
    )

    # Find valid position using nearest_buildable
    origin = game.nearest_buildable(
        Prototype.BurnerMiningDrill, miner_box, center_position=Position(x=0, y=0)
    )

    assert origin, "Could not find valid position"
    origin = origin + left_top + Position(x=0.5, y=0.5)
    game.move_to(origin)

    # Place individual burner-mining-drill
    game.move_to(Position(x=origin.x + 2.0, y=origin.y + 0.0))
    game.place_entity(
        Prototype.BurnerMiningDrill,
        position=Position(x=origin.x + 2.0, y=origin.y + 0.0),
        direction=Direction.DOWN,
        exact=True,
    )

    # Place individual burner-mining-drill
    game.move_to(Position(x=origin.x + 0.0, y=origin.y + 3.0))
    game.place_entity(
        Prototype.BurnerMiningDrill,
        position=Position(x=origin.x + 0.0, y=origin.y + 3.0),
        direction=Direction.DOWN,
        exact=True,
    )

    # Place individual assembling-machine-1
    game.move_to(Position(x=origin.x + 2.5, y=origin.y + 2.5))
    assembling_machine_1_1 = game.place_entity(
        Prototype.AssemblingMachine1,
        position=Position(x=origin.x + 2.5, y=origin.y + 2.5),
        direction=Direction.UP,
        exact=True,
    )

    game.set_entity_recipe(assembling_machine_1_1, Prototype.StoneFurnace)

    # Place individual burner-mining-drill
    game.move_to(Position(x=origin.x + 5.0, y=origin.y + 3.0))
    game.place_entity(
        Prototype.BurnerMiningDrill,
        position=Position(x=origin.x + 5.0, y=origin.y + 3.0),
        direction=Direction.DOWN,
        exact=True,
    )

    # Place individual stone-furnace
    game.move_to(Position(x=origin.x + 0.0, y=origin.y + 5.0))
    game.place_entity(
        Prototype.StoneFurnace,
        position=Position(x=origin.x + 0.0, y=origin.y + 5.0),
        direction=Direction.UP,
        exact=True,
    )

    # Place individual inserter
    game.move_to(Position(x=origin.x + 2.5, y=origin.y + 4.5))
    game.place_entity(
        Prototype.Inserter,
        position=Position(x=origin.x + 2.5, y=origin.y + 4.5),
        direction=Direction.UP,
        exact=True,
    )

    # Place individual stone-furnace
    game.move_to(Position(x=origin.x + 5.0, y=origin.y + 5.0))
    game.place_entity(
        Prototype.StoneFurnace,
        position=Position(x=origin.x + 5.0, y=origin.y + 5.0),
        direction=Direction.UP,
        exact=True,
    )

    # Place individual small-electric-pole
    game.move_to(Position(x=origin.x + 3.5, y=origin.y + 4.5))
    game.place_entity(
        Prototype.SmallElectricPole,
        position=Position(x=origin.x + 3.5, y=origin.y + 4.5),
        direction=Direction.UP,
        exact=True,
    )

    # Place individual wooden-chest
    game.move_to(Position(x=origin.x + 2.5, y=origin.y + 5.5))
    game.place_entity(
        Prototype.WoodenChest,
        position=Position(x=origin.x + 2.5, y=origin.y + 5.5),
        direction=Direction.UP,
        exact=True,
    )

    # Place individual inserter
    game.move_to(Position(x=origin.x + 1.5, y=origin.y + 5.5))
    game.place_entity(
        Prototype.Inserter,
        position=Position(x=origin.x + 1.5, y=origin.y + 5.5),
        direction=Direction.LEFT,
        exact=True,
    )

    # Place individual inserter
    game.move_to(Position(x=origin.x + 3.5, y=origin.y + 5.5))
    game.place_entity(
        Prototype.Inserter,
        position=Position(x=origin.x + 3.5, y=origin.y + 5.5),
        direction=Direction.RIGHT,
        exact=True,
    )

    game.get_entities()
