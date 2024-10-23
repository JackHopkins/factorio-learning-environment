from factorio_instance import *

"""
Main Objective: We need three stone furnaces. The final success should be checked by looking if 3 stone furnaces are in inventory
"""



"""
Step 1: Print recipe for Stone Furnace
"""
# Inventory at the start of step {}
#Step Execution

# Retrieve and print the recipe for a Stone Furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace Recipe: {stone_furnace_recipe}")

# Ensure that we've successfully printed out correct information about stone furnace requirements
assert 'ingredients' in stone_furnace_recipe.__dict__, "Failed to retrieve ingredients for Stone Furnace"
print("Successfully printed the recipe for Stone Furnace.")


"""
Step 2: Gather resources from the chest. We need to carry out the following substeps:
- Move to the chest at position (-11.5, -11.5)
- Take all stone and coal from the chest
"""
# Inventory at the start of step {}
#Step Execution

# Step 2 implementation

# Move to the chest location at (-11.5, -11.5)
chest_position = Position(x=-11.5, y=-11.5)
print(f"Moving towards the chest at {chest_position}")
move_to(chest_position)

# Get the wooden chest entity
target_chest = get_entity(Prototype.WoodenChest, chest_position)
assert target_chest is not None, "No wooden chest found at the specified position"

print(f"Found a wooden chest at {target_chest.position}")

# Extract all stone from the wooden chest
stone_in_chest = target_chest.inventory.get(Prototype.Stone, 0)
if stone_in_chest > 0:
    extract_item(Prototype.Stone, target_chest.position, quantity=stone_in_chest)
    print(f"Extracted {stone_in_chest} stones from the chest")
else:
    print("No stones found in the chest")

# Extract all coal from the wooden chest
coal_in_chest = target_chest.inventory.get(Prototype.Coal, 0)
if coal_in_chest > 0:
    extract_item(Prototype.Coal, target_chest.position, quantity=coal_in_chest)
    print(f"Extracted {coal_in_chest} coals from the chest")
else:
    print("No coals found in the chest")

# Verify extraction by checking updated inventory state
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.Stone, 0) >= stone_in_chest, f"Failed to retrieve expected amount of stone; got {current_inventory.get(Prototype.Stone, 0)} instead of {stone_in_chest}"
assert current_inventory.get(Prototype.Coal, 0) >= coal_in_chest, f"Failed to retrieve expected amount of coal; got {current_inventory.get(Prototype.Coal, 0)} instead of {coal_in_chest}"

print(f"Current Inventory after extraction: {current_inventory}")


"""
Step 3: Mine additional stone. We need to carry out the following substeps:
- Find the nearest stone patch
- Mine at least 12 more stone by hand
"""
# Inventory at the start of step {'coal': 6, 'stone': 3}
#Step Execution

# Find the nearest stone patch
stone_patch_position = nearest(Resource.Stone)
print(f"Nearest stone patch located at {stone_patch_position}")

# Move to the stone patch
print(f"Moving towards the stone patch at {stone_patch_position}")
move_to(stone_patch_position)

# Current amount of stone in inventory
current_stone_in_inventory = inspect_inventory().get(Prototype.Stone, 0)
required_stone_to_mine = max(15 - current_stone_in_inventory, 0) # Ensure we calculate how much more is needed

if required_stone_to_mine > 0:
    # Mine additional stones needed
    harvested_stones = harvest_resource(stone_patch_position, quantity=required_stone_to_mine)
    print(f"Harvested {harvested_stones} stones from the resource patch")

# Verify that we've reached or exceeded our target number of stones in inventory
final_stone_count = inspect_inventory().get(Prototype.Stone, 0)
assert final_stone_count >= 15, f"Failed to gather enough stones; expected at least 15 but got {final_stone_count}"

print("Successfully mined additional stones.")


"""
Step 4: Craft the stone furnaces. We need to carry out the following substeps:
- Open the crafting menu
- Craft 3 stone furnaces using 15 stone
"""
# Inventory at the start of step {'coal': 6, 'stone': 15}
#Step Execution

# Check if we have enough stone in our inventory
current_inventory = inspect_inventory()
stone_count = current_inventory.get(Prototype.Stone, 0)
assert stone_count >= 15, f"Insufficient stone to craft three furnaces; needed 15 but only have {stone_count}"

print(f"Stone count before crafting: {stone_count}")

# Craft three stone furnaces
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=3)
print(f"Crafted {crafted_furnaces} Stone Furnaces")

# Check if we've successfully crafted three Stone Furnaces by inspecting the inventory again
inventory_after_crafting = inspect_inventory()
furnace_count = inventory_after_crafting.get(Prototype.StoneFurnace, 0)

assert furnace_count >= 3, f"Failed to craft enough Stone Furnaces; expected at least 3 but got {furnace_count}"
print("Successfully crafted three Stone Furnaces.")


"""
Step 5: Verify success. Check the inventory to ensure we have 3 stone furnaces.
##
"""
# Inventory at the start of step {'stone-furnace': 3, 'coal': 6}
#Step Execution

# Step 5: Verify success by checking if we have 3 stone furnaces in our inventory

# Inspect the current inventory
current_inventory = inspect_inventory()
print(f"Current Inventory for verification: {current_inventory}")

# Get the count of stone furnaces in the inventory
stone_furnace_count = current_inventory.get(Prototype.StoneFurnace, 0)
print(f"Stone Furnace count in inventory: {stone_furnace_count}")

# Assert to ensure we have crafted at least 3 Stone Furnaces
assert stone_furnace_count >= 3, f"Verification failed: Expected at least 3 Stone Furnaces but found {stone_furnace_count}"

print("Successfully verified that there are at least 3 Stone Furnaces in the inventory.")
