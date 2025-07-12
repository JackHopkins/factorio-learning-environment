from instance import *

"""
Step 1: Place the burner mining drill. We need to carry out the following substeps:
- Move to a copper ore patch
- Place the burner mining drill on the copper ore patch
- Add coal to fuel the burner mining drill
"""
# Inventory at the start of step {'wooden-chest': 1, 'transport-belt': 100, 'burner-inserter': 5, 'burner-mining-drill': 3, 'stone-furnace': 9, 'coal': 10}
# Step Execution

# Find the nearest copper ore patch
copper_ore_position = nearest(Resource.CopperOre)
print(f"Nearest copper ore found at: {copper_ore_position}")

# Move to the copper ore patch
move_to(copper_ore_position)
print(f"Moved to copper ore patch at: {copper_ore_position}")

# Place the burner mining drill on the copper ore patch
drill = place_entity(
    Prototype.BurnerMiningDrill, direction=Direction.UP, position=copper_ore_position
)
print(f"Placed burner mining drill at: {drill.position}")

# Add coal to fuel the burner mining drill
coal_inserted = insert_item(Prototype.Coal, drill, quantity=5)
print(f"Inserted {coal_inserted} coal into the burner mining drill")

# Verify that the drill is placed and fueled
entities_around = get_entities(
    {Prototype.BurnerMiningDrill}, position=copper_ore_position, radius=1
)
assert len(entities_around) > 0, "Failed to place burner mining drill"
print("Burner mining drill successfully placed and fueled")

# Print the current inventory
current_inventory = inspect_inventory()
print(f"Current inventory after placing and fueling the drill: {current_inventory}")
###SEP

"""
Step 2: Place the wooden chest. We need to carry out the following substeps:
- Move to a position further away from the drill (at least 5 tiles away)
- Place the wooden chest at this position
"""
# Inventory at the start of step {'wooden-chest': 1, 'transport-belt': 100, 'burner-inserter': 5, 'burner-mining-drill': 2, 'stone-furnace': 9, 'coal': 5}
# Step Execution

# Calculate a position 7 tiles to the right of the drill
drill_position = drill.position
chest_position = Position(x=drill_position.x + 7, y=drill_position.y)

# Move to the calculated position
print(f"Moving to position: {chest_position}")
move_to(chest_position)

# Place the wooden chest
chest = place_entity(
    Prototype.WoodenChest, direction=Direction.UP, position=chest_position
)
print(f"Placed wooden chest at: {chest.position}")

# Verify that the chest has been placed correctly
entities_around = get_entities(
    {Prototype.WoodenChest}, position=chest_position, radius=1
)
if len(entities_around) > 0:
    print("Wooden chest successfully placed")
else:
    print("Failed to place wooden chest")

# Print the current inventory
current_inventory = inspect_inventory()
print(f"Current inventory after placing the wooden chest: {current_inventory}")

###SEP
"""
Step 3: Set up the burner inserter. We need to carry out the following substeps:
- Move next to the wooden chest
- Place the burner inserter adjacent to the chest
- Rotate the inserter so it will insert items into the chest
- Add coal to fuel the burner inserter
"""
# Inventory at the start of step {'transport-belt': 100, 'burner-inserter': 5, 'burner-mining-drill': 2, 'stone-furnace': 9, 'coal': 5}
# Step Execution

# Move next to the wooden chest
move_to(chest_position)

# Place the burner inserter adjacent to the chest
inserter = place_entity_next_to(
    Prototype.BurnerInserter, chest_position, direction=Direction.RIGHT
)
print(f"Placed burner inserter at: {inserter.position}")

# Rotate the inserter so it will insert items into the chest
# By default, the inserter is oriented to pick up items from the chest
inserter = rotate_entity(inserter, Direction.LEFT)


# Add coal to fuel the burner inserter
inserter_fueled = insert_item(Prototype.Coal, inserter, quantity=1)
print(f"Inserted {coal_inserted} coal into the burner inserter")

# Verify that the inserter is fueled
coal_in_inserter = inserter_fueled.fuel.get("coal", 0)
assert coal_in_inserter > 0, "Failed to fuel inserter"

# Print the current inventory
current_inventory = inspect_inventory()
print(f"Current inventory after setting up the burner inserter: {current_inventory}")

###SEP
"""
Step 4: Connect the drill to the inserter. We need to carry out the following substeps:
- Use transport belts to connect the drop position of the burner mining drill to the pickup position of the burner inserter
- Ensure the belt is properly aligned and connected
"""
# Inventory at the start of step {'transport-belt': 100, 'burner-inserter': 4, 'burner-mining-drill': 2, 'stone-furnace': 9, 'coal': 4}
# Step Execution

# Connect the drill's drop position to the inserter's pickup position with transport belts
print("Connecting drill to inserter with transport belts...")
belts = connect_entities(
    drill.drop_position, inserter.pickup_position, Prototype.TransportBelt
)
assert belts, "Failed to connect drill to inserter with transport belts"
print("Successfully connected drill to inserter with transport belts")

###SEP
"""
Step 5: Verify the setup. We need to carry out the following substeps:
- Wait for 30 seconds to allow the system to operate
- Check the contents of the wooden chest for copper ore
- If copper ore is present, the setup is working correctly
"""
# Inventory at the start of step {'transport-belt': 91, 'burner-inserter': 4, 'burner-mining-drill': 2, 'stone-furnace': 9, 'coal': 4}
# Step Execution

# Wait for 30 seconds to allow the system to operate
print("Waiting for 30 seconds to allow the system to operate...")
sleep(30)
print("30 seconds have passed. Checking the setup now.")

# Move near the chest to inspect its contents
move_to(chest.position)


# Check the contents of the wooden chest for copper ore
chest_inventory = inspect_inventory(chest)
copper_ore_count = chest_inventory.get(Prototype.CopperOre, 0)
print(f"Copper ore in the wooden chest: {copper_ore_count}")
assert copper_ore_count > 0, (
    "No copper ore found in the wooden chest. Setup verification failed."
)
print("\nSetup verification complete.")
