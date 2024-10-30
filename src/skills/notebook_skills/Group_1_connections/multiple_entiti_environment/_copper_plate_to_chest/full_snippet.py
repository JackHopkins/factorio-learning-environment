from factorio_instance import *

"""
Main Objective: We need to set up copper plate transport from a furnace to a chest. The final setup should be checked by looking if the chest where we sent plates to has copper plates
"""



"""
Step 1: Place inserter next to the furnace. We need to:
- Move to the furnace at position (0, -5)
- Place a burner inserter next to the furnace's output
- Fuel the inserter with coal from the nearby chest
"""
# Inventory at the start of step {'transport-belt': 100, 'burner-inserter': 5}
#Step Execution

# Move to the furnace
furnace_position = Position(x=0, y=-5)
move_to(furnace_position)
print(f"Moved to furnace at position {furnace_position}")

# Get the furnace entity
furnace = get_entity(Prototype.StoneFurnace, furnace_position)
assert furnace is not None, f"Failed to find furnace at {furnace_position}"
print(f"Found furnace: {furnace}")

# Place burner inserter next to the furnace's output (south side)
inserter_position = Position(x=furnace.position.x, y=furnace.position.y + 1)
inserter = place_entity(Prototype.BurnerInserter, Direction.UP, inserter_position)
assert inserter is not None, f"Failed to place inserter at {inserter_position}"
print(f"Placed burner inserter at {inserter_position}")

# Find the nearby chest with coal
chests = get_entities({Prototype.WoodenChest})
coal_chest = next((chest for chest in chests if inspect_inventory(chest).get('coal', 0) > 0), None)

if coal_chest:
    print(f"Found chest with coal at {coal_chest.position}")
    
    # Move to the chest
    move_to(coal_chest.position)
    print(f"Moved to chest at {coal_chest.position}")
    
    # Extract coal from the chest
    coal_extracted = extract_item(Prototype.Coal, coal_chest.position, 5)
    assert coal_extracted > 0, f"Failed to extract coal from chest at {coal_chest.position}"
    print(f"Extracted {coal_extracted} coal from the chest")
    
    # Move back to the inserter
    move_to(inserter.position)
    print(f"Moved back to inserter at {inserter.position}")
    
    # Insert coal into the inserter
    insert_item(Prototype.Coal, inserter, 5)
    print("Inserted coal into the inserter")
else:
    raise Exception("No chest with coal found nearby")

# Print final setup
print(f"Furnace setup complete. Furnace at {furnace.position}, Inserter at {inserter.position}")
print(f"Current inventory: {inspect_inventory()}")


"""
Step 2: Place inserter next to the chest. We need to:
- Move to the chest at position (5.5, -4.5)
- Place a burner inserter next to the chest
- Rotate the inserter to face the chest (as it needs to put items into the chest)
- Fuel the inserter with coal from the chest
"""
# Inventory at the start of step {'transport-belt': 100, 'burner-inserter': 4}
#Step Execution

# Move to the chest at position (5.5, -4.5)
chest_position = Position(x=5.5, y=-4.5)
move_to(chest_position)
print(f"Moved to chest at position {chest_position}")

# Get the chest entity
chest = get_entity(Prototype.WoodenChest, chest_position)
assert chest is not None, f"Failed to find chest at {chest_position}"
print(f"Found chest: {chest}")

# Place a burner inserter to the left of the chest
inserter_position = Position(x=chest.position.x - 1, y=chest.position.y)
inserter = place_entity(Prototype.BurnerInserter, Direction.RIGHT, inserter_position)
print(f"Placed burner inserter at {inserter_position}")

# Rotate the inserter to face the chest (it should already be facing right, but let's make sure)
inserter = rotate_entity(inserter, Direction.RIGHT)
print(f"Rotated inserter to face the chest")

# Extract coal from the chest
coal_extracted = extract_item(Prototype.Coal, chest.position, 5)
print(f"Extracted {coal_extracted} coal from the chest")

# Insert coal into the burner inserter
insert_item(Prototype.Coal, inserter, 5)
print("Inserted coal into the burner inserter")

# Final checks
inserter = get_entity(Prototype.BurnerInserter, inserter_position)
assert inserter is not None, "Failed to place or retrieve the burner inserter"
assert inserter.direction.value == Direction.RIGHT.value, "Inserter is not facing the correct direction"

print(f"Inserter setup complete. Chest at {chest.position}, Inserter at {inserter.position}")
print(f"Current inventory: {inspect_inventory()}")


"""
Step 3: Connect furnace to chest with transport belts. We need to:
- Connect the drop position of the furnace inserter to the pickup position of the chest inserter using transport belts
"""
# Placeholder 3

"""
Step 4: Verify the setup. We need to:
- Wait for 30 seconds to allow time for copper plates to be produced and transported
- Check the contents of the chest to see if it contains copper plates
##
"""
# Placeholder 4