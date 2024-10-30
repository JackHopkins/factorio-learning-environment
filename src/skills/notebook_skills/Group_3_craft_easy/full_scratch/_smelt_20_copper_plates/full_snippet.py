from factorio_instance import *

"""
Main Objective: We need to craft 18 copper plates. The final success should be checked by looking if the copper plates are in inventory
"""



"""
Step 1: Print recipes and gather resources
- Print recipes for burner mining drill, stone furnace, and wooden chest
- Gather resources: copper ore (at least 18), coal (for fuel), stone (for furnace), and iron ore (for crafting)
"""
# Inventory at the start of step {}
#Step Execution

# Print recipes
print("Printing recipes for required entities:")
burner_drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
print(f"Burner Mining Drill recipe: {burner_drill_recipe}")

stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace recipe: {stone_furnace_recipe}")

wooden_chest_recipe = get_prototype_recipe(Prototype.WoodenChest)
print(f"Wooden Chest recipe: {wooden_chest_recipe}")

# Define required resources
resources_needed = [
    (Resource.CopperOre, 25),  # A bit extra to be safe
    (Resource.Coal, 20),
    (Resource.Stone, 10),
    (Resource.IronOre, 20)
]

print("\nGathering resources:")
for resource, amount in resources_needed:
    resource_position = nearest(resource)
    print(f"Moving to nearest {resource} at {resource_position}")
    move_to(resource_position)
    
    print(f"Harvesting {amount} {resource}")
    harvested = harvest_resource(resource_position, amount)
    print(f"Harvested {harvested} {resource}")
    
    # Verify the harvested amount
    inventory = inspect_inventory()
    actual_amount = inventory.get(resource, 0)
    print(f"Current inventory of {resource}: {actual_amount}")
    assert actual_amount >= amount, f"Failed to harvest enough {resource}. Expected at least {amount}, but got {actual_amount}"

print("\nFinal inventory after gathering resources:")
print(inspect_inventory())

print("\nResource gathering completed successfully!")


"""
Step 2: Craft necessary entities
- Craft a stone furnace
- Craft a burner mining drill
- Craft a wooden chest
"""
# Placeholder 2

"""
Step 3: Set up mining operation
- Place the burner mining drill on a copper ore patch
- Fuel the burner mining drill with coal
"""
# Placeholder 3

"""
Step 4: Set up smelting operation
- Place the stone furnace next to the burner mining drill's output
- Fuel the stone furnace with coal
- Place the wooden chest next to the stone furnace's output
"""
# Placeholder 4

"""
Step 5: Smelt copper plates and check inventory
- Wait for the mining and smelting process to complete (approximately 18 seconds for 18 plates)
- Check the wooden chest or player inventory for 18 copper plates
##
"""
# Placeholder 5