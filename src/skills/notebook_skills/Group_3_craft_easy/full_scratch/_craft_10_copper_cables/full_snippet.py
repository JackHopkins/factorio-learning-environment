from factorio_instance import *

"""
Main Objective: We need to craft 10 copper cables. The final success should be checked by looking if the copper cables are in inventory
"""



"""
Step 1: Print recipes. We need to craft copper cables, a burner mining drill, and a stone furnace. Print out the recipes for these items:
- CopperCable: Crafting 2 copper cables requires 1 copper plate
- BurnerMiningDrill: Crafting requires 3 iron gear wheels, 3 iron plates, 1 stone furnace. In total all ingredients require atleast 9 iron plates and 5 stone
- StoneFurnace: Crafting requires 5 stone
"""
# Inventory at the start of step {}
#Step Execution

# Get and print the recipe for Copper Cable
copper_cable_recipe = get_prototype_recipe(Prototype.CopperCable)
print("Copper Cable Recipe:")
print(f"Ingredients: {copper_cable_recipe.ingredients}")
print(f"Products: {copper_cable_recipe.products}")
print()

# Get and print the recipe for Burner Mining Drill
burner_drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
print("Burner Mining Drill Recipe:")
print(f"Ingredients: {burner_drill_recipe.ingredients}")

# Calculate total iron plates needed for Burner Mining Drill
total_iron_plates = 0
for ingredient in burner_drill_recipe.ingredients:
    if ingredient.name == "iron-plate":
        total_iron_plates += ingredient.count
    elif ingredient.name == "iron-gear-wheel":
        # Each iron gear wheel requires 2 iron plates
        total_iron_plates += ingredient.count * 2

print(f"Total iron plates required: {total_iron_plates}")
print(f"Stone required: 5 (1 for stone furnace, 4 additional)")
print()

# Get and print the recipe for Stone Furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print("Stone Furnace Recipe:")
print(f"Ingredients: {stone_furnace_recipe.ingredients}")
print()

# Print a summary of all recipes
print("Summary of Recipes:")
print("1. Copper Cable: 1 copper plate -> 2 copper cables")
print(f"2. Burner Mining Drill: {total_iron_plates} iron plates, 5 stone")
print("3. Stone Furnace: 5 stone")

# Assert to ensure we got all the recipes
assert copper_cable_recipe is not None, "Failed to get Copper Cable recipe"
assert burner_drill_recipe is not None, "Failed to get Burner Mining Drill recipe"
assert stone_furnace_recipe is not None, "Failed to get Stone Furnace recipe"

print("Successfully printed all required recipes.")


"""
Step 2: Gather resources. We need to gather the following resources by hand:
- Stone for the stone furnace and burner mining drill
- Iron ore for the burner mining drill
- Copper ore for the copper cables
- Coal for fuel
"""
# Inventory at the start of step {}
#Step Execution

# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 15),  # A bit extra stone
    (Resource.IronOre, 20),  # Extra iron ore
    (Resource.CopperOre, 12),  # Extra copper ore
    (Resource.Coal, 25)  # Extra coal for fuel
]

# Gather each resource
for resource, amount in resources_to_gather:
    resource_position = nearest(resource)
    print(f"Moving to nearest {resource} patch at {resource_position}")
    move_to(resource_position)
    
    print(f"Harvesting {amount} {resource}")
    harvested = harvest_resource(resource_position, amount)
    
    # Check if we harvested enough
    inventory = inspect_inventory()
    actual_amount = inventory.get(resource, 0)
    print(f"Harvested {actual_amount} {resource}")
    
    assert actual_amount >= amount, f"Failed to harvest enough {resource}. Got {actual_amount}, needed {amount}"

# Print final inventory
final_inventory = inspect_inventory()
print("Final inventory after gathering resources:")
print(final_inventory)

# Assert that we have all the resources we need
assert final_inventory.get(Resource.Stone, 0) >= 10, "Not enough stone gathered"
assert final_inventory.get(Resource.IronOre, 0) >= 14, "Not enough iron ore gathered"
assert final_inventory.get(Resource.CopperOre, 0) >= 8, "Not enough copper ore gathered"
assert final_inventory.get(Resource.Coal, 0) >= 20, "Not enough coal gathered"

print("Successfully gathered all required resources!")


"""
Step 3: Craft and set up mining. We need to craft the necessary items and set up a basic mining operation:
- Craft a stone furnace
- Smelt iron ore into iron plates
- Craft iron gear wheels
- Craft a burner mining drill
- Place the burner mining drill on a copper ore patch and fuel it with coal
"""
# Placeholder 3

"""
Step 4: Smelt copper plates. We need to smelt copper ore into copper plates:
- Place the stone furnace near the burner mining drill
- Fuel the stone furnace with coal
- Manually move copper ore from the mining drill to the furnace
- Collect the smelted copper plates
"""
# Placeholder 4

"""
Step 5: Craft copper cables. We need to craft the copper cables and verify success:
- Craft 10 copper cables using the copper plates
- Check the inventory to confirm that 10 copper cables have been crafted
##
"""
# Placeholder 5