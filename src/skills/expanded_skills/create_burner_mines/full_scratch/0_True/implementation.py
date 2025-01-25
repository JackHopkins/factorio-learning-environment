
from factorio_instance import *

"""
Construct a stone mining facility using a single burner mining drill, delivering the mined stone to a stone furnace situated far from the extraction point.
"""

"""
Step 1: Place the burner mining drill on a stone patch
"""
# Find the nearest stone patch
stone_position = get_resource_patch(Resource.Stone, nearest(Resource.Stone))
print(f"Nearest stone patch found at: {stone_position}")

# Move to the stone patch
move_to(stone_position.bounding_box.center())
print(f"Moved to stone patch at: {stone_position}")

# Place the burner mining drill
drill = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=stone_position.bounding_box.center())
print(f"Placed burner mining drill at: {drill.position}")

# Fuel the burner mining drill
fueled_drill = insert_item(Prototype.Coal, drill, quantity=20)
print(f"Inserted coal into the burner mining drill")

# Verify that the drill is fueled
coal_in_drill = fueled_drill.fuel.get(Prototype.Coal, 0)
assert coal_in_drill > 0, "Failed to fuel drill"
print("Burner mining drill successfully placed and fueled")

"""
Step 2: Place the stone furnace far from the drill
"""
# Calculate a position 10 tiles to the right of the drill
drill_position = drill.position
furnace_position = Position(x=drill_position.x + 10, y=drill_position.y)

# Move to the calculated position
print(f"Moving to position: {furnace_position}")
move_to(furnace_position)

# Place the stone furnace
furnace = place_entity(Prototype.StoneFurnace, direction=Direction.UP, position=furnace_position)
print(f"Placed stone furnace at: {furnace.position}")

"""
Step 3: Set up the burner inserter
"""
# Move next to the stone furnace
move_to(furnace_position)

# Place the burner inserter adjacent to the furnace
inserter = place_entity_next_to(Prototype.BurnerInserter, furnace_position, direction=Direction.LEFT) 
print(f"Placed burner inserter at: {inserter.position}")

# Rotate the inserter so it will insert items into the furnace
inserter = rotate_entity(inserter, Direction.RIGHT)

# Fuel the burner inserter
inserter_fueled = insert_item(Prototype.Coal, inserter, quantity=10)
print(f"Inserted coal into the burner inserter")

# Verify that the inserter is fueled
coal_in_inserter = inserter_fueled.fuel.get(Prototype.Coal, 0)
assert coal_in_inserter > 0, "Failed to fuel inserter"

"""
Step 4: Connect the drill to the furnace inserter using transport belts
"""
print("Connecting drill to inserter with transport belts...")
belts = connect_entities(drill.drop_position, inserter.pickup_position, Prototype.TransportBelt)
assert belts, "Failed to connect drill to furnace inserter with transport belts"
print("Successfully connected drill to inserter with transport belts")

"""
Step 5: Verify the setup
"""
# Wait for 30 seconds to allow the system to operate
print("Waiting for 30 seconds to allow the system to operate...")
sleep(30)
print("30 seconds have passed. Checking the setup now.")

# Move near the furnace to inspect its contents
move_to(furnace.position)

# Check the contents of the stone furnace for stone
furnace = get_entity(Prototype.StoneFurnace, furnace.position)
furnace_inventory = inspect_inventory(furnace)
stone_count = furnace_inventory.get(Prototype.Stone, 0)
print(f"Stone in the stone furnace: {stone_count}")
assert stone_count > 0, "No stone found in the stone furnace. Setup verification failed."
print("Setup verification complete. Stone mining facility is operational.")
