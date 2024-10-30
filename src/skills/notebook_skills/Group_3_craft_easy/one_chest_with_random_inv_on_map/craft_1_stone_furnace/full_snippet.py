from factorio_instance import *

"""
Main Objective: We need one stone furnace. The final success should be checked by looking if the stone furnace is in inventory
"""



"""
Step 1: Gather stone. We need to mine 5 stone by hand.
- Move to the nearest stone patch
- Mine 5 stone by hand
"""
# Inventory at the start of step {}
#Step Execution

# Locate the nearest stone resource patch
stone_patch_position = nearest(Resource.Stone)
print(f"Nearest stone patch located at: {stone_patch_position}")

# Move to the nearest stone resource patch
move_to(stone_patch_position)
print(f"Moved to position: {stone_patch_position}")

# Harvest 6 units of stone by hand (a little more than required for safety)
stones_needed = 6
harvested_stones = harvest_resource(stone_patch_position, quantity=stones_needed)
print(f"Harvested {harvested_stones} stones")

# Verify that we've harvested at least 5 stones
current_inventory = inspect_inventory()
assert current_inventory.get(Resource.Stone, 0) >= 5, "Failed to gather enough stones!"
print("Successfully gathered sufficient amount of stones.")
print(f"Current inventory: {current_inventory}")


"""
Step 2: Craft the stone furnace. We need to use the gathered stone to craft the furnace.
- Print the recipe for the stone furnace
- Craft the stone furnace using 5 stone
"""
# Inventory at the start of step {'stone': 6}
#Step Execution

# Step 1: Print the recipe for the stone furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace Recipe: {stone_furnace_recipe}")

# Step 2: Craft the stone furnace using 5 stones
crafted_quantity = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted {crafted_quantity} Stone Furnace(s)")

# Verify that at least one stone furnace was crafted successfully
current_inventory_after_crafting = inspect_inventory()
assert current_inventory_after_crafting.get(Prototype.StoneFurnace, 0) >= 1, "Failed to craft a stone furnace!"
print("Successfully crafted a Stone Furnace.")
print(f"Current inventory after crafting: {current_inventory_after_crafting}")


"""
Step 3: Verify success. We need to check if the stone furnace is in the inventory.
- Check the inventory for the presence of a stone furnace

##
"""
# Inventory at the start of step {'stone-furnace': 1, 'stone': 1}
#Step Execution

# Step 3 Execution

# Inspect the current inventory to check for a stone furnace
current_inventory = inspect_inventory()
print(f"Current Inventory: {current_inventory}")

# Verify that there is at least one stone furnace in the inventory
stone_furnace_count = current_inventory.get(Prototype.StoneFurnace, 0)
assert stone_furnace_count >= 1, "Verification failed! Stone Furnace not found in inventory."

# If assertion passes, print success message
print("Successfully verified presence of Stone Furnace in inventory.")
