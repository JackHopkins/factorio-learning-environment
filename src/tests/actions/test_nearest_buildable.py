import pytest
from factorio_types import Prototype, Resource
from factorio_entities import Position, BoundingBox, BuildingBox
from factorio_instance import FactorioInstance

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
    chest_box = BuildingBox(height=1, width=1)
    # Find nearest buildable position for wooden chest
    boundingbox_coords = game.nearest_buildable(Prototype.WoodenChest,
                                      chest_box, 
                                      Position(x=5, y=5))

    for key, coord in boundingbox_coords.items():
        # Verify the returned position is valid
        can_build = game.can_place_entity(Prototype.WoodenChest, position = coord)
        assert can_build is True


def test_nearest_buildable_mining_drill(game):
    """
    Test finding a buildable position for an electric mining drill with a bounding box
    over an ore patch.
    """
    # Define mining drill bounding box (3x3)
    drill_box = BuildingBox(height=5, width=5)
    copper_ore = game.nearest(Resource.CopperOre)
    can_build = game.can_place_entity(
            Prototype.BurnerMiningDrill,
            position=copper_ore
        )
    # {'center': {'x': 9.0, 'y': 2.0}, 'left_top': {'x': -1.0, 'y': -1.0}, 'right_bottom': {'x': 19.0, 'y': 5.0}}
    # Find nearest buildable position for mining drill
    boundingbox_coords = game.nearest_buildable(
        Prototype.BurnerMiningDrill,
        building_box=drill_box,
        center_position=game.nearest(Resource.CopperOre)
        #center_position=Position(5, 5)
    )
    for key, coord in boundingbox_coords.items():
        game.move_to(coord)
        # Verify the position is valid for the entire bounding box
        can_build = game.can_place_entity(
            Prototype.BurnerMiningDrill,
            position=coord
        )
        game.place_entity(Prototype.BurnerMiningDrill, position=coord)
        #assert can_build is True

    boundingbox_coords = game.nearest_buildable(
        Prototype.BurnerMiningDrill,
        building_box=drill_box,
        center_position=Position(5, 5)
    )
    for key, coord in boundingbox_coords.items():
        # Verify the position is valid for the entire bounding box
        can_build = game.can_place_entity(
            Prototype.BurnerMiningDrill,
            position=coord
        )
        assert can_build is True

def test_nearest_buildable_invalid_position(game):
    """
    Test that nearest_buildable raises an exception when no valid position
    is found within search radius.
    """
    # Define mining drill bounding box (3x3)
    drill_box = BuildingBox(height=11, width=7)

    boundingbox_coords = game.nearest_buildable(
        Prototype.BurnerMiningDrill,
        building_box=drill_box,
        center_position=game.nearest(Resource.CopperOre)
        #center_position=Position(5, 5)
    )

    # Attempt to find position for an entity with impossible bounding box
    with pytest.raises(Exception) as exc_info:
        boundingbox_coords = game.nearest_buildable(
        Prototype.BurnerMiningDrill,
        building_box=drill_box,
        center_position=game.nearest(Resource.CopperOre)
    )
    assert "Could not find a buildable position" in str(exc_info.value)

def test_nearest_buildable_multiple_entities(game):
    """
    Test finding buildable positions for multiple entities of the same type
    ensuring they don't overlap.
    """
    drill_box = BuildingBox(height=3, width=9)
    
    game.move_to(game.nearest(Resource.IronOre))
    coordinates = game.nearest_buildable(
        Prototype.ElectricMiningDrill,
        building_box=drill_box,
        center_position=game.nearest(Resource.IronOre)
    )

    # get the top left
    top_left = coordinates['left_top']
    positions = []
    # iterate from left to right
    for i in range(0, 3):
        pos = Position(x=top_left.x + 3*i, y=top_left.y)
        game.move_to(pos)
        # Place entity at found position to ensure next search finds different spot
        game.place_entity(Prototype.ElectricMiningDrill, position=pos, exact=True)
        positions.append(pos)

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

    buildingbox = BuildingBox(height=3, width=3)
    # Find buildable position
    position = game.nearest_buildable(Prototype.WoodenChest, buildingbox, player_pos)

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

    chest_box = BuildingBox(height=1, width=1)
    # Find buildable position for another chest
    coords = game.nearest_buildable(Prototype.WoodenChest, chest_box, player_pos)

    position = coords["left_top"]
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
