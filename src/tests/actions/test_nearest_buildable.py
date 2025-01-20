import pytest
from factorio_types import Prototype, Resource
from factorio_entities import Position, BoundingBox


@pytest.fixture()
def game(instance):
    instance.reset()
    instance.set_inventory(**{
        'wooden-chest': 100,
        'electric-mining-drill': 10
    })
    yield instance.namespace


def test_nearest_buildable_simple(game):
    """
    Test finding a buildable position for a simple entity like a wooden chest
    without a bounding box.
    """
    # Find nearest buildable position for wooden chest
    position = game.nearest_buildable(Prototype.WoodenChest)

    # Verify the returned position is valid
    can_build = game.can_place_entity(Prototype.WoodenChest, position)
    assert can_build is True


def test_nearest_buildable_mining_drill(game):
    """
    Test finding a buildable position for an electric mining drill with a bounding box
    over an ore patch.
    """
    # Define mining drill bounding box (3x3)
    drill_box = BoundingBox(
        left_top=Position(x=-1, y=-1),
        right_bottom=Position(x=19, y=5),
        center=Position(x=9, y=2)
    )

    # {'center': {'x': 9.0, 'y': 2.0}, 'left_top': {'x': -1.0, 'y': -1.0}, 'right_bottom': {'x': 19.0, 'y': 5.0}}
    # Find nearest buildable position for mining drill
    position = game.nearest_buildable(
        Prototype.ElectricMiningDrill,
        bounding_box=drill_box
    )

    # Verify the position is valid for the entire bounding box
    can_build = game.can_place_entity(
        Prototype.ElectricMiningDrill,
        position=position
    )
    assert can_build is True


def test_nearest_buildable_invalid_position(game):
    """
    Test that nearest_buildable raises an exception when no valid position
    is found within search radius.
    """
    # Create a bounding box that's too large to be valid anywhere
    large_box = BoundingBox(
        left_top=Position(x=-10, y=-10),
        right_bottom=Position(x=10, y=10),
        center=Position(x=0, y=0)
    )

    # Attempt to find position for an entity with impossible bounding box
    with pytest.raises(Exception) as exc_info:
        game.nearest_buildable(
            Prototype.AssemblingMachine1,
            bounding_box=large_box
        )
    assert "Could not find a buildable position" in str(exc_info.value)

def test_nearest_buildable_manual_box(game):
    # Calculate bounding box for miners
    left_top = Position(
        x=3.0,
        y=0.0
    )
    right_bottom = Position(
        x=13.0,
        y=32.0
    )
    center = Position(
        x=(left_top.x + right_bottom.x) / 2,
        y=(left_top.y + right_bottom.y) / 2
    )

    miner_box = BoundingBox(
        left_top=left_top,
        right_bottom=right_bottom,
        center=center
    )

    # Find valid position for miners using nearest_buildable
    origin = game.nearest_buildable(
        Prototype.ElectricMiningDrill,
        bounding_box=miner_box
    )
    assert origin

def test_nearest_buildable_multiple_entities(game):
    """
    Test finding buildable positions for multiple entities of the same type
    ensuring they don't overlap.
    """
    drill_box = BoundingBox(
        left_top=Position(x=-4, y=-4),
        right_bottom=Position(x=4, y=4),
        center=Position(x=0, y=0)
    )
    game.move_to(game.nearest(Resource.IronOre))
    pos = game.nearest_buildable(
        Prototype.ElectricMiningDrill,
        bounding_box=drill_box
    )

    # Find positions for 3 mining drills
    positions = []
    for i in range(0, 3):
        npos = Position(x=pos.x + i*3, y=pos.y)
        positions.append(npos)
        game.move_to(npos)
        # Place entity at found position to ensure next search finds different spot
        game.place_entity(Prototype.ElectricMiningDrill, position=npos, exact=True)

    # Verify all positions are different
    assert len(set((p.x, p.y) for p in positions)) == 3


    # Verify all positions are valid
    for pos in positions:
        game.pickup_entity(Prototype.ElectricMiningDrill, pos)
        can_build = game.can_place_entity(
            Prototype.ElectricMiningDrill,
            position=pos,
        )
        assert can_build is True


def test_nearest_buildable_relative_to_player(game):
    """
    Test that nearest_buildable finds positions relative to player location.
    """
    # Move player to a specific location
    player_pos = Position(x=100, y=100)
    game.move_to(player_pos)

    # Find buildable position
    position = game.nearest_buildable(Prototype.WoodenChest)

    # Verify found position is reasonably close to player
    distance = ((position.x - player_pos.x) ** 2 +
                (position.y - player_pos.y) ** 2) ** 0.5
    assert distance <= 50  # Within max search radius


def test_nearest_buildable_with_obstacles(game):
    """
    Test finding buildable position when there are obstacles in the way.
    """
    # Place some obstacles around player
    player_pos = game.get_player_position()
    for dx, dy in [(0, 1), (1, 0), (-1, 0), (0, -1)]:
        obstacle_pos = Position(
            x=player_pos.x + dx,
            y=player_pos.y + dy
        )
        game.place_entity(Prototype.WoodenChest, obstacle_pos)

    # Find buildable position for another chest
    position = game.nearest_buildable(Prototype.WoodenChest)

    # Verify position is valid and different from obstacle positions
    can_build = game.can_place_entity(Prototype.WoodenChest, position)
    assert can_build is True

    # Verify it's not at any of the obstacle positions
    for dx, dy in [(0, 1), (1, 0), (-1, 0), (0, -1)]:
        obstacle_pos = Position(
            x=player_pos.x + dx,
            y=player_pos.y + dy
        )
        assert position != obstacle_pos