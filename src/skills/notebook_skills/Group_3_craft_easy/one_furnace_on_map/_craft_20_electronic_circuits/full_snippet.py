from factorio_instance import *

"""
Main Objective: We need 20 electronic circuits. The final success should be checked by looking if 10 electronic circuits are in inventory
"""



"""
Step 1: Gather initial resources
- Mine stone to craft a burner mining drill and additional furnaces
- Mine coal for fuel
- Mine iron ore and copper ore manually
OUTPUT CHECK: Ensure we have at least 20 stone, 50 coal, 50 iron ore, and 50 copper ore in the inventory
"""
# Inventory at the start of step {}
#Step Execution

from factorio_instance import *

# Define the resources needed with their respective amounts
resources_needed = {
    Resource.Stone: 20,
    Resource.Coal: 50,
    Resource.IronOre: 50,
    Resource.CopperOre: 50
}

# Iterate over each resource type and quantity needed
for resource, required_amount in resources_needed.items():
    # Get the nearest position of the current resource
    print(f"Finding nearest {resource[0]}...")
    resource_position = nearest(resource)
    
    # Move to the location of the resource
    print(f"Moving to {resource[0]} at position {resource_position}...")
    move_to(resource_position)
    
    # Harvesting more than needed for buffer (10% extra)
    harvest_amount = int(required_amount * 1.1)
    
    # Harvesting resources from identified position
    print(f"Harvesting {harvest_amount} units of {resource[0]}...")
    harvested_quantity = harvest_resource(resource_position, quantity=harvest_amount)
    
    # Check if we have enough resources after harvesting
    current_inventory = inspect_inventory()
    
    actual_quantity = current_inventory.get(resource[0], 0)
    
    assert actual_quantity >= required_amount,\
        f"Failed to gather enough {resource[0]}. Expected at least {required_amount}, but got {actual_quantity}"
        
    print(f"Successfully gathered sufficient {resource[0]}: Inventory has {actual_quantity}")

print("All necessary initial resources successfully gathered.")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
for resource, amount in resources_needed.items():
    actual_amount = final_inventory.get(resource[0], 0)
    print(f"{resource[0]}: {actual_amount}/{amount}")
    assert actual_amount >= amount, f"Not enough {resource[0]} in final inventory. Expected at least {amount}, but got {actual_amount}"

print("All resource gathering objectives met successfully.")


"""
Step 2: Craft and place initial tools
- Craft a burner mining drill
- Craft two additional stone furnaces
- Place the burner mining drill on a coal patch
- Place the two new furnaces next to the existing one
OUTPUT CHECK: Confirm the burner mining drill is placed and working, and three furnaces are available
"""
# Placeholder 2

"""
Step 3: Set up smelting operation
- Fuel all three furnaces with coal
- Use two furnaces for iron plates and one for copper plates
- Manually feed iron ore and copper ore into respective furnaces
OUTPUT CHECK: Ensure all furnaces are working and producing plates
"""
# Placeholder 3

"""
Step 4: Craft burner inserters and chests
- Craft three burner inserters
- Craft three wooden chests
- Place inserters and chests next to each furnace to collect smelted plates
OUTPUT CHECK: Confirm inserters are moving plates from furnaces to chests
"""
# Placeholder 4

"""
Step 5: Automate coal mining
- Craft another burner inserter and wooden chest
- Place them to automate coal collection from the mining drill
OUTPUT CHECK: Verify that coal is being automatically mined and stored
"""
# Placeholder 5

"""
Step 6: Craft copper cables
- Take copper plates from the chest
- Craft copper cables (2 cables per 1 copper plate)
OUTPUT CHECK: Ensure we have at least 60 copper cables (for 20 electronic circuits)
"""
# Placeholder 6

"""
Step 7: Craft electronic circuits
- Take iron plates from the chests
- Craft electronic circuits using 3 copper cables and 1 iron plate each
- Craft until we have 20 electronic circuits
OUTPUT CHECK: Verify that we have 20 electronic circuits in the inventory

##
"""
# Placeholder 7