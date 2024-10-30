from factorio_instance import *

"""
Main Objective: We need create an automated coal burner mine that mines coal to a chest further away from it. First place down the drill, then the chest, then the inserter and then connect inserter with drill. The final setup should be checked by looking if the chest has any coal in it
"""



"""
Step 1: Place the burner mining drill. We need to carry out the following substeps:
- Move to the nearest coal patch
- Place the burner mining drill on the coal patch
- Fuel the burner mining drill with coal
"""
# Inventory at the start of step {'wooden-chest': 1, 'transport-belt': 100, 'burner-inserter': 5, 'burner-mining-drill': 3, 'stone-furnace': 9, 'coal': 10}
#Step Execution

# Find the nearest coal patch
coal_position = nearest(Resource.Coal)
print(f"Nearest coal patch found at: {coal_position}")

# Move to the coal patch
move_to(coal_position)
print(f"Moved to coal patch at: {coal_position}")

# Place the burner mining drill on the coal patch
drill = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=coal_position)
print(f"Placed burner mining drill at: {drill.position}")

# Fuel the burner mining drill with coal
insert_item(Prototype.Coal, drill, quantity=5)
print("Inserted coal into the burner mining drill")

# Check the drill's fuel inventory
drill_inventory = inspect_inventory(drill)
coal_in_drill = drill_inventory.get(Prototype.Coal, 0)
assert coal_in_drill > 0, f"Failed to insert coal into burner mining drill. Coal in drill: {coal_in_drill}"

# Check the drill's status
drill_info = get_entity(Prototype.BurnerMiningDrill, drill.position)
print(f"Burner mining drill status: {drill_info.status}")

# Final check to ensure everything is set up correctly
assert drill_info.status != EntityStatus.NO_FUEL, "Burner mining drill is not fueled"
print("Burner mining drill placed and fueled successfully")


"""
Step 2: Place the wooden chest. We need to carry out the following substeps:
- Move to a position further away from the drill (at least 5 tiles away)
- Place the wooden chest at this position
"""
# Inventory at the start of step {'wooden-chest': 1, 'transport-belt': 100, 'burner-inserter': 5, 'burner-mining-drill': 2, 'stone-furnace': 9, 'coal': 5}
#Step Execution

# Calculate a position 7 tiles to the right of the drill
drill_position = Position(x=19.0, y=-12.0)
chest_position = Position(x=drill_position.x + 7, y=drill_position.y)

print(f"Calculated chest position: {chest_position}")

# Move to the new position
move_to(chest_position)
print(f"Moved to position: {chest_position}")

# Place the wooden chest
chest = place_entity(Prototype.WoodenChest, direction=Direction.UP, position=chest_position)
print(f"Placed wooden chest at: {chest.position}")

# Verify the chest has been placed correctly
placed_chest = get_entity(Prototype.WoodenChest, chest_position)
assert placed_chest is not None, "Failed to place wooden chest"
print("Wooden chest placed successfully")

# Print the distance between the drill and the chest for verification
distance = ((chest_position.x - drill_position.x)**2 + (chest_position.y - drill_position.y)**2)**0.5
print(f"Distance between drill and chest: {distance} tiles")
assert distance >= 5, f"Chest is not at least 5 tiles away from the drill. Current distance: {distance}"

print("Wooden chest placed successfully at least 5 tiles away from the drill")


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
chest_position = Position(x=26.5, y=-11.5)
move_position = Position(x=chest_position.x - 1, y=chest_position.y)
move_to(move_position)
print(f"Moved to position next to the chest: {move_position}")

# Place the burner inserter adjacent to the chest (to the left)
inserter_position = Position(x=chest_position.x - 1, y=chest_position.y)
inserter = place_entity(Prototype.BurnerInserter, direction=Direction.RIGHT, position=inserter_position)
print(f"Placed burner inserter at: {inserter.position}")

# Verify the inserter has been placed correctly
placed_inserter = get_entity(Prototype.BurnerInserter, inserter_position)
assert placed_inserter is not None, "Failed to place burner inserter"
print("Burner inserter placed successfully")

# Rotate the inserter to face the chest (it should already be facing right, but let's ensure it)
inserter = rotate_entity(inserter, Direction.RIGHT)
print("Rotated inserter to face the chest")

# Check if we have coal in our inventory
player_inventory = inspect_inventory()
coal_in_inventory = player_inventory.get(Prototype.Coal, 0)
assert coal_in_inventory > 0, f"Not enough coal in inventory. Current coal: {coal_in_inventory}"

# Fuel the burner inserter with coal
insert_item(Prototype.Coal, inserter, quantity=1)
print("Attempted to insert coal into the burner inserter")

# Wait a short time for the game state to update
sleep(1)

# Check the inserter's status
inserter_info = get_entity(Prototype.BurnerInserter, inserter.position)
print(f"Burner inserter status: {inserter_info.status}")

# Final check to ensure the inserter is fueled
assert inserter_info.status != EntityStatus.NO_FUEL, "Burner inserter is not fueled"
print("Burner inserter placed, rotated, and fueled successfully")

# Print the current setup for verification
print(f"Current setup: Drill at {drill.position}, Chest at {chest_position}, Inserter at {inserter.position}")


"""
Step 4: Connect the drill to the inserter. We need to carry out the following substeps:
- Place transport belts to connect the drill's output position to the inserter's input position
- Ensure the belt is oriented correctly to move items from the drill to the inserter
"""
# Inventory at the start of step {'transport-belt': 100, 'burner-inserter': 4, 'burner-mining-drill': 2, 'stone-furnace': 9, 'coal': 4}
#Step Execution

# Get the drill and inserter positions
drill = get_entity(Prototype.BurnerMiningDrill, Position(x=19.0, y=-12.0))
inserter = get_entity(Prototype.BurnerInserter, Position(x=25.5, y=-11.5))

print(f"Drill position: {drill.position}, Drop position: {drill.drop_position}")
print(f"Inserter position: {inserter.position}, Pickup position: {inserter.pickup_position}")

# Connect the drill's output to the inserter's input using transport belts
belts = connect_entities(drill.drop_position, inserter.pickup_position, Prototype.TransportBelt)
print(f"Placed {len(belts)} transport belts")

# Verify that belts were placed
assert len(belts) > 0, "Failed to place transport belts"

# Check the orientation of the first belt
first_belt = belts[0]
last_belt = belts[-1]

print(f"First belt direction: {first_belt.direction}")
print(f"Last belt direction: {last_belt.direction}")

# Ensure the first belt is oriented away from the drill
assert first_belt.direction.value in [Direction.RIGHT.value, Direction.DOWN.value], "First belt is not oriented correctly"

# Verify that the belts form a continuous path
for i in range(len(belts) - 1):
    assert (belts[i].position.x == belts[i+1].position.x or 
            belts[i].position.y == belts[i+1].position.y), f"Gap in belt path between belt {i} and {i+1}"

# Check if the last belt's position matches the inserter's pickup position
assert last_belt.position.is_close(inserter.pickup_position), "Last belt is not at the inserter's pickup position"

print("Transport belts successfully placed and oriented to connect drill to inserter")

# Check the inserter's status after connecting
inserter_info = get_entity(Prototype.BurnerInserter, inserter.position)
print(f"Inserter status after connecting: {inserter_info.status}")

# Verify that the inserter is correctly positioned to pick up items from the belt
assert inserter.pickup_position.is_close(last_belt.position), "Inserter is not positioned correctly to pick up items from the belt"

# Final inventory check
final_inventory = inspect_inventory()
print(f"Remaining transport belts: {final_inventory.get(Prototype.TransportBelt, 0)}")

print("Connection between drill and inserter completed successfully")


"""
Step 5: Check the setup. We need to carry out the following substeps:
- Wait for 30 seconds to allow the system to operate
- Check the contents of the wooden chest to see if it contains any coal

##
"""
# Inventory at the start of step {'transport-belt': 91, 'burner-inserter': 4, 'burner-mining-drill': 2, 'stone-furnace': 9, 'coal': 4}
#Step Execution

# Initialize variables
max_wait_time = 120  # 2 minutes
check_interval = 10  # Check every 10 seconds
total_wait_time = 0

# Get references to all components
entities = get_entities()
drill = next((e for e in entities if isinstance(e, BurnerMiningDrill)), None)
inserter = next((e for e in entities if isinstance(e, BurnerInserter)), None)
chest = next((e for e in entities if isinstance(e, Chest)), None)
belts = [e for e in entities if isinstance(e, TransportBelt)]

assert drill is not None, "No burner mining drill found in the setup"
assert inserter is not None, "No burner inserter found in the setup"
assert chest is not None, "No wooden chest found in the setup"
assert len(belts) > 0, "No transport belts found in the setup"

print("Starting system check...")

while total_wait_time < max_wait_time:
    # Wait for check interval
    sleep(check_interval)
    total_wait_time += check_interval
    print(f"Time elapsed: {total_wait_time} seconds")

    # Check drill status
    print(f"Drill status: {drill.status}")
    
    # Check inserter status
    print(f"Inserter status: {inserter.status}")

    # Check belt status
    for i, belt in enumerate(belts):
        print(f"Belt {i+1} status: {belt.status}")

    # Check chest contents
    chest_inventory = inspect_inventory(chest)
    coal_in_chest = chest_inventory.get(Prototype.Coal, 0)
    print(f"Coal in wooden chest: {coal_in_chest}")

    if coal_in_chest > 0:
        print(f"Success! Found {coal_in_chest} coal in the chest after {total_wait_time} seconds.")
        break

if total_wait_time >= max_wait_time:
    print(f"Timeout reached. No coal found in chest after {max_wait_time} seconds.")
    print("Final system status:")
    print(f"Drill status: {drill.status}")
    print(f"Inserter status: {inserter.status}")
    for i, belt in enumerate(belts):
        print(f"Belt {i+1} status: {belt.status}")
    assert False, f"Expected coal in chest, but found {coal_in_chest} after {max_wait_time} seconds"

print("Setup check completed.")
print(f"The automated coal burner mine produced {coal_in_chest} coal in {total_wait_time} seconds.")
