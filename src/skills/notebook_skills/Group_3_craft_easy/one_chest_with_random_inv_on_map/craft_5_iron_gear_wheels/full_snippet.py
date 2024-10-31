from factorio_instance import *

"""
Main Objective: We need to craft 5 iron gear wheels. The final success should be checked by looking if the gear wheels are in inventory
"""



"""
Step 1: Print recipe for iron gear wheels
- Print the recipe for iron gear wheels
"""
# Inventory at the start of step {}
#Step Execution

# Get the recipe for iron gear wheels
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)

# Print out the retrieved recipe
print(f"Iron Gear Wheel Recipe: {iron_gear_wheel_recipe}")


"""
Step 2: Craft a stone furnace
- Move to the wooden chest
- Take 5 stone from the chest
- Craft a stone furnace
"""
# Inventory at the start of step {}
#Step Execution

# Step 2: Craft a stone furnace

# Find nearest position of wooden chest
wooden_chest_position = Position(x=-11.5, y=-11.5)

# Move to wooden chest
print(f"Moving to wooden chest at {wooden_chest_position}")
move_to(wooden_chest_position)
print("Arrived at wooden chest.")

# Extract 5 stones from wooden chest
stone_quantity = 5
extracted_stone_success = extract_item(Prototype.Stone, wooden_chest_position, stone_quantity)
assert extracted_stone_success, "Failed to extract stone from wooden chest."
print(f"Extracted {stone_quantity} stones from the wooden chest.")

# Craft a stone furnace with extracted stones
crafted_furnace_count = craft_item(Prototype.StoneFurnace, 1)
assert crafted_furnace_count == 1, "Failed to craft a stone furnace."
print("Successfully crafted a stone furnace.")


"""
Step 3: Smelt iron ore into iron plates
- Place the stone furnace near the wooden chest
- Take coal from the chest and add it to the furnace
- Take iron ore from the chest and add it to the furnace
- Wait for the iron ore to smelt into iron plates
- Collect the iron plates
"""
# Inventory at the start of step {'stone-furnace': 1}
#Step Execution

# Step 3: Smelt iron ore into iron plates

# Place stone furnace near wooden chest
furnace_position = Position(x=-11.0, y=-12.0)
print(f"Placing stone furnace at {furnace_position}")
stone_furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)

# Move to wooden chest to extract resources
move_to(wooden_chest_position)
print("Arrived at wooden chest.")

# Extract coal from wooden chest
coal_quantity = 5  # Take enough coal for smelting process
extracted_coal_success = extract_item(Prototype.Coal, wooden_chest_position, coal_quantity)
assert extracted_coal_success, "Failed to extract coal from wooden chest."
print(f"Extracted {coal_quantity} units of coal.")

# Extract all available iron ore from wooden chest
wooden_chest = get_entity(Prototype.WoodenChest, wooden_chest_position)
iron_ore_quantity = wooden_chest.inventory.get(Prototype.IronOre, 0)
extracted_iron_ore_success = extract_item(Prototype.IronOre, wooden_chest_position, iron_ore_quantity)
assert extracted_iron_ore_success, "Failed to extract all available iron ore from wooden chest."
print(f"Extracted {iron_ore_quantity} units of iron ore.")

# Insert extracted items into stone furnace
stone_furnace = insert_item(Prototype.Coal, stone_furnace, coal_quantity)
stone_furnace = insert_item(Prototype.IronOre, stone_furnace, iron_ore_quantity)
print(f"Inserted {coal_quantity} units of coal and {iron_ore_quantity} units of iron ore into the furnace.")

# Wait for smelting process - approximately 3.5 seconds per iron plate (0.7 * 5 attempts)
smelt_time = iron_ore_quantity * 3.5
sleep(smelt_time)

# Extract iron plates
expected_iron_plates = iron_ore_quantity
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, stone_furnace.position, expected_iron_plates)
    iron_plates_in_inventory = inspect_inventory()[Prototype.IronPlate]
    if iron_plates_in_inventory >= expected_iron_plates:
        break
    sleep(10)  # Wait a bit more if not all plates are ready

print(f"Extracted {iron_plates_in_inventory} iron plates from the furnace")
assert iron_plates_in_inventory >= expected_iron_plates, f"Failed to smelt enough iron plates. Expected {expected_iron_plates}, but got {iron_plates_in_inventory}"
print(f"Inventory after smelting: {inspect_inventory()}")


"""
Step 4: Craft iron gear wheels
- Use the crafting menu to craft 5 iron gear wheels using the 10 iron plates
"""
# Inventory at the start of step {'iron-plate': 13}
#Step Execution

# Crafting 5 Iron Gear Wheels

# Define how many gear wheels we want to craft
gear_wheels_to_craft = 5

# Use crafting menu to craft the specified number of iron gear wheels
crafted_gear_wheels_count = craft_item(Prototype.IronGearWheel, quantity=gear_wheels_to_craft)

# Assert that we've successfully crafted all desired gear wheels
assert crafted_gear_wheels_count == gear_wheels_to_craft, f"Failed to craft {gear_wheels_to_craft} Iron Gear Wheels."

print(f"Successfully crafted {crafted_gear_wheels_count} Iron Gear Wheels.")


"""
Step 5: Check inventory
- Check the inventory to confirm that 5 iron gear wheels have been crafted
##
"""
# Inventory at the start of step {'iron-plate': 3, 'iron-gear-wheel': 5}
#Step Execution

# Step 5: Check Inventory for Iron Gear Wheels

# Inspecting player inventory
current_inventory = inspect_inventory()
print(f"Current Inventory: {current_inventory}")

# Retrieve number of iron gear wheels
iron_gear_wheels_count = current_inventory.get(Prototype.IronGearWheel, 0)
print(f"Iron Gear Wheels Count in Inventory: {iron_gear_wheels_count}")

# Assert to check if there are exactly 5 iron gear wheels in the inventory
assert iron_gear_wheels_count == 5, f"Inventory verification failed! Expected 5 Iron Gear Wheels but found {iron_gear_wheels_count}."

print("Successfully verified that there are exactly 5 Iron Gear Wheels in the inventory.")
