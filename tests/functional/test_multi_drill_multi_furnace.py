import pytest

from fle.env import BuildingBox, Position, Direction
from fle.env.game_types import Resource, Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "burner-mining-drill": 2,
        "stone-furnace": 5,
        "burner-inserter": 5,
        "electric-mining-drill": 8,
        "transport-belt": 100,
        "iron-chest": 1,
        "coal": 50,
    }
    instance.reset()
    yield instance.namespace
    instance.reset()


def test_multi_drill_multi_furnace(game):
    # Move to the nearest copper ore position
    copper_ore_position = game.nearest(Resource.CopperOre)
    game.move_to(copper_ore_position)
    print(f"Moved to copper ore position at {copper_ore_position}")

    # Define the building box for the drill line
    building_box = BuildingBox(
        width=2 * 4, height=3
    )  # 5 drills, 2 width per drill, 4 height to account for inserter and belt
    # Get the nearest buildable area around the copper ore position
    buildable_coordinates = game.nearest_buildable(
        Prototype.ElectricMiningDrill, building_box, copper_ore_position
    )

    # Place the drill line
    left_top = buildable_coordinates.left_top
    game.move_to(left_top)
    for i in range(4):
        drill_position = Position(x=left_top.x + 3 * i, y=left_top.y)
        game.move_to(drill_position)
        drill = game.place_entity(
            Prototype.ElectricMiningDrill,
            position=drill_position,
            direction=Direction.DOWN,
        )
        print(f"Placed ElectricMiningDrill {i} at {drill.position} to mine copper ore")

    # Place the furnace line
    furnace_positions = []
    for i in range(5):
        furnace_position = Position(x=left_top.x + 3 * i, y=left_top.y + 3)
        game.move_to(furnace_position)
        game.place_entity(Prototype.StoneFurnace, position=furnace_position)
        furnace_positions.append(furnace_position)
        print(f"Placed StoneFurnace {i} at {furnace_position} to smelt copper plates")

    # Connect the drill line to the furnace line with inserters and belts
    for i in range(5):
        drill = game.get_entity(
            Prototype.ElectricMiningDrill,
            position=Position(x=left_top.x + 2 * i, y=left_top.y),
        )
        if not drill:
            assert False
