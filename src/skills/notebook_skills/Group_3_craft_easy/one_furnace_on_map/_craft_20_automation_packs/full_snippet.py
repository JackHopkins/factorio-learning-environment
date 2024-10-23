from factorio_instance import *

"""
Main Objective: We need 20 automation science packs. The final success should be checked by looking if 20 automation science packs are in inventory
"""



"""
Step 1: Gather initial resources
- Mine coal for fuel
- Mine stone for crafting additional furnaces
- Mine iron ore and copper ore
OUTPUT CHECK: Ensure we have at least 50 of each resource in the inventory
"""
# Inventory at the start of step {}
#Step Execution

# Define the resources required and their respective quantities to mine slightly more than needed
resources_required = [(Resource.Coal, 55), (Resource.Stone, 55), (Resource.IronOre, 55), (Resource.CopperOre, 55)]

# Loop through each resource type and perform mining operations
for resource_type, quantity_needed in resources_required:
    # Find the nearest position of the current resource type
    print(f"Finding nearest {resource_type}...")
    resource_position = nearest(resource_type)
    
    # Move towards the identified position of the resource patch
    print(f"Moving to {resource_type} at position {resource_position}")
    move_to(resource_position)
    
    # Harvesting specified quantity from identified position/resource patch
    print(f"Harvesting {quantity_needed} units of {resource_type}")
    harvest_resource(resource_position, quantity=quantity_needed)

# Verify if we have gathered enough resources by checking our inventory after mining all resources 
current_inventory = inspect_inventory()
print(f"Current Inventory after gathering resources: {current_inventory}")

# Assert checks ensuring minimum required amount is available post-harvesting operation per specified requirement 
assert current_inventory[Resource.Coal] >= 50, f"Insufficient Coal! Expected at least 50 but found only {current_inventory[Resource.Coal]}"
assert current_inventory[Resource.Stone] >= 50, f"Insufficient Stone! Expected at least 50 but found only {current_inventory[Resource.Stone]}"
assert current_inventory[Resource.IronOre] >= 50, f"Inadequate Iron Ore! Anticipated minimum count being 50 however discovered merely {current_inventory[Resource.IronOre]}"
assert current_inventory[Resource.CopperOre] >= 50, f"Lackluster Copper Ore collection! Presumed baseline threshold was set around 50 yet encountered just about {current_inventory[Resource.CopperOre]}"

print("Successfully gathered initial resources with sufficient quantities!")


"""
Step 2: Craft basic tools
- Craft 2 stone furnaces (one for iron, one for copper)
- Craft 2 burner mining drills
- Craft 2 burner inserters
OUTPUT CHECK: Verify that we have 2 stone furnaces, 2 burner mining drills, and 2 burner inserters in the inventory
"""
# Placeholder 2

"""
Step 3: Set up automated mining and smelting
- Place burner mining drills on iron and copper patches
- Place stone furnaces near the mining drills
- Place burner inserters between the mining drills and furnaces
- Fuel all entities (mining drills, inserters, and furnaces) with coal
OUTPUT CHECK: Wait for 30 seconds and verify that iron plates and copper plates are being produced
"""
# Placeholder 3

"""
Step 4: Craft iron gear wheels
- Craft 20 iron gear wheels using 40 iron plates
OUTPUT CHECK: Verify that we have 20 iron gear wheels in the inventory
"""
# Placeholder 4

"""
Step 5: Craft automation science packs
- Craft 20 automation science packs using 20 copper plates and 20 iron gear wheels
OUTPUT CHECK: Verify that we have 20 automation science packs in the inventory

##
"""
# Placeholder 5