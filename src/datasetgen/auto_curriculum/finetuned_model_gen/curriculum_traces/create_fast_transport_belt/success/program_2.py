
from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipe for stone-furnace as we need to craft it
"""
# Print recipe for stone-furnace
print("Recipe for stone-furnace:")
print("Crafting requires 5 stone")

"""
Step 2: Gather raw resources
- Mine 6 stone for crafting a stone furnace
- Mine 3 iron ore for smelting into iron plates
- Mine 1 coal for fueling the furnace
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 6),
    (Resource.IronOre, 3),
    (Resource.Coal, 1)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    
    # Move to the resource position
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    
    # Check if we harvested enough of this resource
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.Stone, 0) >= 6, "Not enough Stone"
assert final_inventory.get(Resource.IronOre, 0) >= 3, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 1, "Not enough Coal"

print("Successfully gathered all required resources")

