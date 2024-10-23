from factorio_instance import *

"""
Main Objective: We need 5 iron gear wheels. The final success should be checked by looking if 5 gear wheels are in inventory
"""



"""
Step 1: Gather resources
- Move to the nearest coal patch and mine at least 20 coal
- Move to the nearest iron ore patch and mine at least 20 iron ore
OUTPUT CHECK: Verify that we have at least 20 coal and 20 iron ore in our inventory
"""
# Inventory at the start of step {}
#Step Execution

# Define the required resources
required_coal = 20
required_iron_ore = 20

# Mine coal
coal_position = nearest(Resource.Coal)
move_to(coal_position)
coal_mined = harvest_resource(coal_position, required_coal)
print(f"Mined {coal_mined} coal")

# Mine iron ore
iron_position = nearest(Resource.IronOre)
move_to(iron_position)
iron_mined = harvest_resource(iron_position, required_iron_ore)
print(f"Mined {iron_mined} iron ore")

# Check inventory
final_inventory = inspect_inventory()
print(f"Final inventory after harvesting: {final_inventory}")

# Verify that we have the required resources
assert final_inventory[Prototype.Coal] >= required_coal, f"Failed to gather enough coal. Required {required_coal}, but got {final_inventory[Prototype.Coal]}"
assert final_inventory[Prototype.IronOre] >= required_iron_ore, f"Failed to gather enough iron ore. Required {required_iron_ore}, but got {final_inventory[Prototype.IronOre]}"

print("Successfully gathered the required resources")


"""
Step 2: Fuel and prepare the furnace
- Move to the stone furnace at position (-12.0, -12.0)
- Place 5 coal into the furnace as fuel
OUTPUT CHECK: Verify that the furnace's fuel status is no longer 'no fuel'
"""
# Inventory at the start of step {'coal': 20, 'iron-ore': 20}
#Step Execution

# Step 2: Fuel and prepare the furnace

# Move to the stone furnace at position (-12.0, -12.0)
furnace_position = Position(x=-12.0, y=-12.0)
move_to(furnace_position)

# Get reference to existing stone furnace on map
stone_furnaces = get_entities({Prototype.StoneFurnace})
stone_furnace = next((f for f in stone_furnaces if f.position.is_close(furnace_position)), None)

assert stone_furnace is not None, "Stone Furnace not found at expected location."

# Place 5 coal into the furnace as fuel
coal_to_insert = 5
insert_item(Prototype.Coal, stone_furnace, coal_to_insert)
print(f"Inserted {coal_to_insert} coal into the stone furnace")

# Verify that the furnace's fuel status is no longer 'no fuel'
updated_stone_furnace = inspect_entities(position=furnace_position).get_entity(Prototype.StoneFurnace)
assert updated_stone_furnace.status != EntityStatus.NO_FUEL, "Furnace still indicates 'no fuel' after insertion."
print("Successfully fueled and prepared the furnace.")


"""
Step 3: Smelt iron plates
- Place 15 iron ore into the furnace
- Wait for the smelting process to complete (approximately 15 seconds)
OUTPUT CHECK: Verify that we have at least 15 iron plates in our inventory
"""
# Inventory at the start of step {'coal': 15, 'iron-ore': 20}
#Step Execution

# Get reference to existing stone furnace on map
stone_furnaces = get_entities({Prototype.StoneFurnace})
stone_furnace = next((f for f in stone_furnaces if f.position.is_close(Position(x=-12.0, y=-12.0))), None)

assert stone_furnace is not None, "Stone Furnace not found at expected location."

# Insert 15 iron ore into the furnace
iron_ore_to_insert = 15
insert_item(Prototype.IronOre, stone_furnace, iron_ore_to_insert)
print(f"Inserted {iron_ore_to_insert} iron ore into the stone furnace")

# Wait for smelting process to complete (approximately one second per ore)
sleep(iron_ore_to_insert * 1)

# Attempt to extract all possible iron plates from the furnace
extract_item(Prototype.IronPlate, stone_furnace.position, quantity=iron_ore_to_insert)
print(f"Attempted extraction of {iron_ore_to_insert} iron plates from the furnace")

# Check inventory for number of extracted iron plates
final_inventory = inspect_inventory()
extracted_plates = final_inventory.get(Prototype.IronPlate, 0)
print(f"Inventory after extracting: {final_inventory}")

# Verify that we have at least 15 iron plates in our inventory
assert extracted_plates >= 15, f"Failed to obtain enough iron plates. Expected at least {iron_ore_to_insert}, but got {extracted_plates}"

print("Successfully smelted and obtained required amount of iron plates.")


"""
Step 4: Craft iron gear wheels
- Open the crafting menu
- Select the iron gear wheel recipe
- Craft 5 iron gear wheels
OUTPUT CHECK: Verify that we have 5 iron gear wheels in our inventory

##
"""
# Inventory at the start of step {'coal': 15, 'iron-ore': 5, 'iron-plate': 15}
#Step Execution

# Craft 5 iron gear wheels
gear_wheels_to_craft = 5
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, gear_wheels_to_craft)
print(f"Crafted {crafted_gear_wheels} iron gear wheels")

# Check if we crafted all desired gears
assert crafted_gear_wheels == gear_wheels_to_craft, f"Failed to craft all required iron gear wheels. Expected {gear_wheels_to_craft}, but got {crafted_gear_wheels}"

# Verify that we have at least 5 iron gear wheels in our inventory
final_inventory = inspect_inventory()
iron_gear_count = final_inventory.get(Prototype.IronGearWheel, 0)
assert iron_gear_count >= 5, f"Inventory check failed! Expected at least 5 Iron Gear Wheels but found {iron_gear_count}"
print("Successfully crafted and verified the required number of iron gear wheels.")
