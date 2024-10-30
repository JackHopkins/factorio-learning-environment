
from factorio_instance import *

"""
Create an automated iron ore mining setup with a single burner mining drill that feeds into an iron chest placed at a distance.
"""

"""
Step 1: Place the burner mining drill on an iron ore patch
"""
# Find the nearest iron ore patch
iron_ore_position = get_resource_patch(Resource.IronOre, nearest(Resource.IronOre))
print(f"Nearest iron ore found at: {iron_ore_position}")

# Move to the iron ore patch
move_to(iron_ore_position.bounding_box.center)
print(f"Moved to iron ore patch at: {iron_ore_position}")

# Place the burner mining drill
drill = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=iron_ore_position.bounding_box.center)
print(f"Placed burner mining drill at: {drill.position}")

# Fuel the burner mining drill
fueled_drill = insert_item(Prototype.Coal, drill, quantity=20)
print(f"Inserted coal into the burner mining drill")

# Verify that the drill is fueled
coal_in_drill = fueled_drill.fuel.get(Prototype.Coal, 0)
assert coal_in_drill > 0, "Failed to fuel drill"
print("Burner mining drill successfully placed and fueled")

"""
Step 2: Place the iron chest at a distance
"""
# Calculate a position 5 tiles to the right of the drill
drill_position = drill.position
chest_position = Position(x=drill_position.x + 5, y=drill_position.y)

# Move to the calculated position
print(f"Moving to position: {chest_position}")
move_to(chest_position)

# Place the iron chest
chest = place_entity(Prototype.IronChest, direction=Direction.UP, position=chest_position)
print(f"Placed iron chest at: {chest.position}")

"""
Step 3: Set up the burner inserter
"""
# Move next to the iron chest
move_to(chest_position)

# Place the burner inserter adjacent to the chest
inserter = place_entity_next_to(Prototype.BurnerInserter, chest_position, direction=Direction.RIGHT)
print(f"Placed burner inserter at: {inserter.position}")

# Rotate the inserter to insert items into the chest
inserter = rotate_entity(inserter, Direction.LEFT)

# Fuel the burner inserter
inserter_fueled = insert_item(Prototype.Coal, inserter, quantity=10)
print(f"Inserted coal into the burner inserter")

# Verify that the inserter is fueled
coal_in_inserter = inserter_fueled.fuel.get(Prototype.Coal, 0)
assert coal_in_inserter > 0, "Failed to fuel inserter"

"""
Step 4: Connect the drill to the chest inserter using transport belts
"""
print("Connecting drill to inserter with transport belts...")
belts = connect_entities(drill.drop_position, inserter.pickup_position, Prototype.TransportBelt)
assert belts, "Failed to connect drill to chest inserter with transport belts"
print("Successfully connected drill to inserter with transport belts")

"""
Step 5: Verify the setup
"""
print("Waiting for 30 seconds to allow the system to operate...")
sleep(30)
print("30 seconds have passed. Checking the setup now.")

# Move near the chest to inspect its contents
move_to(chest.position)

# Check the contents of the iron chest for iron ore
chest = get_entity(Prototype.IronChest, chest.position)
chest_inventory = inspect_inventory(chest)
iron_ore_count = chest_inventory.get(Prototype.IronOre, 0)
print(f"Iron ore in the iron chest: {iron_ore_count}")
assert iron_ore_count > 0, "No iron ore found in the iron chest. Setup verification failed."
print("Setup verification complete. Automated iron ore mining setup is working correctly.")
