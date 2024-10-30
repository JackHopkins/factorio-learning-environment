from factorio_instance import *

"""
Main Objective: We need one stone furnace. The final success should be checked by looking if the stone furnace is in inventory
"""



"""
Step 1: Print recipe for stone furnace
"""
# Inventory at the start of step {}
#Step Execution

# Get the recipe for the stone furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)

# Print the recipe details
print("Stone Furnace Recipe:")
print(f"Ingredients: {stone_furnace_recipe.ingredients}")
print(f"Energy required: {stone_furnace_recipe.energy}")

# Log the action
print("Successfully retrieved and printed the Stone Furnace recipe.")

# Assert to ensure we got the recipe
assert stone_furnace_recipe is not None, "Failed to retrieve Stone Furnace recipe"
assert len(stone_furnace_recipe.ingredients) > 0, "Stone Furnace recipe has no ingredients"

print("Stone Furnace recipe retrieval and printing completed successfully.")


"""
Step 2: Gather resources. We need to mine stone for crafting the furnace. The substeps are:
- Locate a stone patch
- Mine at least 5 stone by hand
"""
# Inventory at the start of step {}
#Step Execution

# Step 2: Gather resources (stone)

# Locate the nearest stone patch
stone_patch_position = nearest(Resource.Stone)
print(f"Located stone patch at position: {stone_patch_position}")

# Move to the stone patch
move_to(stone_patch_position)
print(f"Moved to stone patch at position: {stone_patch_position}")

# Mine stone (aiming for 7 to ensure we have at least 5)
stone_mined = harvest_resource(stone_patch_position, quantity=7)
print(f"Mined {stone_mined} stone from the patch")

# Check the inventory to confirm we have at least 5 stone
inventory = inspect_inventory()
stone_in_inventory = inventory.get(Prototype.Stone, 0)
print(f"Current inventory: {inventory}")
print(f"Stone in inventory: {stone_in_inventory}")

# Assert to ensure we have at least 5 stone
assert stone_in_inventory >= 5, f"Failed to mine enough stone. Expected at least 5, but got {stone_in_inventory}"

print("Successfully gathered the required stone for crafting the stone furnace.")


"""
Step 3: Craft the stone furnace. We need to:
- Use the gathered stone to craft one stone furnace
- Check the inventory to confirm the presence of the stone furnace

##
"""
# Inventory at the start of step {'stone': 7}
#Step Execution

# Craft the stone furnace
print("Attempting to craft a stone furnace...")
crafted_amount = craft_item(Prototype.StoneFurnace, 1)
print(f"Crafted {crafted_amount} stone furnace(s)")

# Check the inventory to confirm the presence of the stone furnace
inventory = inspect_inventory()
stone_furnaces_in_inventory = inventory.get(Prototype.StoneFurnace, 0)
print(f"Current inventory: {inventory}")
print(f"Stone furnaces in inventory: {stone_furnaces_in_inventory}")

# Assert to ensure we have crafted the stone furnace
assert stone_furnaces_in_inventory >= 1, f"Failed to craft stone furnace. Expected at least 1, but got {stone_furnaces_in_inventory}"

# Check remaining stone in inventory
remaining_stone = inventory.get(Prototype.Stone, 0)
print(f"Remaining stone in inventory: {remaining_stone}")

# Assert to ensure we used the correct amount of stone (5 stone per furnace)
assert remaining_stone == 2, f"Unexpected amount of stone remaining. Expected 2, but got {remaining_stone}"

print("Successfully crafted the stone furnace and verified its presence in the inventory.")
