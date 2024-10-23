from factorio_instance import *

"""
Main Objective: We require one BurnerMiningDrill. The final success should be checked by looking if a BurnerMiningDrill is in inventory
"""



"""
Step 1: Print recipes. We need to craft a BurnerMiningDrill. Print out the recipe for it.
"""
# Inventory at the start of step {}
#Step Execution

# Fetching the recipe for BurnerMiningDrill
burner_mining_drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)

# Printing out each ingredient required in the recipe
print("Recipe for Burner Mining Drill:")
for ingredient in burner_mining_drill_recipe.ingredients:
    print(f"- {ingredient.name}: {ingredient.count}")

# Since we're only printing, no assert statements are necessary here.


"""
Step 2: Gather resources. We need to gather the following resources:
- 18 iron ore (9 for plates, 9 for gear wheels)
- Enough coal to fuel the furnace (at least 10)
OUTPUT CHECK: Verify that we have at least 18 iron ore and 10 coal in our inventory.
"""
# Inventory at the start of step {}
#Step Execution

# Define the resources needed
resources_needed = [(Resource.IronOre, 18), (Resource.Coal, 10)]

# Loop through each resource type and gather them
for resource_type, required_amount in resources_needed:
    # Find the nearest position of the current resource type
    resource_position = nearest(resource_type)
    
    # Move to the found position
    move_to(resource_position)
    
    # Harvest the required amount of this resource
    harvested_amount = harvest_resource(resource_position, quantity=required_amount)
    
    # Check if we have harvested enough of this particular resource
    current_inventory_count = inspect_inventory().get(resource_type, 0)
    
    assert current_inventory_count >= required_amount, f"Failed to gather enough {resource_type}. Expected {required_amount}, but got {current_inventory_count}"
    
    print(f"Successfully gathered {current_inventory_count} of {resource_type}")

# Final check on inventory after gathering all resources
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.IronOre, 0) >= 18, "Not enough Iron Ore collected."
assert final_inventory.get(Prototype.Coal, 0) >= 10, "Not enough Coal collected."

print("Final inventory after gathering resources:", final_inventory)
print("Successfully completed gathering resources.")


"""
Step 3: Prepare the furnace. We need to prepare the existing furnace for smelting:
- Move to the furnace at position (-12.0, -12.0)
- Add coal to the furnace as fuel
OUTPUT CHECK: Verify that the furnace's energy is above 0, indicating it has fuel.
"""
# Placeholder 3

"""
Step 4: Smelt iron plates. We need to smelt 9 iron ore into 9 iron plates:
- Add 9 iron ore to the furnace
- Wait for the smelting process to complete
OUTPUT CHECK: Verify that we have 9 iron plates in our inventory.
"""
# Placeholder 4

"""
Step 5: Craft iron gear wheels. We need to craft 3 iron gear wheels:
- Craft 3 iron gear wheels using 6 iron plates
OUTPUT CHECK: Verify that we have 3 iron gear wheels in our inventory.
"""
# Placeholder 5

"""
Step 6: Craft BurnerMiningDrill. We now have all the components to craft the BurnerMiningDrill:
- Craft 1 BurnerMiningDrill using 3 iron gear wheels, 3 iron plates, and the stone furnace on the map
OUTPUT CHECK: Verify that we have 1 BurnerMiningDrill in our inventory.

##
"""
# Placeholder 6