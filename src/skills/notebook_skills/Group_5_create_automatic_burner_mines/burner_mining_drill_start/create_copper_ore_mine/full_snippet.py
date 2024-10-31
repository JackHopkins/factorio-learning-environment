from factorio_instance import *

"""
Main Objective: We need create an automated copper burner mine that mines copper ore to a chest further away from it. First place down the drill, then the chest, then the inserter and then connect inserter with drill. The final setup should be checked by looking if the chest has any copper ore in it
"""



"""
Step 1: Place the burner mining drill. We need to carry out the following substeps:
- Move to a copper ore patch
- Place the burner mining drill on the copper ore patch
- Add coal to fuel the burner mining drill
"""
# Inventory at the start of step {'wooden-chest': 1, 'transport-belt': 100, 'burner-inserter': 5, 'burner-mining-drill': 3, 'stone-furnace': 9, 'coal': 10}
#Step Execution

# Find the nearest copper ore patch
copper_ore_position = nearest(Resource.CopperOre)
print(f"Nearest copper ore found at: {copper_ore_position}")

# Move to the copper ore patch
move_to(copper_ore_position)
print(f"Moved to copper ore patch at: {copper_ore_position}")

# Place the burner mining drill on the copper ore patch
drill = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=copper_ore_position)
print(f"Placed burner mining drill at: {drill.position}")

# Add coal to fuel the burner mining drill
coal_inserted = insert_item(Prototype.Coal, drill, quantity=5)
print(f"Inserted {coal_inserted} coal into the burner mining drill")

# Verify that the drill is placed and fueled
entities_around = get_entities({Prototype.BurnerMiningDrill}, position=copper_ore_position, radius=1)
assert len(entities_around) > 0, "Failed to place burner mining drill"
print("Burner mining drill successfully placed and fueled")

# Print the current inventory
current_inventory = inspect_inventory()
print(f"Current inventory after placing and fueling the drill: {current_inventory}")


"""
Step 2: Place the wooden chest. We need to carry out the following substeps:
- Move to a position further away from the drill (at least 5 tiles away)
- Place the wooden chest at this position
"""
# Inventory at the start of step {'wooden-chest': 1, 'transport-belt': 100, 'burner-inserter': 5, 'burner-mining-drill': 2, 'stone-furnace': 9, 'coal': 5}
#Step Execution

# Calculate a position 7 tiles to the right of the drill
drill_position = Position(x=19.0, y=19.0)
chest_position = Position(x=drill_position.x + 7, y=drill_position.y)

# Move to the calculated position
print(f"Moving to position: {chest_position}")
move_to(chest_position)

# Place the wooden chest
chest = place_entity(Prototype.WoodenChest, direction=Direction.UP, position=chest_position)
print(f"Placed wooden chest at: {chest.position}")

# Verify that the chest has been placed correctly
entities_around = get_entities({Prototype.WoodenChest}, position=chest_position, radius=1)
if len(entities_around) > 0:
    print("Wooden chest successfully placed")
else:
    print("Failed to place wooden chest")

# Print the current inventory
current_inventory = inspect_inventory()
print(f"Current inventory after placing the wooden chest: {current_inventory}")


"""
Step 3: Set up the burner inserter. We need to carry out the following substeps:
- Move next to the wooden chest
- Place the burner inserter adjacent to the chest
- Rotate the inserter so it will insert items into the chest
- Add coal to fuel the burner inserter
"""
# Inventory at the start of step {'transport-belt': 100, 'burner-inserter': 5, 'burner-mining-drill': 2, 'stone-furnace': 9, 'coal': 5}
#Step Execution

# Move next to the wooden chest
chest_position = Position(x=26.5, y=19.5)
inserter_position = Position(x=chest_position.x - 1, y=chest_position.y)
print(f"Moving to position next to the chest: {inserter_position}")
move_to(inserter_position)

# Place the burner inserter adjacent to the chest
inserter = place_entity(Prototype.BurnerInserter, direction=Direction.RIGHT, position=inserter_position)
print(f"Placed burner inserter at: {inserter.position}")

# Rotate the inserter so it will insert items into the chest (it's already facing right, so no need to rotate)
print("Inserter is already facing the right direction to insert into the chest")

# Add coal to fuel the burner inserter
coal_inserted = insert_item(Prototype.Coal, inserter, quantity=1)
print(f"Inserted {coal_inserted} coal into the burner inserter")

# Verify that the inserter has been placed and fueled correctly
entities_around = get_entities({Prototype.BurnerInserter}, position=inserter_position, radius=1)
if len(entities_around) > 0:
    print("Burner inserter successfully placed")
    inserter_entity = entities_around[0]
    if inserter_entity.direction.value == Direction.RIGHT.value:
        print("Burner inserter is correctly oriented towards the chest")
    else:
        print("Warning: Burner inserter is not correctly oriented towards the chest")
else:
    print("Failed to place burner inserter")

# Print the current inventory
current_inventory = inspect_inventory()
print(f"Current inventory after setting up the burner inserter: {current_inventory}")


"""
Step 4: Connect the drill to the inserter. We need to carry out the following substeps:
- Use transport belts to connect the drop position of the burner mining drill to the pickup position of the burner inserter
- Ensure the belt is properly aligned and connected
"""
# Inventory at the start of step {'transport-belt': 100, 'burner-inserter': 4, 'burner-mining-drill': 2, 'stone-furnace': 9, 'coal': 4}
#Step Execution

# Get the positions of the drill and inserter
drill = [entity for entity in get_entities({Prototype.BurnerMiningDrill}) if isinstance(entity, BurnerMiningDrill)][0]
inserter = [entity for entity in get_entities({Prototype.BurnerInserter}) if isinstance(entity, BurnerInserter)][0]

print(f"Drill position: {drill.position}, Drop position: {drill.drop_position}")
print(f"Inserter position: {inserter.position}, Pickup position: {inserter.pickup_position}")

# Move to a position near the drill to start placing belts
move_to(Position(x=drill.position.x, y=drill.position.y + 2))

# Connect the drill's drop position to the inserter's pickup position with transport belts
print("Connecting drill to inserter with transport belts...")
belts = connect_entities(drill.drop_position, inserter.pickup_position, Prototype.TransportBelt)

# Verify that the belts have been placed
if belts:
    print(f"Successfully placed {len(belts)} transport belts to connect drill to inserter")
    for i, belt in enumerate(belts):
        print(f"Belt {i+1} position: {belt.position}")
else:
    print("Failed to place transport belts")

# Check if the connection is complete
start_pos = drill.drop_position
end_pos = inserter.pickup_position
connected_entities = get_entities({Prototype.TransportBelt}, position=start_pos, radius=20)

if connected_entities:
    print("Transport belt connection verified:")
    for entity in connected_entities:
        print(f"Transport belt at position: {entity.position}")
    
    # Check if the last belt is close to the inserter's pickup position
    last_belt = connected_entities[-1]
    if last_belt.position.is_close(end_pos):
        print("Connection successful: Last belt is close to inserter's pickup position")
    else:
        print("Warning: Last belt may not be properly connected to inserter")
else:
    print("Error: No transport belts found connecting drill to inserter")

# Print current inventory after placing belts
current_inventory = inspect_inventory()
print(f"Current inventory after connecting drill to inserter: {current_inventory}")


"""
Step 5: Verify the setup. We need to carry out the following substeps:
- Wait for 30 seconds to allow the system to operate
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

# Locate the wooden chest
chest_entities = [entity for entity in get_entities({Prototype.WoodenChest}) if isinstance(entity, Chest)]
if not chest_entities:
    print("Error: Wooden chest not found in the setup.")
    assert False, "Wooden chest is missing from the setup."

chest = chest_entities[0]
print(f"Wooden chest found at position: {chest.position}")

# Move near the chest to inspect its contents
move_to(chest.position)

# Check the contents of the wooden chest for copper ore
chest_inventory = chest.inventory
copper_ore_count = chest_inventory.get(Prototype.CopperOre, 0)

print(f"Copper ore in the wooden chest: {copper_ore_count}")

# Verify if the setup is working correctly
if copper_ore_count > 0:
    print("Success: The automated copper burner mine setup is working correctly!")
    print(f"Found {copper_ore_count} copper ore in the wooden chest.")
else:
    print("Warning: No copper ore found in the wooden chest.")
    print("The setup might not be working as expected. Here are some potential issues to check:")
    print("1. Ensure the burner mining drill has enough fuel (coal).")
    print("2. Verify that the transport belts are correctly connected from the drill to the inserter.")
    print("3. Check if the burner inserter has enough fuel and is oriented correctly.")
    print("4. Make sure there are no obstructions in the system.")

# Additional check: Inspect the burner mining drill
drill_entities = [entity for entity in get_entities({Prototype.BurnerMiningDrill}) if isinstance(entity, BurnerMiningDrill)]
if drill_entities:
    drill = drill_entities[0]
    print(f"\nBurner Mining Drill status: {drill.status}")
    print(f"Drill fuel: {drill.fuel}")
else:
    print("\nWarning: Burner Mining Drill not found in the setup.")

# Additional check: Inspect the burner inserter
inserter_entities = [entity for entity in get_entities({Prototype.BurnerInserter}) if isinstance(entity, BurnerInserter)]
if inserter_entities:
    inserter = inserter_entities[0]
    print(f"\nBurner Inserter status: {inserter.status}")
    print(f"Inserter fuel: {inserter.fuel}")
else:
    print("\nWarning: Burner Inserter not found in the setup.")

print("\nSetup verification complete.")
