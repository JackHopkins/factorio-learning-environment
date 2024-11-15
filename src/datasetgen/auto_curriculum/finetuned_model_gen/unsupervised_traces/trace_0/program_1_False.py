

from factorio_instance import *

"""
Planning: We need to create a coal mining setup using a burner mining drill that deposits coal into a wooden chest.
We already have a burner mining drill on the map, and we have wooden chests and burner inserters in our inventory.
We need to:
1. Find the wooden chest on the map
2. Place a burner inserter next to the chest
3. Connect the burner mining drill to the inserter using transport belts
4. Fuel the inserter
5. Verify the setup by checking if coal is being deposited into the chest
"""

"""
Step 1: Find the wooden chest and move to its position
"""
# Get the position of the wooden chest
chests = get_entities({Prototype.WoodenChest})
chest = chests[0]
chest_position = chest.position
print(f"Found wooden chest at: {chest_position}")

# Move to the chest position
move_to(chest_position)
print(f"Moved to wooden chest at: {chest_position}")

"""
Step 2: Place and set up the burner inserter
"""
# Place the burner inserter next to the chest
inserter = place_entity_next_to(Prototype.BurnerInserter, chest_position, direction=Direction.RIGHT)
print(f"Placed burner inserter at: {inserter.position}")

# Rotate the inserter to insert items into the chest
inserter = rotate_entity(inserter, Direction.LEFT)
print(f"Rotated inserter to face the chest")

# Fuel the inserter
fueled_inserter = insert_item(Prototype.Coal, inserter, quantity=5)
coal_in_inserter = fueled_inserter.fuel.get(Prototype.Coal, 0)
assert coal_in_inserter > 0, "Failed to fuel inserter"
print("Inserter successfully placed, rotated, and fueled")

"""
Step 3: Connect the drill to the inserter using transport belts
"""
# Get the burner mining drill entity
drill = get_entities({Prototype.BurnerMiningDrill})[0]
print(f"Using burner mining drill at: {drill.position}")

# Connect the drill's drop position to the inserter's pickup position with transport belts
belts = connect_entities(drill.drop_position, inserter.pickup_position, Prototype.TransportBelt)
assert belts, "Failed to connect drill to inserter with transport belts"
print("Successfully connected drill to inserter with transport belts")

"""
Step 4: Verify the setup
"""
# Wait for 30 seconds to allow the system to operate
print("Waiting for 30 seconds to allow the system to operate...")
sleep(30)
print("30 seconds have passed. Checking the setup now.")

# Move near the chest to inspect its contents
move_to(chest_position)

# Check the contents of the wooden chest for coal
chest = get_entity(Prototype.WoodenChest, chest_position)
chest_inventory = inspect_inventory(chest)
coal_count = chest_inventory.get(Prototype.Coal, 0)
print(f"Coal in the wooden chest: {coal_count}")
assert coal_count > 0, "No coal found in the wooden chest. Setup verification failed."
print("Setup verification complete. The coal mining setup is working correctly.")

