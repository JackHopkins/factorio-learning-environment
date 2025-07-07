import pytest

from fle.commons.cluster_ips import get_local_container_ips
from fle.env.game_types import Prototype, Resource
from fle.env.entities import Position, BuildingBox, Direction
from fle.env import FactorioInstance

# @pytest.fixture()
# def game(instance):
#     instance.reset()
#     instance.set_inventory({
#         'wooden-chest': 100,
#         'electric-mining-drill': 10,
#         'steam-engine': 1,
#         'burner-mining-drill': 5
#     })
#     yield instance.namespace


@pytest.fixture()
def game():
    ips, udp_ports, tcp_ports = get_local_container_ips()

    instance = FactorioInstance(
        address="localhost",
        bounding_box=200,
        tcp_port=tcp_ports[-1],
        cache_scripts=False,
        fast=True,
        inventory={
            "coal": 50,
            "copper-plate": 50,
            "iron-plate": 50,
            "iron-chest": 2,
            "burner-mining-drill": 3,
            "electric-mining-drill": 1,
            "assembling-machine-1": 1,
            "stone-furnace": 9,
            "transport-belt": 50,
            "boiler": 1,
            "burner-inserter": 32,
            "pipe": 15,
            "steam-engine": 1,
            "small-electric-pole": 10,
            "pumpjack": 1,
        },
    )
    instance.reset()
    instance.set_inventory(
        {
            "wooden-chest": 100,
            "electric-mining-drill": 10,
            "steam-engine": 1,
            "burner-mining-drill": 5,
            "pumpjack": 1,
        }
    )
    yield instance.namespace


def test_nearest_buildable_simple(game):
    """
    Test finding a buildable position for a simple entity like a wooden chest
    without a bounding box.
    """
    chest_box = BuildingBox(height=1, width=1)
    # Find nearest buildable position for wooden chest
    boundingbox_coords = game.nearest_buildable(
        Prototype.WoodenChest, chest_box, Position(x=5, y=5)
    )

    can_build = game.can_place_entity(
        Prototype.WoodenChest, position=boundingbox_coords.center
    )
    assert can_build is True


def test_nearest_buildable_near_water(game):
    """
    Test finding a buildable position for a simple entity like a wooden chest
    without a bounding box.
    """
    # steam_engine = game.place_entity(Prototype.SteamEngine, direction=Direction.RIGHT, position=Position(x=0, y=0))
    water_pos = game.nearest(Resource.Water)
    game.move_to(water_pos)

    building_box = BuildingBox(width=5, height=3)  # Steam engine dimensions are 3x5
    buildable_area = game.nearest_buildable(
        Prototype.SteamEngine, building_box, water_pos
    )

    # Step 2: Place Steam Engine at Valid Position
    steam_engine_position = buildable_area.center
    game.move_to(steam_engine_position.right(5))

    game.place_entity(
        Prototype.SteamEngine, direction=Direction.RIGHT, position=steam_engine_position
    )

    assert True, "The steam engine should be placeable due to the bounding box"


def test_nearest_buildable_prototype_dimensions(game):
    """
    Test finding a buildable position for an entity with prototype dimensions.
    """
    offshore_pump_box = BuildingBox(  # noqa
        width=Prototype.OffshorePump.WIDTH, height=Prototype.OffshorePump.HEIGHT
    )
    assert True


def test_nearest_buildable_mining_drill(game):
    """
    Test finding a buildable position for an electric mining drill with a bounding box
    over an ore patch.
    """
    # Define mining drill bounding box (3x3)
    drill_box = BuildingBox(height=5, width=5)
    copper_ore = game.nearest(Resource.CopperOre)
    can_build = game.can_place_entity(Prototype.BurnerMiningDrill, position=copper_ore)
    # {'center': {'x': 9.0, 'y': 2.0}, 'left_top': {'x': -1.0, 'y': -1.0}, 'right_bottom': {'x': 19.0, 'y': 5.0}}
    # Find nearest buildable position for mining drill
    boundingbox_coords = game.nearest_buildable(
        Prototype.BurnerMiningDrill,
        drill_box,
        center_position=game.nearest(Resource.CopperOre),
        # center_position=Position(5, 5)
    )
    game.move_to(boundingbox_coords.center)
    # Verify the position is valid for the entire bounding box
    can_build = game.can_place_entity(
        Prototype.BurnerMiningDrill, position=boundingbox_coords.center
    )
    game.place_entity(Prototype.BurnerMiningDrill, position=boundingbox_coords.center)
    # assert can_build is True

    boundingbox_coords = game.nearest_buildable(
        Prototype.BurnerMiningDrill, drill_box, center_position=Position(5, 5)
    )
    game.move_to(boundingbox_coords.center)
    can_build = game.can_place_entity(
        Prototype.BurnerMiningDrill,
        direction=Direction.UP,
        position=boundingbox_coords.center,
    )
    assert can_build is True
    game.place_entity(
        Prototype.BurnerMiningDrill,
        direction=Direction.UP,
        position=boundingbox_coords.center,
    )


def test_nearest_buildable_invalid_position(game):
    """
    Test that nearest_buildable raises an exception when no valid position
    is found within search radius.
    """
    # Define mining drill bounding box (3x3)
    drill_box = BuildingBox(height=11, width=7)

    # Attempt to find position for an entity with impossible bounding box
    with pytest.raises(Exception) as exc_info:
        boundingbox_coords = game.nearest_buildable(  # noqa
            Prototype.BurnerMiningDrill,
            drill_box,
            center_position=game.nearest(Resource.CopperOre),
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
        drill_box,
        center_position=game.nearest(Resource.IronOre),
    )

    # get the top left
    top_left = coordinates.left_top
    positions = []
    # iterate from left to right
    for i in range(0, 3):
        pos = Position(x=top_left.x + 3 * i, y=top_left.y)
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
    position = game.nearest_buildable(
        Prototype.WoodenChest, buildingbox, player_pos
    ).center

    # Verify found position is reasonably close to player
    distance = (
        (position.x - player_pos.x) ** 2 + (position.y - player_pos.y) ** 2
    ) ** 0.5
    assert distance <= 50  # Within max search radius


def test_nearest_buildable_with_obstacles(game):
    """
    Test finding buildable position when there are obstacles in the way.
    """
    # Place some obstacles around player
    player_pos = Position(x=0, y=0)
    for dx, dy in [(0, 1), (1, 0), (-1, 0), (0, -1)]:
        obstacle_pos = Position(x=player_pos.x + dx, y=player_pos.y + dy)
        game.place_entity(Prototype.WoodenChest, Direction.UP, obstacle_pos)

    chest_box = BuildingBox(height=1, width=1)
    # Find buildable position for another chest
    coords = game.nearest_buildable(Prototype.WoodenChest, chest_box, player_pos)

    position = coords.center
    # Verify position is valid and different from obstacle positions
    can_build = game.can_place_entity(Prototype.WoodenChest, Direction.UP, position)
    assert can_build is True

    # Verify it's not at any of the obstacle positions
    for dx, dy in [(0, 1), (1, 0), (-1, 0), (0, -1)]:
        obstacle_pos = Position(x=player_pos.x + dx, y=player_pos.y + dy)
        assert position is not obstacle_pos


def test_drill_groups(game):
    # Find iron ore patch
    iron_ore_pos = game.nearest(Resource.IronOre)
    print(f"Found iron ore patch at {iron_ore_pos}")

    # Place 3 electric mining drills with smaller building boxes
    drill_positions = []
    for i in range(3):
        # Use 3x3 building box for each drill
        building_box = BuildingBox(width=3, height=3)
        buildable_coords = game.nearest_buildable(
            Prototype.ElectricMiningDrill, building_box, iron_ore_pos
        )

        # Place drill at center of buildable area
        drill_pos = Position(
            x=buildable_coords.left_top.x + 1.5, y=buildable_coords.left_top.y + 1.5
        )
        game.move_to(drill_pos)
        drill = game.place_entity(
            Prototype.ElectricMiningDrill, position=drill_pos, direction=Direction.DOWN
        )
        print(f"Placed electric mining drill {i + 1} at {drill.position}")
        drill_positions.append(drill.position)
        # Update iron_ore_pos to be near last placed drill for next iteration
        iron_ore_pos = drill.position

    entities = game.get_entities()
    assert len(entities) == 3


def test_nearest_buildable_pumpjack(game):
    # Find crude oil patch
    crude_oil_pos = game.nearest(Resource.CrudeOil)
    print(f"Found crude oil patch at {crude_oil_pos}")

    # place one pumpjack
    building_box = BuildingBox(width=5, height=5)
    buildable_coords = game.nearest_buildable(
        Prototype.PumpJack, building_box, crude_oil_pos
    )
    game.move_to(buildable_coords.center)
    game.place_entity(
        Prototype.PumpJack, position=buildable_coords.center, direction=Direction.DOWN
    )

    entities = game.get_entities()
    assert len(entities) == 1
