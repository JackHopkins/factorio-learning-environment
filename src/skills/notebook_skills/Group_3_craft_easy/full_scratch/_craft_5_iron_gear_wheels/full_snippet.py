from factorio_instance import *

"""
Main Objective: We need to craft 5 iron gear wheels. The final success should be checked by looking if the gear wheels are in inventory
"""



"""
Step 1: Print recipes and gather resources. We need to print the recipes for burner mining drill, stone furnace, and iron gear wheel. Then gather the necessary resources:
- Print recipes for burner mining drill, stone furnace, and iron gear wheel
- Gather stone for the furnace
- Gather coal for fuel
- Gather iron ore for smelting
"""
# Inventory at the start of step {}
#Step Execution

# Print recipes for required items
print("Printing recipes for required items:")
burner_drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
print(f"Burner Mining Drill recipe: {burner_drill_recipe}")

stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace recipe: {stone_furnace_recipe}")

iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(f"Iron Gear Wheel recipe: {iron_gear_wheel_recipe}")

# Calculate required resources
stone_needed = stone_furnace_recipe.ingredients[0].count
coal_needed = 10  # Extra coal for fuel
iron_ore_needed = 20  # Extra iron ore for smelting

print(f"\nRequired resources:")
print(f"Stone: {stone_needed}")
print(f"Coal: {coal_needed}")
print(f"Iron Ore: {iron_ore_needed}")

# Gather resources
resources_to_gather = [
    (Resource.Stone, stone_needed),
    (Resource.Coal, coal_needed),
    (Resource.IronOre, iron_ore_needed)
]

for resource, amount in resources_to_gather:
    print(f"\nGathering {resource}:")
    resource_position = nearest(resource)
    print(f"Moving to {resource} at position {resource_position}")
    move_to(resource_position)
    
    print(f"Harvesting {amount} {resource}")
    harvested = harvest_resource(resource_position, amount)
    print(f"Harvested {harvested} {resource}")

    # Check if we have enough resources
    inventory = inspect_inventory()
    actual_amount = inventory.get(resource, 0)
    print(f"Current inventory of {resource}: {actual_amount}")
    assert actual_amount >= amount, f"Failed to gather enough {resource}. Expected at least {amount}, but got {actual_amount}"

print("\nFinal inventory after gathering resources:")
print(inspect_inventory())

print("\nSuccessfully gathered all required resources!")


"""
Step 2: Craft and set up basic mining and smelting. We need to create a simple setup to mine and smelt iron:
- Craft a stone furnace and place it down
- Craft a burner mining drill and place it on an iron ore patch
- Fuel both the furnace and the mining drill with coal
"""
# Placeholder 2

"""
Step 3: Smelt iron plates. We need to smelt enough iron plates for 5 iron gear wheels:
- Wait for the burner mining drill to mine iron ore
- Move iron ore to the furnace
- Wait for the furnace to smelt iron plates
- Collect the iron plates
"""
# Placeholder 3

"""
Step 4: Craft iron gear wheels. We need to craft 5 iron gear wheels:
- Use the collected iron plates to craft 5 iron gear wheels
- Check the inventory to ensure 5 iron gear wheels have been crafted
"""
# Placeholder 4

"""
Step 5: Verify success. We need to confirm that the 5 iron gear wheels are in the inventory:
- Check the inventory for the presence of 5 iron gear wheels
##
"""
# Placeholder 5