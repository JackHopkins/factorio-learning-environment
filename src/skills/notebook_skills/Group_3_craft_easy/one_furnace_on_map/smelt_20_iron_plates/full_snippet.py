from factorio_instance import *

"""
Main Objective: We need 20 iron plates. The final success should be checked by looking if the iron plates are in inventory
"""



"""
Step 1: Gather resources
- Move to the nearest iron ore patch and mine at least 20 iron ore
- Move to the nearest coal patch and mine at least 10 coal (for fueling the furnace)
OUTPUT CHECK: Verify that we have at least 20 iron ore and 10 coal in our inventory
"""
# Inventory at the start of step{}
#Step Execution

# Define required quantities
required_iron_ore = 20
required_coal = 10

# Step 1: Gather Iron Ore
print("Gathering Iron Ore...")
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
harvest_resource(iron_ore_position, required_iron_ore)

# Check if we have enough iron ore
current_inventory = inspect_inventory()
assert current_inventory[Resource.IronOre] >= required_iron_ore, f"Failed to mine enough Iron Ore. Expected {required_iron_ore}, but got {current_inventory[Resource.IronOre]}"
print(f"Mined {current_inventory[Resource.IronOre]} Iron Ore")

# Step 2: Gather Coal
print("Gathering Coal...")
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, required_coal)

# Check if we have enough coal
current_inventory = inspect_inventory()
assert current_inventory[Resource.Coal] >= required_coal, f"Failed to mine enough Coal. Expected {required_coal}, but got {current_inventory[Resource.Coal]}"
print(f"Mined {current_inventory[Resource.Coal]} Coal")

final_inventory = inspect_inventory()
print(f"Final Inventory after gathering resources: {final_inventory}")

# Final check for overall success of this step
assert final_inventory[Resource.IronOre] >= required_iron_ore, "Not enough Iron Ore gathered."
assert final_inventory[Resource.Coal] >= required_coal, "Not enough Coal gathered."
print("Successfully gathered all necessary resources.")


"""
Step 2: Prepare the furnace
- Move to the existing stone furnace at position (-12.0, -12.0)
- Add coal to the furnace as fuel
OUTPUT CHECK: Verify that the furnace status changes from NO_FUEL to IDLE
"""
# Inventory at the start of step{'coal': 10, 'iron-ore': 20}
#Step Execution

# Step 2: Prepare the Furnace

# Get current state of entities around us
inspection_results = inspect_entities()
stone_furnace_info = inspection_results.get_entity(Prototype.StoneFurnace)

# Ensure we have found a stone furnace
assert stone_furnace_info is not None, "Stone Furnace not found!"

# Move near to the stone furnace at (-12.0, -12.0)
furnace_position = Position(x=-12.0, y=-12.0)
move_to(furnace_position)

# Check current inventory for available coal
coal_in_inventory = inspect_inventory()[Prototype.Coal]
print(f"Coal available in inventory: {coal_in_inventory}")

# Insert coal into the stone furnace for fueling
stone_furnace = get_entity(Prototype.StoneFurnace, Position(x=-12.0, y=-12.0))
stone_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=coal_in_inventory)
print("Inserted coal into Stone Furnace.")

# Re-inspect entities after inserting coal to check status change
updated_inspection_results = inspect_entities()
updated_stone_furnace_info = updated_inspection_results.get_entity(Prototype.StoneFurnace)

# Assert if status has changed from NO_FUEL to IDLE or WORKING (as smelting might start immediately)
assert updated_stone_furnace_info.status != EntityStatus.NO_FUEL, f"Failed! Furnace still shows 'No Fuel'. Current Status: {updated_stone_furnace_info.status}"
print("Successfully fueled Stone Furnace and verified its status.")


"""
Step 3: Smelt iron plates
- Add iron ore to the furnace
- Wait for the smelting process to complete (it takes 3.2 seconds to smelt one iron plate)
OUTPUT CHECK: Check the furnace periodically to see if iron plates are being produced
"""
# Inventory at the start of step{'iron-ore': 20}
#Step Execution

# Step 3: Smelt Iron Plates

# Get reference to the existing stone furnace
stone_furnace = get_entity(Prototype.StoneFurnace, Position(x=-12.0, y=-12.0))

# Check how much iron ore is available in inventory
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
print(f"Iron Ore available in inventory: {iron_ore_in_inventory}")

# Insert all available iron ore into the stone furnace
stone_furnace = insert_item(Prototype.IronOre, stone_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} Iron Ore into Stone Furnace.")

# Calculate total time needed for smelting based on number of ores inserted (3.2 seconds per ore)
smelting_time_per_ore = 3.2
total_smelting_time = smelting_time_per_ore * iron_ore_in_inventory

# Wait for initial smelting process to start
sleep(total_smelting_time)

# Check periodically if iron plates are being produced in the furnace
max_attempts = 5
for attempt in range(max_attempts):
    # Try to extract iron plates
    extract_item(Prototype.IronPlate, stone_furnace.position, iron_ore_in_inventory)
    
    # Check how many iron plates we have in our inventory
    iron_plates_in_inventory = inspect_inventory()[Prototype.IronPlate]
    
    print(f"Attempt {attempt + 1}: Found {iron_plates_in_inventory} Iron Plates in inventory.")
    
    # If we have extracted all expected iron plates, break out of the loop
    if iron_plates_in_inventory >= iron_ore_in_inventory:
        break
    
    sleep(10)  # Wait a bit more before checking again

# Final check to ensure we have produced the expected number of iron plates
assert iron_plates_in_inventory >= iron_ore_in_inventory, f"Failed to produce enough Iron Plates. Expected at least {iron_ore_in_inventory}, but got {iron_plates_in_inventory}"

print(f"Iron plate production completed successfully. Produced {iron_plates_in_inventory} Iron Plates.")


"""
Step 4: Collect iron plates
- Collect the iron plates from the furnace
- Repeat steps 3 and 4 until we have at least 20 iron plates in our inventory
OUTPUT CHECK: Verify that we have at least 20 iron plates in our inventory

##
"""
# Inventory at the start of step{'iron-plate': 20}
#Step Execution

# Step 4: Collect Iron Plates

# Check how many iron plates are currently in our inventory
current_iron_plates = inspect_inventory()[Prototype.IronPlate]
print(f"Current Iron Plates in Inventory: {current_iron_plates}")

# Assert to verify we have met the requirement of having at least 20 iron plates
assert current_iron_plates >= 20, f"Failed! Expected at least 20 Iron Plates, but found {current_iron_plates}"

print("Successfully collected enough Iron Plates.")
