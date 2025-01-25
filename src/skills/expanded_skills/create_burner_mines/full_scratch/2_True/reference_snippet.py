from factorio_instance import *

"""
We need create an automated copper burner mine that mines copper ore to a chest further away from it with 2 burner mining drills. 
The final setup should be checked by looking if the chest has any copper ore in it
"""


"""
Step 1: Place the burner mining drills. We need to carry out the following substeps:
- Move to a copper ore patch as the api requires to first move to the position where we want to place the entity
- Place the burner mining drills on the copper ore patch
- Add coal to fuel the burner mining drill
"""

# Find the nearest copper ore patch
copper_ore_position = get_resource_patch(Resource.CopperOre, nearest(Resource.CopperOre))
print(f"Nearest copper ore found at: {copper_ore_position}")

# Move to the copper ore patch to place the burner mining drills
# move to the center of the patch, the place where the drills will be placed
move_to(copper_ore_position.bounding_box.center())
print(f"Moved to copper ore patch at: {copper_ore_position}")

# Place the first burner mining drill on the copper ore patch
# place it at the center of the patch
drill = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=copper_ore_position.bounding_box.center())
print(f"Placed burner mining drill at: {drill.position}")

# Add coal to fuel the first burner mining drill
# Also get a updated fueled_drill variable to refresh the drill variable with the updated fuel level
fueled_drill = insert_item(Prototype.Coal, drill, quantity=20)
print(f"Inserted {coal_inserted} coal into the burner mining drill")

# Verify that the drill is fueled
# We use the updated fueled_drill variabe to check the fuel level
# We also use the .fuel attribute to get the fuel inventory of the entity as the fuel does not end up in the normal inspect inventory
coal_in_drill = fueled_drill.fuel.get(Prototype.Coal, 0)
assert coal_in_drill > 0, "Failed to fuel drill"
print("Burner mining drill successfully placed and fueled")

# Place the second burner mining drill on the copper ore patch
# Place it diirectly next to the first drill
second_drill = place_entity_next_to(Prototype.BurnerMiningDrill, direction=Direction.UP, reference_position=fueled_drill.position, spacing = 1)
print(f"Placed burner mining drill at: {drill.position}")

# Add coal to fuel the second burner mining drill
# Also get a updated fueled_drill variable to refresh the drill variable with the updated fuel level
fueled_second_drill = insert_item(Prototype.Coal, second_drill, quantity=20)
print(f"Inserted {coal_inserted} coal into the burner mining drill")

# Verify that the second_drill is fueled
# We use the updated fueled_second_drill variabe to check the fuel level
# We also use the .fuel attribute to get the fuel inventory of the entity as the fuel does not end up in the normal inspect inventory
coal_in_drill = fueled_second_drill.fuel.get(Prototype.Coal, 0)
assert coal_in_drill > 0, "Failed to fuel second drill"
print("Burner mining drill successfully placed and fueled")

# Print the current inventory
current_inventory = inspect_inventory()
print(f"Current inventory after placing and fueling the drill: {current_inventory}")
###SEP

"""
Step 2: Place the wooden chest. We need to carry out the following substeps:
- Move to a position further away from the drill (at least 5 tiles away) as the api requires to first move to the position where we want to place the entity
- Place the wooden chest at this position
"""

# Calculate a position 7 tiles to the right of the drill
drill_position = drill.position
chest_position = Position(x=drill_position.x + 7, y=drill_position.y)

# Move to the calculated position
# We need to move to the position where we want to place the wooden chest
print(f"Moving to position: {chest_position}")
move_to(chest_position)

# Place the wooden chest
chest = place_entity(Prototype.WoodenChest, direction=Direction.UP, position=chest_position)
print(f"Placed wooden chest at: {chest.position}")

# Print the current inventory
current_inventory = inspect_inventory()
print(f"Current inventory after placing the wooden chest: {current_inventory}")

###SEP
"""
Step 3: Set up the burner inserter. First we need to place down the inserters and only then connect the drills to inserters. We need to carry out the following substeps:
- Move next to the wooden chest
- Place the burner inserter adjacent to the chest
- Rotate the inserter so it will insert items into the chest
- Add coal to fuel the burner inserter
"""
#Step Execution

# Move next to the wooden chest
move_to(chest_position)

# Place the burner inserter adjacent to the chest
inserter = place_entity_next_to(Prototype.BurnerInserter, chest_position, direction=Direction.RIGHT) 
print(f"Placed burner inserter at: {inserter.position}")

# Rotate the inserter so it will insert items into the chest
# By default, the inserter is oriented to pick up items from the chest
inserter = rotate_entity(inserter, Direction.LEFT)

# Add coal to fuel the burner inserter
# We also update the inserter variable with the updated fuel level
inserter_fueled = insert_item(Prototype.Coal, inserter, quantity=10)
print(f"Inserted {coal_inserted} coal into the burner inserter")

# Verify that the inserter is fueled
# We use the updated inserter_fueled variable to check the fuel level
coal_in_inserter = inserter_fueled.fuel.get(Prototype.Coal, 0)
assert coal_in_inserter > 0, "Failed to fuel inserter"

# Print the current inventory
current_inventory = inspect_inventory()
print(f"Current inventory after setting up the burner inserter: {current_inventory}")

###SEP
"""
Step 4: Connect the drills to the chest inserter. We need to carry out the following substeps:
- Use transport belts to connect the drop position of the burner mining drills to the pickup position of the burner inserter
- Ensure the belt is properly aligned and connected
"""
#Step Execution

# Connect the first drill's drop position to the inserter's pickup position with transport belts
print("Connecting drill to inserter with transport belts...")
first_belts = connect_entities(drill.drop_position, inserter.pickup_position, Prototype.TransportBelt)
assert first_belts, "Failed to connect first drill to chest inserter with transport belts"

# Connect the second drill's drop position to the inserter's pickup position with transport belts
print("Connecting drill to inserter with transport belts...")
second_belts = connect_entities(second_drill.drop_position, inserter.pickup_position, Prototype.TransportBelt)
assert second_belts, "Failed to connect second drill to chest inserter with transport belts"

print("Successfully connected drills to inserter with transport belts")

###SEP
"""
Step 5: Verify the setup. We need to carry out the following substeps:
- Wait for 30 seconds to allow the system to operate
- Get the latest chest entity as the chest will have the updated inventory
- Check the contents of the wooden chest for copper ore
- If copper ore is present, the setup is working correctly
##
"""
# Inventory at the start of step {'transport-belt': 91, 'burner-inserter': 4, 'burner-mining-drill': 2, 'stone-furnace': 9, 'coal': 4}
#Step Execution

# Wait for 30 seconds to allow the system to operate
print("Waiting for 30 seconds to allow the system to operate...")
sleep(30)
print("30 seconds have passed. Checking the setup now.")

# Move near the chest to inspect its contents
move_to(chest.position)


# Check the contents of the wooden chest for copper ore
# First we need to get the latest chest entity as the chest will have the updated inventory
chest = get_entity(Prototype.WoodenChest, chest.position)

# Next we inspect the inventory as the chest will always have everything in their inventory
chest_inventory = inspect_inventory(chest)
copper_ore_count = chest_inventory.get(Prototype.CopperOre, 0)
print(f"Copper ore in the wooden chest: {copper_ore_count}")
assert copper_ore_count > 0, "No copper ore found in the wooden chest. Setup verification failed."
print("\nSetup verification complete.")
