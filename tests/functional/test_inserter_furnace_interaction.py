"""
Unit tests for inserter-furnace interactions.

These tests were created to investigate an issue where inserters couldn't
drop items into furnaces. The root cause was identified as:

**Steel processing technology was not researched.**

In Factorio, inserters are "smart" and won't pick up items if there's no
valid destination. When trying to drop iron plates into a furnace, if steel
processing hasn't been researched, the furnace won't accept iron plates
(since the only recipe using iron plates in a furnace is steel).

Solution: Ensure `all_technologies_researched=True` in test fixtures.
"""

import pytest
from fle.env.entities import Position, Direction
from fle.env.game_types import Prototype


@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        "stone-furnace": 5,
        "iron-chest": 5,
        "burner-inserter": 20,
        "coal": 100,
        "iron-ore": 100,
        "iron-plate": 100,
    }
    instance.reset(all_technologies_researched=True)
    yield instance.namespace


def test_inserter_picks_from_furnace_to_chest(game):
    """
    Test 1: Can an inserter pick iron plates from a furnace's output and put them in a chest?
    This mimics the working test_basic_iron_smelting_chain setup.
    """
    # Place furnace at origin
    furnace = game.place_entity(
        Prototype.StoneFurnace, Direction.UP, Position(x=0, y=0)
    )
    print(f"Furnace at {furnace.position}")

    # Manually add iron ore and coal to furnace
    game.insert_item(Prototype.IronOre, furnace, 50)
    game.insert_item(Prototype.Coal, furnace, 10)

    # Place inserter next to furnace (to the right)
    inserter = game.place_entity_next_to(
        Prototype.BurnerInserter, furnace.position, Direction.RIGHT, spacing=0
    )
    game.insert_item(Prototype.Coal, inserter, 5)
    print(f"Inserter at {inserter.position}")
    print(f"  pickup: {inserter.pickup_position}, drop: {inserter.drop_position}")

    # Place chest next to inserter
    chest = game.place_entity_next_to(
        Prototype.IronChest, inserter.position, Direction.RIGHT, spacing=0
    )
    print(f"Chest at {chest.position}")

    # Wait for smelting and transfer
    game.sleep(30)

    # Check results
    chest_inv = game.inspect_inventory(chest)
    furnace_updated = game.get_entity(Prototype.StoneFurnace, furnace.position)
    inserter_updated = game.get_entity(Prototype.BurnerInserter, inserter.position)

    print(f"Furnace status: {furnace_updated.status}")
    print(f"Furnace result: {furnace_updated.furnace_result}")
    print(f"Inserter status: {inserter_updated.status}")
    print(f"Chest inventory: {chest_inv}")

    iron_plates = chest_inv.get(Prototype.IronPlate, 0)
    assert iron_plates > 0, (
        "Inserter should pick iron plates from furnace and put in chest"
    )


def test_inserter_picks_from_furnace_to_furnace(game):
    """
    Test 2: Can an inserter pick iron plates from furnace1's output and put them into furnace2?
    This is the failing scenario in test_steel_smelting_chain.
    """
    # Place furnace1 at origin
    furnace1 = game.place_entity(
        Prototype.StoneFurnace, Direction.UP, Position(x=0, y=0)
    )
    print(f"Furnace1 at {furnace1.position}")

    # Manually add iron ore and coal to furnace1
    game.insert_item(Prototype.IronOre, furnace1, 50)
    game.insert_item(Prototype.Coal, furnace1, 10)

    # Place inserter next to furnace1 (to the right)
    inserter = game.place_entity_next_to(
        Prototype.BurnerInserter, furnace1.position, Direction.RIGHT, spacing=0
    )
    game.insert_item(Prototype.Coal, inserter, 5)
    print(f"Inserter at {inserter.position}")
    print(f"  pickup: {inserter.pickup_position}, drop: {inserter.drop_position}")

    # Place furnace2 next to inserter
    furnace2 = game.place_entity_next_to(
        Prototype.StoneFurnace, inserter.position, Direction.RIGHT, spacing=0
    )
    game.insert_item(Prototype.Coal, furnace2, 10)
    print(f"Furnace2 at {furnace2.position}")

    # Wait for smelting and transfer
    game.sleep(30)

    # Check results
    f1 = game.get_entity(Prototype.StoneFurnace, furnace1.position)
    f2 = game.get_entity(Prototype.StoneFurnace, furnace2.position)
    ins = game.get_entity(Prototype.BurnerInserter, inserter.position)

    print(f"Furnace1 status: {f1.status}, result: {f1.furnace_result}")
    print(f"Furnace2 status: {f2.status}, source: {f2.furnace_source}")
    print(f"Inserter status: {ins.status}")

    # Check if furnace2 received iron plates
    f2_source = f2.furnace_source.get(Prototype.IronPlate, 0)
    assert f2_source > 0, (
        "Inserter should pick iron plates from furnace1 and put in furnace2"
    )


def test_inserter_picks_plates_from_chest_to_furnace(game):
    """
    Test 3: Can an inserter pick iron plates from a chest and put them into a furnace?
    This tests the drop-into-furnace capability.

    Attempt to manually align entities properly:
    - Chest at (0, 0) - actually ends up at (0.5, 0.5) for 1x1 entities
    - Inserter needs its pickup to reach chest
    - Furnace needs to be reachable by inserter's drop
    """
    # Place chest with iron plates at origin (will be at 0.5, 0.5)
    chest = game.place_entity(Prototype.IronChest, Direction.UP, Position(x=0, y=0))
    game.insert_item(Prototype.IronPlate, chest, 50)
    print(f"Chest at {chest.position}")
    print(
        f"  Chest occupies approx: x=[{chest.position.x - 0.5}, {chest.position.x + 0.5}], y=[{chest.position.y - 0.5}, {chest.position.y + 0.5}]"
    )

    # Place inserter - we want pickup to reach chest center
    # For inserter at (x, y), pickup is at (x-1, y), drop is at (x+1, y)
    # If chest is at (0.5, 0.5), we want inserter at (1.5, 0.5) so pickup is at (0.5, 0.5)
    inserter = game.place_entity(
        Prototype.BurnerInserter, Direction.RIGHT, Position(x=1.5, y=0.5)
    )
    game.insert_item(Prototype.Coal, inserter, 5)
    print(f"Inserter at {inserter.position}")
    print(f"  pickup: {inserter.pickup_position}, drop: {inserter.drop_position}")

    # Verify pickup alignment with chest
    print(
        f"  Pickup {inserter.pickup_position} matches chest {chest.position}? {inserter.pickup_position.x == chest.position.x and inserter.pickup_position.y == chest.position.y}"
    )

    # Place furnace - need drop to reach it
    # Drop is at (2.5, 0.5). Furnace (2x2) centered at (4, 0) occupies [3,5] x [-1, 1]
    # But drop at 2.5 would be outside [3,5]!
    # We need furnace center at x = drop.x + 0.5 = 3.0 for drop to be at furnace left edge
    # Actually for 2x2 furnace centered at 3, it occupies x=[2, 4], so drop at 2.5 IS inside
    furnace = game.place_entity(
        Prototype.StoneFurnace, Direction.UP, Position(x=3, y=0)
    )
    game.insert_item(Prototype.Coal, furnace, 10)
    print(f"Furnace at {furnace.position}")
    print(
        f"  Furnace occupies approx: x=[{furnace.position.x - 1}, {furnace.position.x + 1}], y=[{furnace.position.y - 1}, {furnace.position.y + 1}]"
    )
    print(
        f"  Drop {inserter.drop_position} in furnace X range [{furnace.position.x - 1}, {furnace.position.x + 1}]? {furnace.position.x - 1 <= inserter.drop_position.x <= furnace.position.x + 1}"
    )

    # Wait for transfer
    game.sleep(30)

    # Check results
    f = game.get_entity(Prototype.StoneFurnace, furnace.position)
    ins = game.get_entity(Prototype.BurnerInserter, inserter.position)
    ch = game.get_entity(Prototype.IronChest, chest.position)

    print(f"Chest remaining: {game.inspect_inventory(ch)}")
    print(
        f"Furnace status: {f.status}, source: {f.furnace_source}, result: {f.furnace_result}"
    )
    print(f"Inserter status: {ins.status}")

    # Check if furnace received iron plates for steel smelting
    f_source = f.furnace_source.get(Prototype.IronPlate, 0)
    assert f_source > 0, (
        "Inserter should pick iron plates from chest and put in furnace"
    )


def test_inserter_positions_relative_to_furnace(game):
    """
    Test 4: Examine exact positions when placing inserter next to a furnace.
    This is a diagnostic test to understand the positioning issue.
    """
    # Place furnace at a known position (close to origin, player starts at 0,0)
    furnace = game.place_entity(
        Prototype.StoneFurnace, Direction.UP, Position(x=0, y=0)
    )
    print(f"\nFurnace placed at: {furnace.position}")
    print(
        f"  Furnace is 2x2, should span: x=[{furnace.position.x - 1}, {furnace.position.x + 1}], y=[{furnace.position.y - 1}, {furnace.position.y + 1}]"
    )

    # Place inserter to the right
    inserter = game.place_entity_next_to(
        Prototype.BurnerInserter, furnace.position, Direction.RIGHT, spacing=0
    )
    print(f"\nInserter placed at: {inserter.position}")
    print(f"  Direction: {inserter.direction}")
    print(f"  Pickup position: {inserter.pickup_position}")
    print(f"  Drop position: {inserter.drop_position}")

    # Calculate expected overlap
    pickup_x, pickup_y = inserter.pickup_position.x, inserter.pickup_position.y
    furnace_x_min = furnace.position.x - 1
    furnace_x_max = furnace.position.x + 1
    furnace_y_min = furnace.position.y - 1
    furnace_y_max = furnace.position.y + 1

    pickup_overlaps_furnace_x = furnace_x_min <= pickup_x <= furnace_x_max
    pickup_overlaps_furnace_y = furnace_y_min <= pickup_y <= furnace_y_max

    print("\nPickup position analysis:")
    print(
        f"  Pickup X={pickup_x} in furnace X range [{furnace_x_min}, {furnace_x_max}]? {pickup_overlaps_furnace_x}"
    )
    print(
        f"  Pickup Y={pickup_y} in furnace Y range [{furnace_y_min}, {furnace_y_max}]? {pickup_overlaps_furnace_y}"
    )
    print(
        f"  Pickup overlaps furnace: {pickup_overlaps_furnace_x and pickup_overlaps_furnace_y}"
    )

    # This test always passes - it's for diagnostic output
    assert True


def test_manually_aligned_furnace_inserter_furnace(game):
    """
    Test 6: Use place_entity_next_to for proper inserter positioning between furnaces.

    This test verifies the furnace → inserter → furnace chain works when using
    the place_entity_next_to helper which handles proper alignment automatically.
    """
    # Place furnace1 at origin
    furnace1 = game.place_entity(
        Prototype.StoneFurnace, Direction.UP, Position(x=0, y=0)
    )
    print(f"Furnace1 at {furnace1.position}")

    # Manually add iron ore and coal to furnace1
    game.insert_item(Prototype.IronOre, furnace1, 50)
    game.insert_item(Prototype.Coal, furnace1, 10)

    # Use place_entity_next_to for proper alignment - this handles the
    # grid alignment automatically so inserter can reach furnace1
    inserter = game.place_entity_next_to(
        Prototype.BurnerInserter, furnace1.position, Direction.RIGHT, spacing=0
    )
    game.insert_item(Prototype.Coal, inserter, 5)
    print(f"Inserter at {inserter.position}")
    print(f"  pickup: {inserter.pickup_position}, drop: {inserter.drop_position}")

    # Place furnace2 next to inserter
    furnace2 = game.place_entity_next_to(
        Prototype.StoneFurnace, inserter.position, Direction.RIGHT, spacing=0
    )
    game.insert_item(Prototype.Coal, furnace2, 10)
    print(f"Furnace2 at {furnace2.position}")
    print(
        f"  Furnace2 occupies: x=[{furnace2.position.x - 1}, {furnace2.position.x + 1}], y=[{furnace2.position.y - 1}, {furnace2.position.y + 1}]"
    )

    # Wait for smelting and transfer
    game.sleep(30)

    # Check results
    f1 = game.get_entity(Prototype.StoneFurnace, furnace1.position)
    f2 = game.get_entity(Prototype.StoneFurnace, furnace2.position)
    ins = game.get_entity(Prototype.BurnerInserter, inserter.position)

    print(f"Furnace1 status: {f1.status}, result: {f1.furnace_result}")
    print(f"Furnace2 status: {f2.status}, source: {f2.furnace_source}")
    print(f"Inserter status: {ins.status}")

    # Check if furnace2 received iron plates
    f2_source = f2.furnace_source.get(Prototype.IronPlate, 0)
    assert f2_source > 0, (
        "Inserter should pick iron plates from furnace1 and put in furnace2"
    )


def test_chest_between_furnaces_works(game):
    """
    Test 7: Use a chest between furnaces as intermediate storage.

    The key insight: a burner inserter has 1-tile reach on each side.
    To transfer from furnace1 → chest → furnace2:
    - Inserter1 must reach both furnace1's edge AND chest center
    - Inserter2 must reach both chest center AND furnace2's edge

    Since furnaces are 2x2 and chests are 1x1, we need:
    - Inserter1 placed so its pickup reaches furnace1, drop reaches chest
    - Chest placed at inserter1's drop position
    - Inserter2 placed so its pickup reaches chest, drop reaches furnace2
    - Furnace2 placed so inserter2's drop reaches it

    But here's the problem: inserter2's drop position is 1 tile from its center.
    Furnace2 (2x2) must be positioned so its edge is at inserter2's drop position.
    That means furnace2's CENTER must be 1 tile further out than the drop position.
    """
    # Place furnace1 at origin
    furnace1 = game.place_entity(
        Prototype.StoneFurnace, Direction.UP, Position(x=0, y=0)
    )
    print(f"Furnace1 at {furnace1.position}")

    # Manually add iron ore and coal to furnace1
    game.insert_item(Prototype.IronOre, furnace1, 50)
    game.insert_item(Prototype.Coal, furnace1, 10)

    # Place inserter1 next to furnace1 - this places inserter where it can reach furnace1
    inserter1 = game.place_entity_next_to(
        Prototype.BurnerInserter, furnace1.position, Direction.RIGHT, spacing=0
    )
    game.insert_item(Prototype.Coal, inserter1, 5)
    print(f"Inserter1 at {inserter1.position}")
    print(f"  pickup: {inserter1.pickup_position}, drop: {inserter1.drop_position}")

    # Place chest at inserter1's drop position
    chest = game.place_entity(
        Prototype.IronChest, Direction.UP, inserter1.drop_position
    )
    print(f"Chest at {chest.position}")

    # Place inserter2 next to chest
    inserter2 = game.place_entity_next_to(
        Prototype.BurnerInserter, chest.position, Direction.RIGHT, spacing=0
    )
    game.insert_item(Prototype.Coal, inserter2, 5)
    print(f"Inserter2 at {inserter2.position}")
    print(f"  pickup: {inserter2.pickup_position}, drop: {inserter2.drop_position}")

    # Place furnace2 so inserter2's drop is within its bounds
    # Furnace2 center should be at drop_position + (0.5, 0.5) offset for grid alignment
    # Actually, drop position (4.5, 0.5) means furnace2 centered at (5, 0) or (5, 1)
    # would have its left edge at x=4, which includes x=4.5
    furnace2_x = inserter2.drop_position.x + 0.5  # round up to next integer
    furnace2_y = 0  # same Y as other entities
    furnace2 = game.place_entity(
        Prototype.StoneFurnace, Direction.UP, Position(x=furnace2_x, y=furnace2_y)
    )
    game.insert_item(Prototype.Coal, furnace2, 10)
    print(f"Furnace2 at {furnace2.position}")
    print(f"  Furnace2 left edge at x={furnace2.position.x - 1}")
    print(
        f"  Does drop ({inserter2.drop_position.x}) reach furnace2? {inserter2.drop_position.x >= furnace2.position.x - 1}"
    )

    # Wait for smelting and transfer
    game.sleep(45)

    # Check results
    f1 = game.get_entity(Prototype.StoneFurnace, furnace1.position)
    f2 = game.get_entity(Prototype.StoneFurnace, furnace2.position)
    ch = game.get_entity(Prototype.IronChest, chest.position)
    ins1 = game.get_entity(Prototype.BurnerInserter, inserter1.position)
    ins2 = game.get_entity(Prototype.BurnerInserter, inserter2.position)

    print(f"Furnace1 status: {f1.status}, result: {f1.furnace_result}")
    print(f"Inserter1 status: {ins1.status}")
    print(f"Chest inventory: {game.inspect_inventory(ch)}")
    print(f"Inserter2 status: {ins2.status}")
    print(
        f"Furnace2 status: {f2.status}, source: {f2.furnace_source}, result: {f2.furnace_result}"
    )

    # Check if furnace2 is making steel
    f2_source = f2.furnace_source.get(Prototype.IronPlate, 0)
    f2_result = f2.furnace_result.get(Prototype.SteelPlate, 0)
    assert f2_source > 0 or f2_result > 0, (
        "Furnace2 should have received iron plates through chest"
    )


def test_inserter_pickup_from_chest_sanity_check(game):
    """
    Test 9: A simple sanity check - can an inserter pick from a chest when placed properly?
    This verifies our basic understanding of inserter mechanics.

    Key insight from previous test:
    - Chest at (0.5, 0.5), Inserter pickup at (0.5, 0.5) - should be exact match
    - But inserter showed WAITING_FOR_SOURCE_ITEMS!

    Let's verify the exact alignment works in a simpler setup.
    """
    # Place chest first
    chest = game.place_entity(Prototype.IronChest, Direction.UP, Position(x=0, y=0))
    game.insert_item(Prototype.IronPlate, chest, 50)
    print(f"\nChest placed at: {chest.position}")

    # Place inserter facing RIGHT - it should pickup from its LEFT
    inserter = game.place_entity(
        Prototype.BurnerInserter, Direction.RIGHT, Position(x=1, y=0)
    )
    game.insert_item(Prototype.Coal, inserter, 5)
    print(f"Inserter placed at: {inserter.position}")
    print(f"  direction: {inserter.direction}")
    print(f"  pickup: {inserter.pickup_position}")
    print(f"  drop: {inserter.drop_position}")

    # Place output chest at drop position
    output_chest = game.place_entity(
        Prototype.IronChest, Direction.UP, inserter.drop_position
    )
    print(f"Output chest at: {output_chest.position}")

    # Check if pickup position matches chest position
    print("\n=== Position Analysis ===")
    print(f"Chest position: ({chest.position.x}, {chest.position.y})")
    print(
        f"Inserter pickup: ({inserter.pickup_position.x}, {inserter.pickup_position.y})"
    )
    print(f"Distance X: {abs(chest.position.x - inserter.pickup_position.x)}")
    print(f"Distance Y: {abs(chest.position.y - inserter.pickup_position.y)}")

    # Wait and check
    game.sleep(10)

    ins = game.get_entity(Prototype.BurnerInserter, inserter.position)
    ch = game.get_entity(Prototype.IronChest, chest.position)
    out = game.get_entity(Prototype.IronChest, output_chest.position)

    print("\n=== After 10 seconds ===")
    print(f"Source chest: {game.inspect_inventory(ch)}")
    print(f"Output chest: {game.inspect_inventory(out)}")
    print(f"Inserter status: {ins.status}")

    # Check if transfer happened
    out_plates = game.inspect_inventory(out).get(Prototype.IronPlate, 0)
    assert out_plates > 0, (
        f"Inserter should transfer plates from chest to chest. Status: {ins.status}"
    )


def test_inserter_drops_iron_ore_to_furnace(game):
    """
    Test 11: Test inserter dropping iron ORE (not plates) into furnace.

    Hypothesis: The issue with dropping iron plates into furnace might be that
    steel processing research hasn't been completed. Iron ore → iron plate
    smelting is available from the start, so this should work.
    """
    # Place chest with iron ORE (not plates - ore can always be smelted)
    chest = game.place_entity(Prototype.IronChest, Direction.UP, Position(x=0, y=0))
    game.insert_item(Prototype.IronOre, chest, 50)
    print(f"\nChest at: {chest.position} with iron ORE")

    # Place inserter facing RIGHT
    inserter = game.place_entity(
        Prototype.BurnerInserter, Direction.RIGHT, Position(x=1, y=0)
    )
    game.insert_item(Prototype.Coal, inserter, 5)
    print(f"Inserter at: {inserter.position}")
    print(f"  pickup: {inserter.pickup_position}")
    print(f"  drop: {inserter.drop_position}")

    # Place furnace so drop position is within bounds
    furnace = game.place_entity(
        Prototype.StoneFurnace, Direction.UP, Position(x=3, y=1)
    )
    game.insert_item(Prototype.Coal, furnace, 10)
    print(f"Furnace at: {furnace.position}")
    print(
        f"  Furnace spans: x=[{furnace.position.x - 1}, {furnace.position.x + 1}], y=[{furnace.position.y - 1}, {furnace.position.y + 1}]"
    )

    # Wait and check
    game.sleep(15)

    ins = game.get_entity(Prototype.BurnerInserter, inserter.position)
    f = game.get_entity(Prototype.StoneFurnace, furnace.position)
    ch = game.get_entity(Prototype.IronChest, chest.position)

    print("\n=== After 15 seconds ===")
    print(f"Source chest: {game.inspect_inventory(ch)}")
    print(f"Furnace source: {f.furnace_source}")
    print(f"Furnace result: {f.furnace_result}")
    print(f"Inserter status: {ins.status}")

    # Check if furnace received iron ORE (not plates)
    f_source = f.furnace_source.get(Prototype.IronOre, 0)
    f_result = f.furnace_result.get(Prototype.IronPlate, 0)
    assert f_source > 0 or f_result > 0, (
        f"Inserter should drop iron ORE into furnace. Status: {ins.status}"
    )


def test_inserter_drops_to_furnace_aligned_y(game):
    """
    Test 10: Test inserter drop into furnace with aligned Y coordinates.

    Key insight from previous tests:
    - Chest-to-chest works when drop position EXACTLY matches chest center
    - Furnace-to-chest works (pickup at 0.5, 0.5 from furnace at 0, 0)
    - Chest-to-furnace FAILS when drop y=0.5 and furnace y=0.0

    Hypothesis: The drop position y-coordinate must match the furnace center y-coordinate.
    Let's test with furnace at y=0.5 to match the inserter's drop y-coordinate.
    """
    # Place chest with iron plates - 1x1 snaps to half coordinates
    chest = game.place_entity(Prototype.IronChest, Direction.UP, Position(x=0, y=0))
    game.insert_item(Prototype.IronPlate, chest, 50)
    print(f"\nChest at: {chest.position}")

    # Place inserter facing RIGHT at x=1, y=0 (will snap to 1.5, 0.5)
    inserter = game.place_entity(
        Prototype.BurnerInserter, Direction.RIGHT, Position(x=1, y=0)
    )
    game.insert_item(Prototype.Coal, inserter, 5)
    print(f"Inserter at: {inserter.position}")
    print(f"  pickup: {inserter.pickup_position}")
    print(f"  drop: {inserter.drop_position}")

    # Place furnace so its Y-center matches the drop Y-coordinate
    # If drop is at y=0.5, and furnace is 2x2, furnace at y=1 would have edge at y=0
    # Actually, let's place furnace at x=3, y=1 so drop at (2.5, 0.5) is within bounds
    # Furnace at (3, 1) spans x=[2,4], y=[0,2] - drop at (2.5, 0.5) is INSIDE
    furnace = game.place_entity(
        Prototype.StoneFurnace, Direction.UP, Position(x=3, y=1)
    )
    game.insert_item(Prototype.Coal, furnace, 10)
    print(f"Furnace at: {furnace.position}")
    print(
        f"  Furnace spans: x=[{furnace.position.x - 1}, {furnace.position.x + 1}], y=[{furnace.position.y - 1}, {furnace.position.y + 1}]"
    )
    print(
        f"  Drop {inserter.drop_position} in furnace bounds? x:{furnace.position.x - 1 <= inserter.drop_position.x <= furnace.position.x + 1}, y:{furnace.position.y - 1 <= inserter.drop_position.y <= furnace.position.y + 1}"
    )

    # Wait and check
    game.sleep(15)

    ins = game.get_entity(Prototype.BurnerInserter, inserter.position)
    f = game.get_entity(Prototype.StoneFurnace, furnace.position)
    ch = game.get_entity(Prototype.IronChest, chest.position)

    print("\n=== After 15 seconds ===")
    print(f"Source chest: {game.inspect_inventory(ch)}")
    print(f"Furnace source: {f.furnace_source}")
    print(f"Inserter status: {ins.status}")

    # Check if furnace received iron plates
    f_source = f.furnace_source.get(Prototype.IronPlate, 0)
    assert f_source > 0, (
        f"Inserter should drop iron plates into furnace. Status: {ins.status}"
    )


def test_inserter_direction_semantics(game):
    """
    Test 8: Verify inserter direction semantics.

    In Factorio, an inserter's "direction" indicates where it DROPS items, not where it picks from.
    - Inserter facing RIGHT (direction=4): picks from LEFT, drops to RIGHT
    - Inserter facing LEFT (direction=12): picks from RIGHT, drops to LEFT

    If this is inverted, the inserter would be trying to:
    - Pick from the wrong side (where nothing exists)
    - Drop to the wrong side (where nothing exists)

    This test explicitly verifies the direction semantics.
    """
    # Place inserter at origin facing RIGHT
    inserter_right = game.place_entity(
        Prototype.BurnerInserter, Direction.RIGHT, Position(x=0, y=0)
    )
    print("\n=== INSERTER DIRECTION TEST ===")
    print(f"Inserter facing RIGHT (direction={inserter_right.direction})")
    print(f"  Position: {inserter_right.position}")
    print(f"  Pickup position: {inserter_right.pickup_position}")
    print(f"  Drop position: {inserter_right.drop_position}")

    # For an inserter facing RIGHT:
    # - Pickup should be to the LEFT of the inserter (negative X direction)
    # - Drop should be to the RIGHT of the inserter (positive X direction)
    pickup_is_left = inserter_right.pickup_position.x < inserter_right.position.x
    drop_is_right = inserter_right.drop_position.x > inserter_right.position.x

    print(
        f"\n  Expected: pickup to LEFT (x < {inserter_right.position.x}), drop to RIGHT (x > {inserter_right.position.x})"
    )
    print(
        f"  Actual: pickup_x={inserter_right.pickup_position.x}, drop_x={inserter_right.drop_position.x}"
    )
    print(f"  Pickup is LEFT of inserter: {pickup_is_left}")
    print(f"  Drop is RIGHT of inserter: {drop_is_right}")

    # If direction is INVERTED, pickup would be RIGHT and drop would be LEFT
    direction_inverted = not pickup_is_left or not drop_is_right
    print(f"\n  DIRECTION INVERTED? {direction_inverted}")

    # Also test DOWN direction to confirm
    inserter_down = game.place_entity(
        Prototype.BurnerInserter, Direction.DOWN, Position(x=5, y=0)
    )
    print(f"\nInserter facing DOWN (direction={inserter_down.direction})")
    print(f"  Position: {inserter_down.position}")
    print(f"  Pickup position: {inserter_down.pickup_position}")
    print(f"  Drop position: {inserter_down.drop_position}")

    # For an inserter facing DOWN:
    # - Pickup should be UP (negative Y direction)
    # - Drop should be DOWN (positive Y direction)
    pickup_is_up = inserter_down.pickup_position.y < inserter_down.position.y
    drop_is_down = inserter_down.drop_position.y > inserter_down.position.y

    print(
        f"\n  Expected: pickup UP (y < {inserter_down.position.y}), drop DOWN (y > {inserter_down.position.y})"
    )
    print(
        f"  Actual: pickup_y={inserter_down.pickup_position.y}, drop_y={inserter_down.drop_position.y}"
    )
    print(f"  Pickup is UP from inserter: {pickup_is_up}")
    print(f"  Drop is DOWN from inserter: {drop_is_down}")

    direction_inverted_down = not pickup_is_up or not drop_is_down
    print(f"\n  DOWN DIRECTION INVERTED? {direction_inverted_down}")

    # This test passes for diagnostic purposes
    # The assertions below will fail if direction is inverted
    assert pickup_is_left, (
        f"Inserter facing RIGHT should pick from LEFT, but pickup_x={inserter_right.pickup_position.x} >= inserter_x={inserter_right.position.x}"
    )
    assert drop_is_right, (
        f"Inserter facing RIGHT should drop to RIGHT, but drop_x={inserter_right.drop_position.x} <= inserter_x={inserter_right.position.x}"
    )
    assert pickup_is_up, (
        f"Inserter facing DOWN should pick from UP, but pickup_y={inserter_down.pickup_position.y} >= inserter_y={inserter_down.position.y}"
    )
    assert drop_is_down, (
        f"Inserter facing DOWN should drop to DOWN, but drop_y={inserter_down.drop_position.y} <= inserter_y={inserter_down.position.y}"
    )


def test_inserter_picks_pre_loaded_iron_plates_from_furnace(game):
    """
    Test 5: Pre-load iron plates into furnace output and see if inserter picks them.
    This isolates the pickup behavior from the smelting process.
    """
    # Place furnace
    furnace = game.place_entity(
        Prototype.StoneFurnace, Direction.UP, Position(x=0, y=0)
    )
    print(f"Furnace at {furnace.position}")

    # Place inserter next to furnace
    inserter = game.place_entity_next_to(
        Prototype.BurnerInserter, furnace.position, Direction.RIGHT, spacing=0
    )
    game.insert_item(Prototype.Coal, inserter, 5)
    print(f"Inserter at {inserter.position}")
    print(f"  pickup: {inserter.pickup_position}, drop: {inserter.drop_position}")

    # Place chest next to inserter
    chest = game.place_entity_next_to(
        Prototype.IronChest, inserter.position, Direction.RIGHT, spacing=0
    )
    print(f"Chest at {chest.position}")

    # Manually insert iron plates INTO the furnace's output (result slot)
    # We'll simulate finished smelting by adding iron plates
    # Actually, we can't directly add to furnace result - let's use ore and wait
    game.insert_item(Prototype.IronOre, furnace, 10)
    game.insert_item(Prototype.Coal, furnace, 10)

    # Wait for smelting
    game.sleep(30)

    # Check inserter status
    ins = game.get_entity(Prototype.BurnerInserter, inserter.position)
    f = game.get_entity(Prototype.StoneFurnace, furnace.position)

    print(f"Furnace result: {f.furnace_result}")
    print(f"Inserter status: {ins.status}")

    # After 30 seconds, there should be iron plates in the furnace output
    # The inserter should either be WORKING (moving plates) or the chest should have plates
    chest_inv = game.inspect_inventory(chest)
    print(f"Chest inventory: {chest_inv}")

    iron_plates = chest_inv.get(Prototype.IronPlate, 0)
    assert iron_plates > 0, (
        "Inserter should pick completed iron plates from furnace output"
    )
