
from instance import *


"""
Step 1: Print recipes. We need to print the recipes for the final item we need to craft
We need to craft a fast-underground-belt from scratch. There are no entities on the map or in our inventory.
To craft a fast-underground-belt, we need 2 iron gear wheels and 1 underground belt.
The underground belt itself requires 10 iron gear wheels and 1 transport belt.
We'll need to gather resources, smelt iron plates, and craft the necessary components.
We also need to create a temporary mining and smelting setup to produce the required iron plates and gear wheels.
"""
"""
Step 1: Print recipes
"""
# Get the recipes for the items we need to craft
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)

# Print the recipes
print("Recipes:")
print(f"Fast Underground Belt: {fast_underground_belt_recipe}")
print(f"Underground Belt: {underground_belt_recipe}")
print(f"Iron Gear Wheel: {iron_gear_wheel_recipe}")

"""
Step 1: Gather resources
- Mine at least 25 iron ore
- Mine at least 12 stone (for 2 stone furnaces)
- Mine at least 2 coal (for fuel)
"""
"""
Step 1: Gather resources
- Mine at least 25 iron ore
- Mine at least 12 stone (for 2 stone furnaces)
- Mine at least 2 coal (for fuel)
"""

# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 25),
    (Resource.Stone, 12),
    (Resource.Coal, 2)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    
    # Move to the resource
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, quantity=required_quantity)
    
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final verification
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 25, "Not enough Iron Ore"
assert final_inventory.get(Resource.Stone, 0) >= 12, "Not enough Stone"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Not enough Coal"

print("Successfully gathered all required resources.")

"""
Step 2: Craft stone furnaces
- Craft 2 stone furnaces (each requires 5 stone)
"""
"""
Step 2: Craft stone furnaces
- Craft 2 stone furnaces (each requires 5 stone)
"""

# Check initial inventory for stone
initial_inventory = inspect_inventory()
stone_count = initial_inventory.get(Resource.Stone, 0)
assert stone_count >= 10, f"Not enough stone to craft 2 furnaces. Current stone count: {stone_count}"

# Craft 2 stone furnaces
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=2)
assert crafted_furnaces == 2, f"Failed to craft 2 stone furnaces. Only crafted {crafted_furnaces}"

# Verify that 2 furnaces were crafted
final_inventory = inspect_inventory()
furnace_count = final_inventory.get(Prototype.StoneFurnace, 0)
assert furnace_count >= 2, f"Inventory check failed: Expected at least 2 stone furnaces, found {furnace_count}"

print(f"Successfully crafted 2 stone furnaces; current inventory count: {furnace_count}")
