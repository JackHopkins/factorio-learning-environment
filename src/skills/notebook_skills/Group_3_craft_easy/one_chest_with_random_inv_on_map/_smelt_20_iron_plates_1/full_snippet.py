from factorio_instance import *

"""
Main Objective: We need 12 iron plates. The final success should be checked by looking if the iron plates are in inventory
"""



"""
Step 1: Print recipes. We need to craft a stone furnace, burner mining drill, and burner inserter. Print out the recipes for these items:
- Stone Furnace
- Burner Mining Drill
- Burner Inserter
"""
# Inventory at the start of step {}
#Step Execution

# Get and print the recipe for Stone Furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace Recipe: {stone_furnace_recipe}")

# Get and print the recipe for Burner Mining Drill
burner_mining_drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
print(f"Burner Mining Drill Recipe: {burner_mining_drill_recipe}")

# Get and print the recipe for Burner Inserter
burner_inserter_recipe = get_prototype_recipe(Prototype.BurnerInserter)
print(f"Burner Inserter Recipe: {burner_inserter_recipe}")


"""
Step 2: Gather resources. We need to gather the following resources by hand:
- Stone for the furnace
- Iron ore for crafting and smelting
- Coal for fuel
"""
# Inventory at the start of step {}
#Step Execution

# Define required resources with some margin
resources_to_gather = [
    (Prototype.Stone, 12),     # Need extra for potential inefficiencies
    (Prototype.IronOre, 20),   # Extra ores to ensure enough plates after smelting losses
    (Prototype.Coal, 10)       # Initial batch of coal for fueling
]

# Loop through each resource type and gather the specified amount
for resource_type, quantity in resources_to_gather:
    print(f"Gathering {quantity} units of {resource_type}")
    
    # Find nearest patch of the current resource type
    resource_position = nearest(resource_type)
    
    # Move close enough to harvest it
    move_to(resource_position)

    # Harvest the desired quantity from this position or nearby within radius
    harvested_amount = harvest_resource(resource_position, quantity)
    
    print(f"Harvested {harvested_amount} units of {resource_type}")

    # Check inventory after each resource gathering
    current_inventory = inspect_inventory()
    assert current_inventory[resource_type] >= quantity, f"Failed to gather enough {resource_type}. Expected at least {quantity}, but got {current_inventory[resource_type]}"

# Check inventory state after gathering all resources
final_inventory = inspect_inventory()
print(f"Final Inventory after gathering resources: {final_inventory}")

print("Successfully gathered all required resources.")


"""
Step 3: Craft necessary items. Craft the following items:
- Stone Furnace
- Burner Mining Drill
- Burner Inserter
"""
# Placeholder 3

"""
Step 4: Set up mining and smelting. We need to set up the mining and smelting process:
- Place the Burner Mining Drill on an iron ore patch
- Place the Stone Furnace next to the drill's output
- Place the Burner Inserter between the drill and the furnace
- Rotate the Burner Inserter to face the furnace
- Add coal to the Burner Mining Drill, Burner Inserter, and Stone Furnace
"""
# Placeholder 4

"""
Step 5: Start mining and smelting. Allow the setup to run until we have at least 12 iron plates in the furnace output.
"""
# Placeholder 5

"""
Step 6: Collect iron plates. Move to the furnace and collect the 12 iron plates into the inventory.
"""
# Placeholder 6

"""
Step 7: Verify success. Check the inventory to ensure we have 12 iron plates.

##
"""
# Placeholder 7