from factorio_instance import *

"""
Main Objective: We need 20 stone bricks. The final success should be checked by looking if 20 stone bricks are in inventory
"""



"""
Step 1: Gather resources
- Mine at least 40 stone
- Mine at least 10 coal (for fueling the furnace)
OUTPUT CHECK: Check if we have at least 40 stone and 10 coal in our inventory
"""
# Inventory at the start of step {}
#Step Execution

# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 40),
    (Resource.Coal, 10)
]

# Loop through each resource and gather it
for resource, amount in resources_to_gather:
    resource_position = nearest(resource)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, amount)
    
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource, 0)
    
    assert actual_quantity >= amount, f"Failed to gather enough {resource}. Expected at least {amount}, but got {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource}")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory after gathering resources: {final_inventory}")

# Assert that we have the required amounts
assert final_inventory.get(Resource.Stone, 0) >= 40, "Not enough Stone in inventory"
assert final_inventory.get(Resource.Coal, 0) >= 10, "Not enough Coal in inventory"

print("Successfully gathered all required resources")


"""
Step 2: Fuel the furnace
- Move to the furnace at position (-12.0, -12.0)
- Add coal to the furnace
OUTPUT CHECK: Check if the furnace's fuel status is no longer 'no_fuel'
"""
# Inventory at the start of step {'coal': 10, 'stone': 40}
#Step Execution

# Step 2: Fueling the Furnace

# Get current position of stone-furnace
furnace_position = Position(x=-12.0, y=-12.0)

# Move to furnace position
move_to(furnace_position)
print(f"Moved to furnace at {furnace_position}")

# Retrieve stone-furnace entity information
stone_furnaces = get_entities({Prototype.StoneFurnace})
stone_furnace = next((f for f in stone_furnaces if f.position.is_close(furnace_position)), None)
assert stone_furnace is not None, "Stone Furnace not found at expected location."

# Check current inventory for available coal
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
print(f"Coal available in inventory: {coal_in_inventory}")

# Insert all available coal into stone-furnace as fuel
stone_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=coal_in_inventory)
print(f"Inserted {coal_in_inventory} units of coal into Stone Furnace")

# Re-inspect stone-furnace status after fueling attempt
updated_stone_furnaces = get_entities({Prototype.StoneFurnace})
updated_stone_furnace = next((f for f in updated_stone_furnaces if f.position.is_close(f.position)), None)

assert updated_stone_furnace.status != EntityStatus.NO_FUEL, "Failed to fuel Stone Furnace"

print("Successfully fueled Stone Furnace")


"""
Step 3: Smelt stone into stone bricks
- Move to the furnace if not already there
- Add stone to the furnace input
- Wait for the smelting process to complete (it takes 3.2 seconds to smelt 2 stone into 1 stone brick)
OUTPUT CHECK: Check if stone bricks are being produced
"""
# Inventory at the start of step {'stone': 40}
#Step Execution

# Move to ensure we're at or near enough to interact with the furnace
move_to(furnace_position)
print("Ensured proximity to Stone Furnace.")

# Get current inventory details
stone_in_inventory = inspect_inventory().get(Prototype.Stone, 0)
print(f"Stone available in inventory: {stone_in_inventory}")

# Insert all available stones into stone-furnace input
stone_furnace = insert_item(Prototype.Stone, stone_furnace, quantity=stone_in_inventory)
print(f"Inserted {stone_in_inventory} units of stone into Stone Furnace")

# Calculate required sleep time based on conversion rate (3.2 seconds per 2 stones -> 1 brick)
smelt_time_per_batch = 3.2
total_batches = int(stone_in_inventory / 2)  # Each batch uses up 2 stones

# Sleep while waiting for smelting process; use total batches * time per batch
sleep(total_batches * smelt_time_per_batch)

# Re-inspect updated status and contents of Stone Furnace after waiting period
updated_stone_furnaces = get_entities({Prototype.StoneFurnace})
updated_stone_furnace = next((f for f in updated_stone_furnaces if f.position.is_close(f.position)), None)

# Check if any stone bricks have been produced within its result container
produced_bricks_count = updated_stone_furnace.furnace_result.get(Prototype.StoneBrick, 0)

assert produced_bricks_count > 0, "No Stone Bricks were produced."
print(f"Successfully started producing Stone Bricks: {produced_bricks_count} currently present.")


"""
Step 4: Collect stone bricks
- Collect the produced stone bricks from the furnace
- Repeat steps 3 and 4 until we have 20 stone bricks
OUTPUT CHECK: Check if we have 20 stone bricks in our inventory

##
"""
# Inventory at the start of step {}
#Step Execution

# Step 4: Collecting Stone Bricks

# Define target number of stone bricks
target_stone_bricks = 20

# Get initial count of stone bricks in inventory
initial_brick_count = inspect_inventory().get(Prototype.StoneBrick, 0)
print(f"Initial brick count in inventory: {initial_brick_count}")

# Calculate expected total after collection
expected_total_bricks = initial_brick_count + updated_stone_furnace.furnace_result.get(Prototype.StoneBrick, 0)

# While loop to keep collecting until target is met or exceeded
while initial_brick_count < target_stone_bricks:
    # Extract all produced stone bricks from furnace
    extracted_quantity = extract_item(Prototype.StoneBrick, updated_stone_furnace.position,
                                      quantity=updated_stone_furnace.furnace_result.get(Prototype.StoneBrick))
    print(f"Extracted {extracted_quantity} units of Stone Brick")

    # Update brick count after extraction attempt
    current_inventory = inspect_inventory()
    initial_brick_count = current_inventory.get(Prototype.StoneBrick, 0)
    
    print(f"Current brick count in inventory: {initial_brick_count}")
    
    # If not enough yet, wait a bit before trying again (assuming more might be smelted)
    if initial_brick_count < target_stone_bricks:
        sleep(10)  # Wait for additional production

assert initial_brick_count >= target_stone_bricks, f"Failed to collect enough Stone Bricks. Expected at least {target_stone_bricks}, but got {initial_brick_count}"

print("Successfully collected required number of Stone Bricks.")
