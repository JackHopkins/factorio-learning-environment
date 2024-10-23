from factorio_instance import *

"""
Main Objective: We need to craft 11 stone bricks. The final success should be checked by looking if the stone bricks are in inventory
"""



"""
Step 1: Print recipe. We need to craft stone bricks. The recipe for stone bricks is:
StoneBrick - Crafting requires smelting 2 stone to make one stone brick
"""
# Inventory at the start of step {}
#Step Execution

# Get the recipe for stone bricks
stone_brick_recipe = get_prototype_recipe(Prototype.StoneBrick)

# Print the recipe details
print("Stone Brick Recipe:")
print(f"Ingredients: {stone_brick_recipe.ingredients}")
print(f"Products: {stone_brick_recipe.products}")
print(f"Energy required: {stone_brick_recipe.energy} seconds")

# Print additional information about the smelting process
print("\nAdditional Information:")
print("Stone Bricks are crafted by smelting raw stone in a furnace.")
print("Each Stone Brick requires 2 raw stone.")
print("The smelting process takes 3.2 seconds per Stone Brick.")

# Assert to ensure we got the correct recipe
assert stone_brick_recipe.name == "stone-brick", "Failed to get the correct recipe for Stone Brick"
assert len(stone_brick_recipe.ingredients) == 1, "Stone Brick recipe should have only one ingredient"
assert stone_brick_recipe.ingredients[0].name == "stone", "Stone Brick recipe should require stone as ingredient"
assert stone_brick_recipe.ingredients[0].count == 2, "Stone Brick recipe should require 2 stone per brick"

print("Successfully printed the Stone Brick recipe and additional information.")


"""
Step 2: Gather resources. We need to gather the following resources:
- 22 stone (11 stone bricks * 2 stone per brick)
- 5 stone for crafting a stone furnace
- Coal for fueling the furnace
"""
# Inventory at the start of step {}
#Step Execution

# Define the resources we need to gather
resources_needed = [
    (Resource.Stone, 27),  # 22 for bricks + 5 for furnace
    (Resource.Coal, 10)    # Estimated amount for fueling
]

# Gather each resource
for resource, amount in resources_needed:
    # Find the nearest patch of the current resource
    resource_position = nearest(resource)
    print(f"Found nearest {resource} at {resource_position}")

    # Move to the resource position
    move_to(resource_position)
    print(f"Moved to {resource} at {resource_position}")

    # Harvest the resource
    harvested = harvest_resource(resource_position, amount)
    print(f"Harvested {harvested} {resource}")

    # Verify that we harvested enough
    inventory = inspect_inventory()
    actual_amount = inventory.get(resource, 0)
    print(f"Current inventory of {resource}: {actual_amount}")
    
    assert actual_amount >= amount, f"Failed to harvest enough {resource}. Need {amount}, but only got {actual_amount}"

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory after gathering resources: {final_inventory}")

# Verify we have all the resources we need
assert final_inventory.get(Resource.Stone, 0) >= 27, "Not enough stone in inventory"
assert final_inventory.get(Resource.Coal, 0) >= 10, "Not enough coal in inventory"

print("Successfully gathered all required resources for crafting stone bricks and furnace.")


"""
Step 3: Craft and place furnace. We need to craft a stone furnace and place it for smelting:
- Craft a stone furnace using 5 stone
- Place the stone furnace on the ground
- Add coal to the furnace for fuel
"""
# Inventory at the start of step {'coal': 10, 'stone': 27}
#Step Execution

# Craft a stone furnace
print("Crafting a stone furnace...")
craft_item(Prototype.StoneFurnace, 1)

# Check if the stone furnace was crafted successfully
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace, 0) >= 1, "Failed to craft stone furnace"
print("Stone furnace crafted successfully")

# Find a suitable position to place the furnace (near coal for easy refueling)
furnace_position = nearest(Resource.Coal)
print(f"Moving to position near coal at {furnace_position}")
move_to(furnace_position)

# Place the stone furnace
print(f"Attempting to place stone furnace at {furnace_position}")
furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)
print(f"Stone furnace placed at {furnace.position}")

# Add coal to the furnace for fuel
coal_to_add = min(5, inventory[Prototype.Coal])  # Add up to 5 coal, or all available if less
print(f"Adding {coal_to_add} coal to the furnace")
insert_item(Prototype.Coal, furnace, coal_to_add)

# Wait a short time for the game to update
sleep(1)

# Print final status
print("Stone furnace crafted, placed, and fueled successfully")
print(f"Current player inventory: {inspect_inventory()}")

# Do not check the furnace inventory due to known issues with fuel inventory
print("Coal has been added to the furnace. Proceeding with the assumption that it was successful.")


"""
Step 4: Smelt stone bricks. We need to smelt the stone into bricks:
- Add 22 stone to the furnace
- Wait for the smelting process to complete (11 seconds, as it takes 1 second per stone brick)
"""
# Inventory at the start of step {'coal': 5, 'stone': 22}
#Step Execution

# Get the stone furnace
furnaces = get_entities({Prototype.StoneFurnace})
stone_furnace = furnaces[0]

# Get the amount of stone in the inventory
stone_in_inventory = inspect_inventory()[Prototype.Stone]
print(f"Stone in inventory: {stone_in_inventory}")

# Insert all available stone into the furnace
stone_furnace = insert_item(Prototype.Stone, stone_furnace, stone_in_inventory)
print(f"Inserted {stone_in_inventory} stone into the furnace")

# Verify stone insertion
furnace_contents = stone_furnace.furnace_source
inserted_stone = furnace_contents.get(Prototype.Stone, 0)
assert inserted_stone == stone_in_inventory, f"Failed to insert all stone. Inserted {inserted_stone}, expected {stone_in_inventory}"

# Calculate the smelting time
smelting_time = (stone_in_inventory / 2) * 3.2
print(f"Estimated smelting time: {smelting_time:.2f} seconds")

# Wait for smelting to complete with multiple checks
max_attempts = 5
expected_stone_bricks = stone_in_inventory // 2
initial_stone_bricks = inspect_inventory()[Prototype.StoneBrick]

for attempt in range(max_attempts):
    sleep(smelting_time / max_attempts)
    
    # Extract stone bricks
    extract_item(Prototype.StoneBrick, stone_furnace.position, expected_stone_bricks)
    
    # Check inventory for stone bricks
    current_stone_bricks = inspect_inventory()[Prototype.StoneBrick] - initial_stone_bricks
    print(f"Attempt {attempt + 1}: Stone bricks in inventory: {current_stone_bricks}")
    
    if current_stone_bricks >= expected_stone_bricks:
        break
    elif attempt == max_attempts - 1:
        print("Warning: Smelting might not be complete. Proceeding with final check.")

# Final assertion
final_stone_bricks = inspect_inventory()[Prototype.StoneBrick] - initial_stone_bricks
assert final_stone_bricks >= expected_stone_bricks, f"Expected at least {expected_stone_bricks} stone bricks, but only got {final_stone_bricks}"

print(f"Smelting process completed successfully. Smelted {final_stone_bricks} stone bricks.")


"""
Step 5: Confirm success. We need to check if the crafting was successful:
- Collect the stone bricks from the furnace
- Check the inventory to confirm we have 11 stone bricks
##
"""
# Inventory at the start of step {'stone-brick': 11, 'coal': 5}
#Step Execution

# Step 5: Confirm success

# Check the current inventory
current_inventory = inspect_inventory()
print(f"Current inventory: {current_inventory}")

# Get the number of stone bricks in the inventory
stone_bricks_count = current_inventory.get(Prototype.StoneBrick, 0)
print(f"Number of stone bricks in inventory: {stone_bricks_count}")

# Assert that we have at least 11 stone bricks
assert stone_bricks_count >= 11, f"Expected at least 11 stone bricks, but only found {stone_bricks_count}"

print("Success! We have successfully crafted at least 11 stone bricks.")

# Additional check: Verify the furnace is empty
furnaces = get_entities({Prototype.StoneFurnace})
if furnaces:
    stone_furnace = furnaces[0]
    furnace_result = stone_furnace.furnace_result
    print(f"Furnace result inventory: {furnace_result}")
    assert len(furnace_result) == 0, f"Expected empty furnace, but found items: {furnace_result}"
    print("Furnace is empty as expected.")
else:
    print("No furnace found on the map.")

print("All objectives have been successfully completed!")
