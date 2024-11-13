

from factorio_instance import *

"""
Step 1: Print recipes. We need to create a fast-underground-belt from scratch
"""
# Print the recipe for fast-underground-belt
print("To craft fast-underground-belt, we need 20 iron gear wheels and 2 underground belts")

"""
Step 2: Gather resources. We need to mine coal, stone, and iron ore
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.Coal, 7),
    (Resource.Stone, 6),
    (Resource.IronOre, 98)
]

# Loop through each resource and gather it
for resource, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource)
    print(f"Found {resource} at position {resource_position}")
    
    # Move to the resource
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    print(f"Harvested {harvested} of {resource}")
    
    # Check if we got enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} of {resource}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")

# Assert that we have gathered at least the required quantities
assert final_inventory.get(Resource.Coal, 0) >= 7, f"Insufficient Coal. Expected at least 7 but got {final_inventory.get(Resource.Coal, 0)}"
assert final_inventory.get(Resource.Stone, 0) >= 6, f"Insufficient Stone. Expected at least 6 but got {final_inventory.get(Resource.Stone, 0)}"
assert final_inventory.get(Resource.IronOre, 0) >= 98, f"Insufficient Iron Ore. Expected at least 98 but got {final_inventory.get(Resource.IronOre, 0)}"

print("Successfully gathered all required resources!")

