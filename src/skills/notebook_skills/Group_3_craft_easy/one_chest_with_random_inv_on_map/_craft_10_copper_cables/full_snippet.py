from factorio_instance import *

"""
Main Objective: We need to craft 10 copper cables. The final success should be checked by looking if the copper cables are in inventory
"""



"""
Step 1: Print recipes. We need to craft stone furnace and copper cables. Print out their recipes.
"""
# Inventory at the start of step {}
#Step Execution

# Get and print the recipe for a stone furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace Recipe: {stone_furnace_recipe}")

# Get and print the recipe for copper cables
copper_cable_recipe = get_prototype_recipe(Prototype.CopperCable)
print(f"Copper Cable Recipe: {copper_cable_recipe}")


"""
Step 2: Gather resources from the chest. We need to carry out the following substeps:
- Move to the chest at position (-11.5, -11.5)
- Take all the coal and stone from the chest
"""
# Inventory at the start of step {}
#Step Execution

# Step 1: Move to the chest's position
chest_position = Position(x=-11.5, y=-11.5)
move_to(chest_position)
print(f"Moved to chest at {chest_position}")

# Step 2: Get the chest entity
chests = get_entities({Prototype.WoodenChest})
assert len(chests) > 0, "No wooden chests found on the map."
wooden_chest = chests[0]

# Step 3: Extract all coal from the chest
coal_in_chest = wooden_chest.inventory.get('coal', 0)
extract_item(Prototype.Coal, wooden_chest.position, coal_in_chest)
print(f"Extracted {coal_in_chest} coal from the chest")

# Step 4: Extract all stone from the chest
stone_in_chest = wooden_chest.inventory.get('stone', 0)
extract_item(Prototype.Stone, wooden_chest.position, stone_in_chest)
print(f"Extracted {stone_in_chest} stone from the chest")

# Step 5: Check updated inventory for verification
current_inventory = inspect_inventory()
assert current_inventory[Prototype.Coal] >= coal_in_chest, f"Failed to gather enough coal. Expected at least {coal_in_chest}, but got {current_inventory[Prototype.Coal]}."
assert current_inventory[Prototype.Stone] >= stone_in_chest, f"Failed to gather enough stone. Expected at least {stone_in_chest}, but got {current_inventory[Prototype.Stone]}."

print("Successfully gathered resources from the chest.")
print(f"Current inventory: {current_inventory}")


"""
Step 3: Mine additional resources. We need to carry out the following substeps:
- Mine stone if there's not enough for a furnace
- Mine copper ore (at least 5)
"""
# Inventory at the start of step {'coal': 17, 'stone': 6}
#Step Execution

# Check if there's enough stone for a furnace
required_stone = 5
current_stone = inspect_inventory().get(Prototype.Stone, 0)
print(f"Current stone in inventory: {current_stone}")

# No need to mine more stone as we already have enough

# Determine how much more copper ore is needed
required_copper_ore = max(0, required_stone + current_stone)

# Find nearest position with copper ore and move there
copper_ore_position = nearest(Resource.CopperOre)
move_to(copper_ore_position)
print(f"Moved to nearest copper ore patch at {copper_ore_position}")

# Harvest the necessary amount of copper ore
mined_copper_ore = harvest_resource(copper_ore_position, required_copper_ore)
print(f"Mined {mined_copper_ore} units of copper ore")

# Verify that we've mined enough resources
inventory_after_mining = inspect_inventory()
assert inventory_after_mining[Prototype.CopperOre] >= required_copper_ore, f"Failed to mine enough Copper Ore. Expected at least {required_copper_ore}, but got {inventory_after_mining.get(Prototype.CopperOre)}."

print("Successfully mined additional resources.")
print(f"Inventory after mining: {inventory_after_mining}")


"""
Step 4: Craft stone furnace. We need to craft a stone furnace using the stone we gathered.
"""
# Inventory at the start of step {'coal': 17, 'stone': 6, 'copper-ore': 11}
#Step Execution

# Check current amount of stone in inventory
current_stone = inspect_inventory().get(Prototype.Stone, 0)
print(f"Current stone available: {current_stone}")

# Craft a Stone Furnace using the gathered stones
craft_item(Prototype.StoneFurnace, 1)
print("Crafted a Stone Furnace")

# Verify that the Stone Furnace is now in our inventory
stone_furnace_count = inspect_inventory().get(Prototype.StoneFurnace, 0)
assert stone_furnace_count >= 1, f"Failed to craft Stone Furnace. Expected at least one but got {stone_furnace_count}."

print("Successfully crafted a Stone Furnace.")


"""
Step 5: Set up smelting operation. We need to carry out the following substeps:
- Place the stone furnace
- Fuel the furnace with coal
"""
# Inventory at the start of step {'stone-furnace': 1, 'coal': 17, 'stone': 1, 'copper-ore': 11}
#Step Execution

# Step 5: Set up smelting operation

# Find position near copper ore patch for placing furnace
copper_ore_position = nearest(Resource.CopperOre)
furnace_position = Position(x=copper_ore_position.x + 2, y=copper_ore_position.y) # Placing slightly away from ore

# Move close enough to place entity
move_to(furnace_position)

# Place the stone furnace at calculated position
stone_furnace = place_entity(Prototype.StoneFurnace, Direction.UP, position=furnace_position)
print(f"Placed Stone Furnace at {furnace_position}")

# Fueling the stone furnace with coal
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
stone_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=coal_in_inventory)
print(f"Inserted {coal_in_inventory} units of coal into Stone Furnace")

# Log current state after setup
current_inventory_after_setup = inspect_inventory()
print("Current Inventory after setting up smelting operation:", current_inventory_after_setup)

print("Successfully set up smelting operation.")


"""
Step 6: Smelt copper plates. We need to carry out the following substeps:
- Put copper ore into the furnace
- Wait for the copper ore to smelt into copper plates
- Collect the copper plates from the furnace
"""
# Placeholder 6

"""
Step 7: Craft copper cables. We need to craft 10 copper cables using the 5 copper plates we smelted.
"""
# Placeholder 7

"""
Step 8: Verify success. Check the inventory to ensure we have 10 copper cables.

##
"""
# Placeholder 8