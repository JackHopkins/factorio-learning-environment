from factorio_instance import *

"""
Main Objective: We require one GunTurret. The final success should be checked by looking if a GunTurret is in inventory
"""



"""
Step 1: Mine resources
- Mine 50 coal (for fueling the furnace)
- Mine 50 iron ore
- Mine 20 copper ore
OUTPUT CHECK: Verify that we have at least 50 coal, 50 iron ore, and 20 copper ore in the inventory
"""
# Inventory at the start of step {}
#Step Execution

# Define resources and their required amounts
resources_needed = [
    (Resource.Coal, Prototype.Coal, 50),
    (Resource.IronOre, Prototype.IronOre, 50),
    (Resource.CopperOre, Prototype.CopperOre, 20)
]

# Loop through each resource type and mine them
for resource, prototype, required_amount in resources_needed:
    # Find nearest position of current resource type
    print(f"Finding nearest {resource}...")
    position = nearest(resource)
    
    # Move to that position
    print(f"Moving to {resource} at position {position}...")
    move_to(position)
    
    # Harvest the necessary amount of this resource
    print(f"Harvesting {required_amount} units of {resource}...")
    harvested = harvest_resource(position=position, quantity=required_amount)
    assert harvested >= required_amount, f"Failed to harvest enough {resource}. Expected {required_amount}, but got {harvested}"

# Verify if we have mined enough resources by checking inventory
inventory_after_mining = inspect_inventory()
print("Inventory after mining:", inventory_after_mining)

# Assert checks for verifying correct amounts are present in inventory
for _, prototype, required_amount in resources_needed:
    actual_amount = inventory_after_mining.get(prototype, 0)
    assert actual_amount >= required_amount, f"Expected at least {required_amount} {prototype} but found {actual_amount}"

print("Successfully mined all required resources.")


"""
Step 2: Smelt iron and copper plates
- Move to the existing furnace at position (-12.0, -12.0)
- Add coal to the furnace
- Smelt 30 iron plates (requires 30 iron ore)
- Smelt 10 copper plates (requires 10 copper ore)
OUTPUT CHECK: Verify that we have at least 30 iron plates and 10 copper plates in the inventory
"""
# Placeholder 2

"""
Step 3: Craft iron gear wheels
- Craft 10 iron gear wheels (requires 20 iron plates)
OUTPUT CHECK: Verify that we have 10 iron gear wheels in the inventory
"""
# Placeholder 3

"""
Step 4: Craft GunTurret
- Craft 1 GunTurret (requires 10 copper plates, 10 iron gear wheels, and 20 iron plates)
OUTPUT CHECK: Verify that we have 1 GunTurret in the inventory
##
"""
# Placeholder 4