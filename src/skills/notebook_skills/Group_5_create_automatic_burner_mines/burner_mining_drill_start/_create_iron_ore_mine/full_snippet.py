from factorio_instance import *

"""
Main Objective: We need create an automated iron burner mine that mines iron ore to a chest further away from it. First place down the drill, then the chest, then the inserter and then connect inserter with drill. The final setup should be checked by looking if the chest has any iron ore in it
"""



"""
Step 1: Place the burner mining drill. We need to carry out the following substeps:
- Move to the nearest iron ore patch
- Place the burner mining drill on the iron ore patch
- Fuel the burner mining drill with coal
"""
# Inventory at the start of step {'wooden-chest': 1, 'transport-belt': 100, 'burner-inserter': 5, 'burner-mining-drill': 3, 'stone-furnace': 9, 'coal': 10}
#Step Execution

# Find the nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
print(f"Nearest iron ore patch found at: {iron_ore_position}")

# Move to the iron ore patch
move_to(iron_ore_position)
print(f"Moved to iron ore patch at: {iron_ore_position}")

# Place the burner mining drill on the iron ore patch
drill = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=iron_ore_position)
print(f"Placed burner mining drill at: {drill.position}")

# Ensure the drill was placed correctly
entities = get_entities({Prototype.BurnerMiningDrill}, position=iron_ore_position, radius=1)
assert len(entities) > 0, "Failed to place burner mining drill"
print("Successfully placed burner mining drill")

# Fuel the burner mining drill with coal
insert_item(Prototype.Coal, drill, quantity=5)
print("Inserted coal into burner mining drill")

# Print the current inventory for debugging
print(f"Current inventory after placing and fueling drill: {inspect_inventory()}")

print("Successfully completed step 1: Placed and fueled burner mining drill")


"""
Step 2: Place the wooden chest. We need to carry out the following substeps:
- Move to a position further away from the drill (at least 5 tiles away)
- Place the wooden chest at this position
"""
# Inventory at the start of step {'wooden-chest': 1, 'transport-belt': 100, 'burner-inserter': 5, 'burner-mining-drill': 2, 'stone-furnace': 9, 'coal': 5}
#Step Execution

# Get the current position of the drill
drill_position = drill.position
print(f"Current drill position: {drill_position}")

# Calculate a position 7 tiles south of the drill
chest_position = Position(x=drill_position.x, y=drill_position.y + 7)
print(f"Calculated chest position: {chest_position}")

# Move to the calculated position
move_to(chest_position)
print(f"Moved to position: {chest_position}")

# Place the wooden chest
chest = place_entity(Prototype.WoodenChest, direction=Direction.UP, position=chest_position)
print(f"Placed wooden chest at: {chest.position}")

# Verify that the chest was placed correctly
entities = get_entities({Prototype.WoodenChest}, position=chest_position, radius=1)
assert len(entities) > 0, "Failed to place wooden chest"
print("Successfully placed wooden chest")

# Calculate and print the distance between the drill and the chest
distance = ((chest.position.x - drill.position.x)**2 + (chest.position.y - drill.position.y)**2)**0.5
print(f"Distance between drill and chest: {distance} tiles")
assert distance >= 5, "Chest is not at least 5 tiles away from the drill"

# Print the current inventory for debugging
print(f"Current inventory after placing chest: {inspect_inventory()}")

print("Successfully completed step 2: Placed wooden chest")


"""
Step 3: Set up the burner inserter. We need to carry out the following substeps:
- Move next to the wooden chest
- Place the burner inserter adjacent to the chest
- Rotate the inserter so it will insert items into the chest
- Fuel the burner inserter with coal
"""
# Inventory at the start of step {'transport-belt': 100, 'burner-inserter': 5, 'burner-mining-drill': 2, 'stone-furnace': 9, 'coal': 5}
#Step Execution

# Move next to the wooden chest
chest_position = Position(x=-11.5, y=26.5)
move_to(chest_position)
print(f"Moved next to the wooden chest at: {chest_position}")

# Place the burner inserter to the left of the chest
inserter_position = Position(x=chest_position.x - 1, y=chest_position.y)
inserter = place_entity(Prototype.BurnerInserter, direction=Direction.RIGHT, position=inserter_position)
print(f"Placed burner inserter at: {inserter.position}")

# Verify that the inserter was placed correctly
entities = get_entities({Prototype.BurnerInserter}, position=inserter_position, radius=1)
assert len(entities) > 0, "Failed to place burner inserter"
print("Successfully placed burner inserter")

# Rotate the inserter to face the chest (it should already be facing right, but let's make sure)
inserter = rotate_entity(inserter, Direction.RIGHT)
print(f"Rotated inserter to face: {inserter.direction}")

# Fuel the burner inserter with coal
insert_item(Prototype.Coal, inserter, quantity=5)
print("Inserted coal into burner inserter")

# Print the current inventory for debugging
print(f"Current inventory after setting up inserter: {inspect_inventory()}")

# Final check
assert inserter.direction.value == Direction.RIGHT.value, "Inserter is not facing the correct direction"
assert abs(inserter.position.x - chest_position.x) == 1 and abs(inserter.position.y - chest_position.y) < 0.1, "Inserter is not adjacent to the chest"

print("Successfully completed step 3: Set up the burner inserter")


"""
Step 4: Connect the drill to the inserter. We need to carry out the following substeps:
- Use transport belts to connect the drop position of the burner mining drill to the pickup position of the burner inserter
- Ensure the belt is properly aligned and connected
"""
# Placeholder 4

"""
Step 5: Check the setup. We need to carry out the following substeps:
- Wait for 30 seconds to allow the system to operate
- Check the contents of the wooden chest for iron ore
- If iron ore is present in the chest, the setup is working correctly

##
"""
# Placeholder 5