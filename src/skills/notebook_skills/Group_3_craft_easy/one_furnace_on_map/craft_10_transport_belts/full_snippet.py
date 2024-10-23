from factorio_instance import *

"""
Main Objective: We need 10 transport belts. The final success should be checked by looking if 10 transport belts are in inventory
"""



"""
Step 1: Gather resources
- Mine at least 15 iron ore
- Mine at least 10 coal (for fueling the furnace)
OUTPUT CHECK: Verify that we have at least 15 iron ore and 10 coal in our inventory
"""
# Inventory at the start of step {}
#Step Execution

# Define the resources required with their respective quantities
resources_needed = [(Resource.IronOre, 15), (Resource.Coal, 10)]

# Loop through each resource type and quantity needed
for resource_type, quantity_needed in resources_needed:
    # Find the nearest position of the current resource type
    resource_position = nearest(resource_type)
    
    # Move to the position of the found resource
    move_to(resource_position)
    
    # Harvest the specified amount of this resource type from its position
    harvested_quantity = harvest_resource(resource_position, quantity=quantity_needed)
    
    # Log how much was harvested for debugging purposes
    print(f"Harvested {harvested_quantity} of {resource_type}")
    
    # Check if we have successfully harvested enough resources by inspecting our inventory
    current_inventory = inspect_inventory()
    
    # Assert that we have at least as many as needed in our inventory; log an error message otherwise
    assert current_inventory.get(resource_type) >= quantity_needed, f"Failed to gather sufficient {resource_type}. Expected {quantity_needed}, but got {current_inventory.get(resource_type)}"
    
# Final logging statement indicating successful completion of gathering step with final inventory state
final_inventory_state = inspect_inventory()
print(f"Final Inventory after gathering resources: {final_inventory_state}")

# Assertions confirming objective achievement for both types of resources 
assert final_inventory_state.get(Resource.IronOre) >= 15, "Not enough Iron Ore collected."
assert final_inventory_state.get(Resource.Coal) >= 10, "Not enough Coal collected."

print("Successfully completed gathering step with all required resources.")


"""
Step 2: Prepare the furnace
- Move to the stone furnace at position (-12.0, -12.0)
- Fuel the furnace with coal
OUTPUT CHECK: Verify that the furnace is fueled and ready for smelting
"""
# Inventory at the start of step {'coal': 10, 'iron-ore': 15}
#Step Execution

# Move to the position of the stone furnace
furnace_position = Position(x=-12.0, y=-12.0)
move_to(furnace_position)

# Get reference to our existing stone furnace entity
stone_furnaces = get_entities({Prototype.StoneFurnace})
stone_furnace = next((f for f in stone_furnaces if f.position.is_close(furnace_position)), None)

# Check if we found our target furnace
assert stone_furnace is not None, "Stone Furnace not found at expected position."

# Log current inventory before fueling
print(f"Inventory before fueling: {inspect_inventory()}")

# Insert all available coal into the stone furnace
coal_in_inventory = inspect_inventory()[Prototype.Coal]
stone_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=coal_in_inventory)
print(f"Inserted {coal_in_inventory} coal into the Stone Furnace.")

# Wait a moment for the furnace to update its status
sleep(1)

# Re-fetch the furnace entity after inserting coal
updated_stone_furnaces = get_entities({Prototype.StoneFurnace})
updated_stone_furnace = next((f for f in updated_stone_furnaces if f.position.is_close(furnace_position)), None)

assert updated_stone_furnace is not None, "Failed to re-fetch the Stone Furnace after fueling."

# Check if coal was actually inserted into the furnace
assert updated_stone_furnace.fuel.get(Prototype.Coal, 0) > 0, "Failed to insert coal into the Stone Furnace."

# Verify that the furnace is ready for smelting (either has fuel or is in a working state)
assert updated_stone_furnace.fuel.get(Prototype.Coal, 0) > 0 or updated_stone_furnace.status in [EntityStatus.NORMAL, EntityStatus.WORKING], \
    f"Failed to prepare Stone Furnace for smelting. Current status: {updated_stone_furnace.status}, Fuel: {updated_stone_furnace.fuel}"

print("Successfully fueled Stone Furnace and it's ready for smelting.")
print(f"Final furnace state - Status: {updated_stone_furnace.status}, Fuel: {updated_stone_furnace.fuel}")


"""
Step 3: Smelt iron plates
- Smelt all the iron ore into iron plates using the fueled furnace
OUTPUT CHECK: Verify that we have at least 15 iron plates in our inventory
"""
# Inventory at the start of step {'iron-ore': 15}
#Step Execution

# Step 1: Get reference to our existing stone furnace entity
stone_furnaces = get_entities({Prototype.StoneFurnace})
furnace_position = Position(x=-12.0, y=-12.0)
stone_furnace = next((f for f in stone_furnaces if f.position.is_close(furnace_position)), None)

# Check if we found our target furnace
assert stone_furnace is not None, "Stone Furnace not found at expected position."

# Step 2: Log current inventory before inserting ingredients
print(f"Inventory before inserting ingredients: {inspect_inventory()}")

# Step 3: Insert all available iron ore into the stone furnace
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
stone_furnace = insert_item(Prototype.IronOre, stone_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} iron ore into the Stone Furnace.")

# Step 4: Wait for smelting to complete (approximately 0.7 seconds per piece of ore)
sleep(iron_ore_in_inventory * 0.7)

# Step 5: Attempt to extract all possible iron plates from the furnace multiple times until successful
max_attempts = 5
for _ in range(max_attempts):
    # Try extracting as many as were inserted; it's okay if there are fewer than requested
    extract_item(Prototype.IronPlate, stone_furnace.position, quantity=iron_ore_in_inventory)
    
    # Check how many are now present in player's inventory after extraction attempt(s)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    
    # If enough has been extracted successfully break out early otherwise wait more time between attempts 
    if current_iron_plate_count >= 15:
        break
    
    sleep(10) 

# Final check on whether objective was achieved successfully or not based upon final count post-extraction phase 
final_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
assert final_iron_plate_count >= 15, f"Failed to obtain required number of Iron Plates! Expected at least fifteen but only got {final_iron_plate_count}"

print("Successfully completed smelting step with required number of Iron Plates.")


"""
Step 4: Craft iron gear wheels
- Craft 5 iron gear wheels using 10 iron plates
OUTPUT CHECK: Verify that we have 5 iron gear wheels in our inventory
"""
# Inventory at the start of step {'iron-plate': 15}
#Step Execution

# Step 1: Check current inventory for sufficient resources
current_inventory = inspect_inventory()
iron_plates_available = current_inventory.get(Prototype.IronPlate, 0)
print(f"Current Iron Plates available: {iron_plates_available}")

# Ensure we have enough iron plates to craft the gear wheels
assert iron_plates_available >= 10, f"Not enough Iron Plates to craft Gear Wheels! Required: 10, Available: {iron_plates_available}"

# Step 2: Crafting process - Crafting five Iron Gear Wheels
craft_item(Prototype.IronGearWheel, quantity=5)
print("Crafted 5 Iron Gear Wheels.")

# Step 3: Verify crafting success by inspecting updated inventory
updated_inventory = inspect_inventory()
gear_wheels_count = updated_inventory.get(Prototype.IronGearWheel, 0)
print(f"Iron Gear Wheels after crafting: {gear_wheels_count}")

# Assert that we have successfully crafted and obtained at least five Iron Gear Wheels
assert gear_wheels_count >= 5, f"Failed to craft enough Iron Gear Wheels! Expected at least five but got {gear_wheels_count}"

print("Successfully completed crafting step with required number of Iron Gear Wheels.")


"""
Step 5: Craft transport belts
- Craft 10 transport belts using 5 iron gear wheels and 5 iron plates
OUTPUT CHECK: Verify that we have 10 transport belts in our inventory

##
"""
# Inventory at the start of step {'iron-plate': 5, 'iron-gear-wheel': 5}
#Step Execution

# Step 1: Check current inventory for sufficient resources
current_inventory = inspect_inventory()
iron_plates_available = current_inventory.get(Prototype.IronPlate, 0)
gear_wheels_available = current_inventory.get(Prototype.IronGearWheel, 0)

print(f"Current Iron Plates available: {iron_plates_available}")
print(f"Current Iron Gear Wheels available: {gear_wheels_available}")

# Ensure we have enough resources to craft the transport belts
assert iron_plates_available >= 5, f"Not enough Iron Plates to craft Transport Belts! Required: 5, Available: {iron_plates_available}"
assert gear_wheels_available >= 5, f"Not enough Iron Gear Wheels to craft Transport Belts! Required: 5, Available: {gear_wheels_available}"

# Step 2: Crafting process - Crafting ten Transport Belts
craft_item(Prototype.TransportBelt, quantity=10)
print("Crafted 10 Transport Belts.")

# Step 3: Verify crafting success by inspecting updated inventory
updated_inventory = inspect_inventory()
transport_belts_count = updated_inventory.get(Prototype.TransportBelt, 0)
print(f"Transport Belts after crafting: {transport_belts_count}")

# Assert that we have successfully crafted and obtained at least ten Transport Belts
assert transport_belts_count >= 10, f"Failed to craft enough Transport Belts! Expected at least ten but got {transport_belts_count}"

print("Successfully completed crafting step with required number of Transport Belts.")
