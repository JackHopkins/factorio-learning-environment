Sure! The objective requires us to create a fast-underground-belt.
To craft a fast-underground-belt, we need 2 underground-belts and 20 iron gear wheels. 
Each underground-belt requires 10 iron gear wheels and 1 iron plate, so in total we'll need 22 iron plates and 20 iron gear wheels for the fast-underground-belt.
We'll also need a stone furnace for smelting the iron plates.
Since there are no entities on the map and the inventory is empty, we'll need to gather all the resources and craft the necessary items from scratch.

Here's a detailed plan to achieve the objective of creating a fast-underground-belt:

1. Print out the recipe for fast-underground-belt
2. Calculate the total resources needed
3. Gather raw resources
4. Craft intermediate products
5. Craft the final product: fast-underground-belt
6. Verify the crafting process

After the plan, create a policy that carries out the plan. Make sure to check if the final objective was achieved successfully 

"""
from factorio_instance import *

"""
Objective: Create a fast-underground-belt from scratch

Planning:
- There are no entities on the map and the inventory is empty
- We need to craft a fast-underground-belt
- We need to gather all resources and craft intermediate products

Steps:
1. Print out the recipe for fast-underground-belt
2. Calculate the total resources needed
3. Gather raw resources
4. Craft intermediate products
5. Craft the final product: fast-underground-belt
6. Verify the crafting process
"""

"""
Step 1: Print out the recipe for fast-underground-belt
"""
# Get the recipe for fast-underground-belt
recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)

# Print out the recipe details
print("fast-underground-belt Recipe:")
print(f"Ingredients: {recipe.ingredients}")
print("")

"""
Step 2: Calculate the total resources needed
"""
# Calculate total iron plates needed
iron_gear_wheels = 40  # 20 for each underground-belt
iron_plates_for_gears = iron_gear_wheels * 2  # Each iron gear wheel requires 2 iron plates
iron_plates_for_belts = 2  # Each underground-belt requires 1 iron plate
total_iron_plates = iron_plates_for_gears + iron_plates_for_belts

# Calculate total iron ore needed (1 iron ore = 1 iron plate)
total_iron_ore = total_iron_plates

# Calculate total coal needed (1 coal can smelt approximately 1.6 items)
coal_for_smelting = int(total_iron_plates / 1.6) + 1

# We need 5 stone for crafting a stone furnace
stone_for_furnace = 5

# Print out the calculated resources
print("Calculated Resources Needed:")
print(f"Total Iron Ore: {total_iron_ore}")
print(f"Total Coal: {coal_for_smelting}")
print(f"Total Stone: {stone_for_furnace}")
print("")

"""
Step 3: Gather raw resources
"""
print("Gathering raw resources...")

# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, total_iron_ore),
    (Resource.Coal, coal_for_smelting),
    (Resource.Stone, stone_for_furnace)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    
    # Move to the resource position
    print(f"Moving to {resource_type} at {resource_position}")
    move_to(resource_position)
    
    # Harvest the required quantity of this resource
    print(f"Harvesting {required_quantity} of {resource_type}")
    harvested = harvest_resource(resource_position, required_quantity)
    
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} of {resource_type}\n")

print("Finished gathering raw resources.\n")

"""
Step 4: Craft intermediate products
"""
print("Crafting intermediate products...")

# Craft a stone furnace
print("Crafting a stone furnace...")
stone_furnaces_crafted = craft_item(Prototype.StoneFurnace, 1)
assert stone_furnaces_crafted == 1, "Failed to craft a stone furnace"
print("Successfully crafted a stone furnace\n")

# Place the stone furnace
current_position = inspect_entities().player_position
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=current_position[0]+2, y=current_position[1]))
print(f"Placed stone furnace at: {furnace.position}")

# Insert coal into the furnace as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=coal_for_smelting)
print("Inserted coal into the stone furnace")

# Smelt iron plates
print("Smelting iron plates...")
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
sleep(10)  # Wait for some smelting to occur

# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= total_iron_plates:
        break
    sleep(5)

print(f"Extracted {current_iron_plate_count} iron plates from the furnace")
assert current_iron_plate_count >= total_iron_plates, f"Failed to obtain required number of iron plates. Expected: {total_iron_plates}, Found: {current_iron_plate_count}"

# Craft iron gear wheels
print("Crafting iron gear wheels...")
iron_gear_wheels_crafted = craft_item(Prototype.IronGearWheel, iron_gear_wheels)
assert iron_gear_wheels_crafted == iron_gear_wheels, f"Failed to craft iron gear wheels. Expected: {iron_gear_wheels}, Found: {iron_gear_wheels_crafted}"
print(f"Successfully crafted {iron_gear_wheels_crafted} iron gear wheels\n")

"""
Step 5: Craft the final product: fast-underground-belt
"""
print("Crafting fast-underground-belt...")

fast_underground_belts_crafted = craft_item(Prototype.FastUndergroundBelt, 1)
assert fast_underground_belts_crafted == 1, "Failed to craft a fast-underground-belt"
print("Successfully crafted a fast-underground-belt\n")

"""
Step 6: Verify the crafting process
"""
print("Verifying the crafting process...")

final_inventory = inspect_inventory()
fast_underground_belt_count = final_inventory.get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belt_count >= 1, f"Failed to verify the presence of fast-underground-belts. Expected at least 1, Found: {fast_underground_belt_count}"

print(f"Final Inventory:")
print(f"Fast Underground Belts: {fast_underground_belt_count}")
print("Successfully verified the presence of the crafted fast-underground-belt!")
print("Objective completed successfully!")
"""
This policy creates a fast-underground-belt from scratch by following a thorough plan. 
It takes into account the recipe for fast-underground-belt, calculates the required resources, gathers raw resources, crafts intermediate products, and finally crafts the fast-underground-belt.
The policy includes recipe printing, resource calculation, raw resource gathering, intermediate product crafting, final product crafting, and verification steps.
"""
