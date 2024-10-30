from factorio_instance import *

"""
Main Objective: We need to craft 11 stone bricks. The final success should be checked by looking if the stone bricks are in inventory
"""



"""
Step 1: Print recipes. We need to print the recipe for stone furnace and stone brick:
- StoneFurnace - Crafting requires 5 stone
- StoneBrick - Crafting requires smelting 2 stone to make one stone brick
"""
# Inventory at the start of step {}
#Step Execution

# Get and print the recipe for Stone Furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace Recipe: {stone_furnace_recipe}")

# Get and print the recipe for Stone Brick
stone_brick_recipe = get_prototype_recipe(Prototype.StoneBrick)
print(f"Stone Brick Recipe: {stone_brick_recipe}")


"""
Step 2: Gather resources. We need to gather the following resources:
- 27 stone (22 for bricks, 5 for furnace)
- At least 10 coal for fuel
"""
# Inventory at the start of step {}
#Step Execution

# Define the resources needed
resources_needed = [(Resource.Stone, 35), (Resource.Coal, 15)]

# Loop through each resource type needed
for resource_type, amount_needed in resources_needed:
    # Find the nearest patch of this resource type
    resource_position = nearest(resource_type)
    
    # Move to the position of this resource patch
    move_to(resource_position)
    
    # Harvest the specified amount of this resource
    harvested_amount = harvest_resource(resource_position, amount_needed)
    
    # Log how much was harvested successfully
    print(f"Harvested {harvested_amount} units of {resource_type}.")
    
    # Check if we have gathered enough of this particular resource type
    current_inventory = inspect_inventory()
    assert current_inventory.get(resource_type, 0) >= amount_needed, f"Failed to gather enough {resource_type}. Expected {amount_needed}, but got {current_inventory.get(resource_type, 0)}"
    
print("Successfully gathered all required resources.")
print(f"Final inventory: {inspect_inventory()}")


"""
Step 3: Craft stone furnace. We need to craft a stone furnace using 5 stone.
"""
# Inventory at the start of step {'coal': 15, 'stone': 35}
#Step Execution

# Craft a stone furnace using available stones
crafted_count = craft_item(Prototype.StoneFurnace, 1)
print(f"Attempted to craft 1 Stone Furnace.")

# Inspect inventory to verify that the stone furnace has been crafted
inventory_after_crafting = inspect_inventory()
stone_furnaces_in_inventory = inventory_after_crafting.get(Prototype.StoneFurnace, 0)

assert stone_furnaces_in_inventory >= 1, f"Failed to craft Stone Furnace. Expected at least 1 but got {stone_furnaces_in_inventory}"
print("Successfully crafted a Stone Furnace.")


"""
Step 4: Set up smelting area. We need to do the following:
- Place the stone furnace
- Fuel the furnace with coal
"""
# Inventory at the start of step {'stone-furnace': 1, 'coal': 15, 'stone': 30}
#Step Execution

# Inspect entities around us to find a good spot for placing
inspection_results = inspect_entities()
print(f"Entities around us: {inspection_results.entities}")

# Choose a position next to an existing entity like Chest
chest_position = inspection_results.get_entity(Prototype.WoodenChest).position

# Calculate new position slightly offset from chest for placement
furnace_position = Position(x=chest_position.x + 1, y=chest_position.y)

# Move close enough to place the furnace (assuming we're not already there)
move_to(furnace_position)
print(f"Moved near desired position {furnace_position} for placing Stone Furnace.")

# Place the Stone Furnace at calculated position
placed_furnace = place_entity(Prototype.StoneFurnace, Direction.UP, furnace_position)
print(f"Placed Stone Furnace at {placed_furnace.position}")

# Fueling process: Insert coal into newly placed stone furnace
coal_amount_for_fuel = 10  # Use part of available coal for initial fueling

insert_item(Prototype.Coal, placed_furnace, coal_amount_for_fuel)
print(f"Inserted {coal_amount_for_fuel} units of Coal into Stone Furnace")

# Log final state after setup
final_inventory_after_setup = inspect_inventory()
print(f"Final inventory after setting up smelting area: {final_inventory_after_setup}")


"""
Step 5: Smelt stone bricks. We need to smelt 22 stone into 11 stone bricks:
- Put 22 stone into the furnace
- Wait for the smelting to complete
"""
# Inventory at the start of step {'coal': 5, 'stone': 30}
#Step Execution

# Get the most up-to-date reference to the stone furnace
furnaces = get_entities({Prototype.StoneFurnace})
assert len(furnaces) > 0, "No Stone Furnace found on the map!"
stone_furnace = furnaces[0]

# Move close to the furnace
move_to(stone_furnace.position)

# Check if we have enough stone in the inventory
current_inventory = inspect_inventory()
stones_to_insert = min(22, current_inventory.get(Prototype.Stone, 0))
assert stones_to_insert > 0, "Not enough stone in inventory to start smelting!"

# Insert stone into the furnace
stone_furnace = insert_item(Prototype.Stone, stone_furnace, stones_to_insert)
print(f"Inserted {stones_to_insert} units of Stone into Stone Furnace")

# Calculate expected number of stone bricks after smelting completes
initial_stone_bricks = current_inventory.get(Prototype.StoneBrick, 0)
expected_stone_bricks = initial_stone_bricks + (stones_to_insert // 2)

# Wait for smelting process to complete
smelting_time_per_unit = 3.2  # Smelting time for stone brick is 3.2 seconds
total_smelting_time = smelting_time_per_unit * (stones_to_insert // 2)
sleep(total_smelting_time)

print("Smelting period over; proceeding with extraction...")

# Extract stone bricks from the furnace
max_attempts = 5
for attempt in range(max_attempts):
    extract_item(Prototype.StoneBrick, stone_furnace.position, stones_to_insert // 2)
    current_inventory = inspect_inventory()
    current_stone_bricks = current_inventory.get(Prototype.StoneBrick, 0)
    
    print(f"Attempt {attempt + 1}: Current count of Stone Bricks after extraction: {current_stone_bricks}")
    
    if current_stone_bricks >= expected_stone_bricks:
        break
    
    if attempt < max_attempts - 1:
        sleep(10)  # Wait before next attempt

assert current_stone_bricks >= expected_stone_bricks, f"Failed to produce sufficient Stone Bricks! Expected at least {expected_stone_bricks}, but got {current_stone_bricks}"

print(f"Successfully completed smelting step. Obtained {current_stone_bricks} Stone Bricks.")


"""
Step 6: Collect stone bricks. We need to collect the 11 stone bricks from the furnace and put them in our inventory.
"""
# Inventory at the start of step {'stone-brick': 11, 'coal': 5, 'stone': 8}
#Step Execution

# Step 6: Collect stone bricks. We need to collect the 11 stone bricks from the furnace and put them in our inventory.

# Check the current inventory
current_inventory = inspect_inventory()
print(f"Current inventory: {current_inventory}")

# Get the number of stone bricks in the inventory
stone_bricks_in_inventory = current_inventory.get(Prototype.StoneBrick, 0)

# Assert that we have the expected number of stone bricks
expected_stone_bricks = 11
assert stone_bricks_in_inventory >= expected_stone_bricks, f"Expected at least {expected_stone_bricks} stone bricks, but found {stone_bricks_in_inventory}"

print(f"Successfully verified {stone_bricks_in_inventory} Stone Bricks in inventory.")

# If we want to be extra sure, we can check the furnace contents
furnaces = get_entities({Prototype.StoneFurnace})
assert len(furnaces) > 0, "No Stone Furnace found on the map!"
stone_furnace = furnaces[0]

print(f"Stone Furnace contents: {stone_furnace.furnace_result}")

# Assert that the furnace is empty of stone bricks
assert stone_furnace.furnace_result.get(Prototype.StoneBrick, 0) == 0, "Unexpected stone bricks found in the furnace"

print("Verified that all stone bricks have been collected from the furnace.")


"""
Step 7: Verify success. Check if 11 stone bricks are in the inventory.
##
"""
# Inventory at the start of step {'stone-brick': 11, 'coal': 5, 'stone': 8}
#Step Execution

# Verify success: Check if 11 stone bricks are in the inventory

# Get current state of the player's inventory
current_inventory = inspect_inventory()
print(f"Current Inventory: {current_inventory}")

# Retrieve number of stone bricks from inventory
stone_bricks_count = current_inventory.get(Prototype.StoneBrick, 0)
print(f"Stone Bricks in Inventory: {stone_bricks_count}")

# Define expected amount of stone bricks
expected_stone_bricks = 11

# Verify that we have at least as many stone bricks as needed
assert stone_bricks_count >= expected_stone_bricks, f"Verification failed! Expected at least {expected_stone_bricks} Stone Bricks but found {stone_bricks_count}"

print("Successfully verified the presence of required Stone Bricks.")
