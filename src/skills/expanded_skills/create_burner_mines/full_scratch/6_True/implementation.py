
from factorio_instance import *

"""
Set up an automated stone mining operation using 2 burner mining drills: 
one outputting to an iron chest 12 tiles away, and another feeding a stone furnace 7 tiles away to create stone bricks.
"""

"""
Step 1: Place the burner mining drills on a stone patch
"""

# Find the nearest stone patch
stone_position = get_resource_patch(Resource.Stone, nearest(Resource.Stone))
print(f"Nearest stone patch found at: {stone_position}")

# Move to the stone patch
move_to(stone_position.bounding_box.center)
print(f"Moved to stone patch at: {stone_position}")

# Place the first burner mining drill
drill1 = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=stone_position.bounding_box.center)
print(f"Placed first burner mining drill at: {drill1.position}")

# Place the second burner mining drill next to the first one
drill2 = place_entity_next_to(Prototype.BurnerMiningDrill, direction=Direction.UP, reference_position=drill1.position, spacing=1)
print(f"Placed second burner mining drill at: {drill2.position}")

# Fuel both drills
for drill in [drill1, drill2]:
    fueled_drill = insert_item(Prototype.Coal, drill, quantity=20)
    coal_in_drill = fueled_drill.fuel.get(Prototype.Coal, 0)
    assert coal_in_drill > 0, f"Failed to fuel drill at {drill.position}"
    print(f"Burner mining drill at {drill.position} successfully fueled")

"""
Step 2: Place the iron chest and stone furnace
"""

# Calculate positions for chest and furnace
chest_position = Position(x=drill1.position.x + 12, y=drill1.position.y)
furnace_position = Position(x=drill2.position.x + 7, y=drill2.position.y)

# Place the iron chest
move_to(chest_position)
chest = place_entity(Prototype.IronChest, direction=Direction.UP, position=chest_position)
print(f"Placed iron chest at: {chest.position}")

# Place the stone furnace
move_to(furnace_position)
furnace = place_entity(Prototype.StoneFurnace, direction=Direction.UP, position=furnace_position)
print(f"Placed stone furnace at: {furnace.position}")

# Fuel the furnace
fueled_furnace = insert_item(Prototype.Coal, furnace, quantity=20)
coal_in_furnace = fueled_furnace.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace > 0, "Failed to fuel furnace"
print("Stone furnace successfully fueled")

"""
Step 3: Set up the burner inserters
"""

# Place and fuel inserter for the chest
chest_inserter = place_entity_next_to(Prototype.BurnerInserter, chest.position, direction=Direction.LEFT)
chest_inserter = rotate_entity(chest_inserter, Direction.RIGHT)
chest_inserter_fueled = insert_item(Prototype.Coal, chest_inserter, quantity=10)
assert chest_inserter_fueled.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel chest inserter"
print(f"Placed and fueled chest inserter at: {chest_inserter.position}")

# Place and fuel inserter for the furnace
furnace_inserter = place_entity_next_to(Prototype.BurnerInserter, furnace.position, direction=Direction.LEFT)
furnace_inserter = rotate_entity(furnace_inserter, Direction.RIGHT)
furnace_inserter_fueled = insert_item(Prototype.Coal, furnace_inserter, quantity=10)
assert furnace_inserter_fueled.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel furnace inserter"
print(f"Placed and fueled furnace inserter at: {furnace_inserter.position}")

"""
Step 4: Connect the drills to the inserters using transport belts
"""

# Connect first drill to chest inserter
belts1 = connect_entities(drill1.drop_position, chest_inserter.pickup_position, Prototype.TransportBelt)
assert belts1, "Failed to connect first drill to chest inserter with transport belts"
print("Successfully connected first drill to chest inserter")

# Connect second drill to furnace inserter
belts2 = connect_entities(drill2.drop_position, furnace_inserter.pickup_position, Prototype.TransportBelt)
assert belts2, "Failed to connect second drill to furnace inserter with transport belts"
print("Successfully connected second drill to furnace inserter")

"""
Step 5: Verify the setup
"""

print("Waiting for 30 seconds to allow the system to operate...")
sleep(30)

# Check iron chest for stone
move_to(chest.position)
chest = get_entity(Prototype.IronChest, chest.position)
chest_inventory = inspect_inventory(chest)
stone_count = chest_inventory.get(Prototype.Stone, 0)
print(f"Stone in the iron chest: {stone_count}")
assert stone_count > 0, "No stone found in the iron chest. Setup verification failed."
print("Stone found in the iron chest")

# Check furnace for stone bricks
furnace = get_entity(Prototype.StoneFurnace, furnace.position)
furnace_inventory = inspect_inventory(furnace)
stone_brick_count = furnace_inventory.get(Prototype.StoneBrick, 0)
print(f"Stone bricks in the furnace: {stone_brick_count}")
assert stone_brick_count > 0, "No stone bricks found in the furnace. Setup verification failed."
print("Stone bricks found in the furnace")

print("\nSetup verification complete. Automated stone mining operation is working correctly.")
