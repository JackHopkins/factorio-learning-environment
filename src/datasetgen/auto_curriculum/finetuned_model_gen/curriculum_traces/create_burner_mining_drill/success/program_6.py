
from factorio_instance import *

"""
Step 1: Gather raw resources
- Mine at least 6 iron ore
- Mine at least 5 stone
- Mine at least 5 coal
- Harvest at least 5 wood
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 6),
    (Resource.Stone, 5),
    (Resource.Coal, 5),
    (Resource.Wood, 5)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest position of this resource
    resource_position = nearest(resource_type)
    
    # Move to the location of the resource
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    
    # Check if we've harvested enough; if not, try again
    while inspect_inventory()[resource_type] < required_quantity:
        additional_needed = required_quantity - inspect_inventory()[resource_type]
        harvested += harvest_resource(resource_position, additional_needed)
        
        # Re-inspect the inventory after additional harvesting
        current_inventory = inspect_inventory()
        
        # If still not enough, print warning (although this should not happen in normal circumstances)
        if current_inventory[resource_type] < required_quantity:
            print(f"Warning: Unable to gather sufficient {resource_type}. Current: {current_inventory[resource_type]}, Required: {required_quantity}")
        
    # Final assertion to ensure we have gathered at least the required amount
    assert inspect_inventory()[resource_type] >= required_quantity, f"Failed to gather enough {resource_type}"

print("Successfully gathered all required resources:")
print(f"Iron Ore: {inspect_inventory()[Resource.IronOre]}")
print(f"Stone: {inspect_inventory()[Resource.Stone]}")
print(f"Coal: {inspect_inventory()[Resource.Coal]}")
print(f"Wood: {inspect_inventory()[Resource.Wood]}")

