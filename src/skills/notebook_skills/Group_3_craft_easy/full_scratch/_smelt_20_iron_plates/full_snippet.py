from factorio_instance import *

"""
Main Objective: We need 12 iron plates. The final success should be checked by looking if the iron plates are in inventory
"""



"""
Step 1: Print recipes and gather initial resources. We need to craft a burner mining drill and a stone furnace. We'll also need coal for fuel.
- Print recipes for burner mining drill and stone furnace
- Gather iron ore, stone, and coal by hand
"""
# Inventory at the start of step {}
#Step Execution

# Print recipes for burner mining drill and stone furnace
burner_drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)

print("Burner Mining Drill Recipe:")
print(burner_drill_recipe)
print("\nStone Furnace Recipe:")
print(stone_furnace_recipe)

# Calculate required resources (with some extra)
iron_ore_needed = sum(ingredient.count for ingredient in burner_drill_recipe.ingredients if ingredient.name == "iron-plate") + 5
stone_needed = sum(ingredient.count for ingredient in stone_furnace_recipe.ingredients if ingredient.name == "stone") + 5
coal_needed = 10  # Extra for fuel

# Gather resources
resources_to_gather = [
    (Resource.IronOre, iron_ore_needed),
    (Resource.Stone, stone_needed),
    (Resource.Coal, coal_needed)
]

for resource, amount in resources_to_gather:
    resource_position = nearest(resource)
    print(f"Moving to {resource} at {resource_position}")
    move_to(resource_position)
    
    print(f"Harvesting {amount} {resource}")
    harvested = harvest_resource(resource_position, amount)
    print(f"Harvested {harvested} {resource}")

# Check inventory
inventory = inspect_inventory()
print("Current inventory:")
print(inventory)

# Verify we have the required resources
assert inventory.get(Resource.IronOre, 0) >= iron_ore_needed, f"Not enough iron ore. Need {iron_ore_needed}, have {inventory.get(Resource.IronOre, 0)}"
assert inventory.get(Resource.Stone, 0) >= stone_needed, f"Not enough stone. Need {stone_needed}, have {inventory.get(Resource.Stone, 0)}"
assert inventory.get(Resource.Coal, 0) >= coal_needed, f"Not enough coal. Need {coal_needed}, have {inventory.get(Resource.Coal, 0)}"

print("Successfully gathered all required resources!")


"""
Step 2: Craft and place initial equipment.
- Craft a stone furnace
- Craft a burner mining drill
- Place the burner mining drill on an iron ore patch
- Place the stone furnace adjacent to the burner mining drill's output
"""
# Placeholder 2

"""
Step 3: Set up mining and smelting operation.
- Fuel the burner mining drill with coal
- Fuel the stone furnace with coal
- Wait for the burner mining drill to mine iron ore and for the furnace to smelt it into iron plates
"""
# Placeholder 3

"""
Step 4: Collect iron plates.
- Collect the iron plates from the furnace
- Check inventory to ensure we have 12 iron plates
##
"""
# Placeholder 4