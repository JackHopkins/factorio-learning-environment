from factorio_instance import *

"""
Main Objective: We need to craft 4 automation science packs. The final success should be checked by looking if the automation science packs are in inventory
"""



"""
Step 1: Print recipes. We need to print the recipes for the following items:
- Automation Science Pack
- Iron Gear Wheel
- Stone Furnace
"""
# Inventory at the start of step {}
#Step Execution

# Fetch and print the recipe for Automation Science Pack
automation_science_pack_recipe = get_prototype_recipe(Prototype.AutomationSciencePack)
print(f"Automation Science Pack Recipe: {automation_science_pack_recipe}")

# Fetch and print the recipe for Iron Gear Wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(f"Iron Gear Wheel Recipe: {iron_gear_wheel_recipe}")

# Fetch and print the recipe for Stone Furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace Recipe: {stone_furnace_recipe}")


"""
Step 2: Gather resources. We need to:
- Collect the coal and copper ore from the wooden chest on the map
- Mine at least 8 iron ore
- Mine 5 stone for crafting a stone furnace
"""
# Inventory at the start of step {}
#Step Execution

# Step 1: Collect resources from wooden chest
chest_position = Position(x=-11.5, y=-11.5)
move_to(chest_position)

# Extract coal from the wooden chest
extract_item(Prototype.Coal, chest_position)
coal_in_inventory = inspect_inventory().get('coal', 0)
print(f"Collected {coal_in_inventory} units of coal from wooden chest.")

# Extract copper ore from the wooden chest
extract_item(Prototype.CopperOre, chest_position)
copper_ore_in_inventory = inspect_inventory().get('copper-ore', 0)
print(f"Collected {copper_ore_in_inventory} units of copper ore from wooden chest.")

# Verify collection was successful
assert coal_in_inventory > 0, "Failed to collect any coal."
assert copper_ore_in_inventory > 0, "Failed to collect any copper ore."

# Step 2: Mine Iron Ore
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)

# Harvest iron ore (mining slightly more than needed for safety)
harvest_resource(iron_ore_position, quantity=10) 
iron_ore_count = inspect_inventory().get('iron-ore', 0)
print(f"Mined {iron_ore_count} units of iron ore.")
assert iron_ore_count >= 8, f"Insufficient iron ore mined: expected at least 8 but got {iron_ore_count}"

# Step 3: Mine Stone
stone_patch_position = nearest(Resource.Stone)
move_to(stone_patch_position)

# Harvest stone (mining slightly more than needed for safety)
harvest_resource(stone_patch_position, quantity=7) 
stone_count = inspect_inventory().get('stone', 0)
print(f"Mined {stone_count} units of stone.")
assert stone_count >= 5, f"Insufficient stone mined: expected at least 5 but got {stone_count}"

final_resources = inspect_inventory()
print(f"Final inventory after gathering resources: {final_resources}")


"""
Step 3: Craft and place stone furnace. We need to:
- Craft a stone furnace using the 5 stone
- Place the stone furnace at a suitable location
"""
# Inventory at the start of step {'coal': 5, 'stone': 7, 'iron-ore': 10, 'copper-ore': 5}
#Step Execution

# Step 1: Craft a Stone Furnace
print("Attempting to craft a Stone Furnace.")
crafted_furnaces = craft_item(Prototype.StoneFurnace, 1)
assert crafted_furnaces == 1, "Failed to craft a Stone Furnace."
print(f"Successfully crafted {crafted_furnaces} Stone Furnace.")

# Step 2: Place the Stone Furnace
# Determine the placement position; for simplicity, use player's current position as reference
player_position = Position(x=0.0, y=0.0) # Assuming player starts at origin

# Move close enough if needed (using move_to ensures we're within range)
move_to(player_position)

# Place the stone furnace at player's position facing UP direction
furnace_position = Position(x=player_position.x + 2, y=player_position.y) # Offset by x+2 for clear space
stone_furnace = place_entity(Prototype.StoneFurnace, Direction.UP, furnace_position)

print(f"Placed Stone Furnace at {furnace_position}.")


"""
Step 4: Smelt ores into plates. We need to:
- Fuel the furnace with coal
- Smelt 4 copper ore into 4 copper plates
- Smelt 8 iron ore into 8 iron plates
"""
# Inventory at the start of step {'coal': 5, 'stone': 2, 'iron-ore': 10, 'copper-ore': 5}
#Step Execution

# Move close enough to interact with the stone furnace
move_to(stone_furnace.position)

# Step 1: Fueling Furnace
print("Inserting coal as fuel into Stone Furnace.")
stone_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=5)
print(f"Coal inserted successfully.")

# Step 2: Smelting Copper Ore
copper_ore_quantity = 4
print(f"Inserting {copper_ore_quantity} copper ore for smelting.")
stone_furnace = insert_item(Prototype.CopperOre, stone_furnace, quantity=copper_ore_quantity)
print("Copper ore inserted successfully.")

# Wait for smelting to complete; assuming each takes about 0.7 seconds per item
sleep(copper_ore_quantity * 0.7)

# Extracting Copper Plates from Furnace
extract_item(Prototype.CopperPlate, stone_furnace.position, quantity=copper_ore_quantity)
copper_plate_count = inspect_inventory().get('copper-plate', 0)
assert copper_plate_count >= copper_ore_quantity, f"Expected at least {copper_ore_quantity} copper plates but got {copper_plate_count}"
print(f"Extracted {copper_plate_count} copper plates.")

# Step 3: Smelting Iron Ore
iron_ore_quantity = 8
print(f"Inserting {iron_ore_quantity} iron ore for smelting.")
stone_furnace = insert_item(Prototype.IronOre, stone_furnace, quantity=iron_ore_quantity)
print("Iron ore inserted successfully.")

# Wait for smelting to complete; assuming each takes about 0.7 seconds per item
sleep(iron_ore_quantity * 0.7)

# Extracting Iron Plates from Furnace
extract_item(Prototype.IronPlate, stone_furnace.position, quantity=iron_ore_quantity)
iron_plate_count = inspect_inventory().get('iron-plate', 0)
assert iron_plate_count >= iron_ore_quantity , f"Expected at least {iron_ore_quantity} iron plates but got {iron_plate_count}"
print(f"Extracted {iron_plate_count} iron plates.")

final_inventory_after_smelting = inspect_inventory()
print(f"Final inventory after all operations: {final_inventory_after_smelting}")


"""
Step 5: Craft iron gear wheels. We need to:
- Craft 4 iron gear wheels using 8 iron plates
"""
# Inventory at the start of step {'stone': 2, 'iron-ore': 2, 'copper-ore': 1, 'iron-plate': 8, 'copper-plate': 4}
#Step Execution

# Step Execution: Craft Iron Gear Wheels

# Check initial inventory for iron plates
initial_iron_plate_count = inspect_inventory().get('iron-plate', 0)
print(f"Initial count of iron plates: {initial_iron_plate_count}")
assert initial_iron_plate_count >= 8, "Not enough iron plates to craft Iron Gear Wheels."

# Crafting process
number_of_gears_to_craft = 4
crafted_gears = craft_item(Prototype.IronGearWheel, number_of_gears_to_craft)
print(f"Crafted {crafted_gears} Iron Gear Wheels.")

# Verify that we have crafted the correct amount of gears
final_gear_wheel_count = inspect_inventory().get('iron-gear-wheel', 0)
assert final_gear_wheel_count >= number_of_gears_to_craft, f"Expected at least {number_of_gears_to_craft} Iron Gear Wheels but got {final_gear_wheel_count}"
print(f"Successfully crafted {final_gear_wheel_count} Iron Gear Wheels.")


"""
Step 6: Craft automation science packs. We need to:
- Craft 4 automation science packs using 4 copper plates and 4 iron gear wheels
"""
# Inventory at the start of step {'stone': 2, 'iron-ore': 2, 'copper-ore': 1, 'copper-plate': 4, 'iron-gear-wheel': 4}
#Step Execution

# Check initial inventory for required materials
copper_plate_count = inspect_inventory().get('copper-plate', 0)
iron_gear_wheel_count = inspect_inventory().get('iron-gear-wheel', 0)

print(f"Initial count of copper plates: {copper_plate_count}")
print(f"Initial count of iron gear wheels: {iron_gear_wheel_count}")

# Assert if we have enough materials to proceed with crafting
assert copper_plate_count >= 4, "Not enough copper plates to craft Automation Science Packs."
assert iron_gear_wheel_count >= 4, "Not enough iron gear wheels to craft Automation Science Packs."

# Crafting process for Automation Science Packs
number_of_packs_to_craft = 4
crafted_packs = craft_item(Prototype.AutomationSciencePack, number_of_packs_to_craft)
print(f"Crafted {crafted_packs} Automation Science Packs.")

# Verify that we have crafted the correct amount of automation science packs
final_pack_count = inspect_inventory().get('automation-science-pack', 0)
assert final_pack_count >= number_of_packs_to_craft, f"Expected at least {number_of_packs_to_craft} Automation Science Packs but got {final_pack_count}"
print(f"Successfully crafted {final_pack_count} Automation Science Packs.")


"""
Step 7: Verify success. Check the inventory to ensure we have 4 automation science packs.
##
"""
# Inventory at the start of step {'stone': 2, 'iron-ore': 2, 'copper-ore': 1, 'automation-science-pack': 4}
#Step Execution

# Inspect current inventory for automation science packs
automation_science_pack_count = inspect_inventory().get('automation-science-pack', 0)
print(f"Current count of Automation Science Packs in inventory: {automation_science_pack_count}")

# Assert if we have met the requirement of having at least 4 automation science packs
assert automation_science_pack_count >= 4, f"Expected at least 4 Automation Science Packs but got {automation_science_pack_count}"

# Success message upon verification
print("Successfully verified presence of 4 Automation Science Packs in inventory.")
