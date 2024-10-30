from factorio_instance import *

"""
Main Objective: We need to craft 4 small electric poles. The final success should be checked by looking if the small electric poles are in inventory
"""



"""
Step 1: Print recipes. We need to print the recipes for the following items:
- Small Electric Pole
- Copper Cable
- Copper Plate
- Stone Furnace
"""
# Inventory at the start of step {}
#Step Execution

# Get and print the recipe for Small Electric Pole
small_electric_pole_recipe = get_prototype_recipe(Prototype.SmallElectricPole)
print(f"Small Electric Pole Recipe: {small_electric_pole_recipe}")

# Get and print the recipe for Copper Cable
copper_cable_recipe = get_prototype_recipe(Prototype.CopperCable)
print(f"Copper Cable Recipe: {copper_cable_recipe}")

# Get and print the recipe for Copper Plate
copper_plate_recipe = get_prototype_recipe(Prototype.CopperPlate)
print(f"Copper Plate Recipe: {copper_plate_recipe}")

# Get and print the recipe for Stone Furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace Recipe: {stone_furnace_recipe}")


"""
Step 2: Gather resources. We need to gather the following resources:
- Mine copper ore (at least 2 copper ore)
- Mine coal for fuel (at least 2 coal)
- Mine stone for furnace (5 stone)
- Deconstruct the wooden chest on the map to obtain wood (2 wood)
"""
# Placeholder 2

"""
Step 3: Craft and place a stone furnace. We need to:
- Craft a stone furnace using 5 stone
- Place the stone furnace down
- Fuel the furnace with coal
"""
# Placeholder 3

"""
Step 4: Smelt copper plates. We need to:
- Put copper ore into the furnace
- Wait for the copper ore to smelt into copper plates (we need at least 2 copper plates)
"""
# Placeholder 4

"""
Step 5: Craft copper cables. We need to:
- Craft 4 copper cables using 2 copper plates
"""
# Placeholder 5

"""
Step 6: Craft small electric poles. We need to:
- Craft 4 small electric poles using 4 copper cables and 2 wood
"""
# Placeholder 6

"""
Step 7: Verify success. Check the inventory to ensure we have 4 small electric poles.
##
"""
# Placeholder 7