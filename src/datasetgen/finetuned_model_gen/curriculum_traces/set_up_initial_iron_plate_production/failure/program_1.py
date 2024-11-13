

from factorio_instance import *

"""
Policy to set up initial iron plate production. There are no entities on the map or in the inventory, 
so we need to craft a stone furnace from scratch and gather all necessary resources.
"""

"""
Step 1: Print recipes
"""
# Fetch and print recipe for stone furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace Recipe: Needs {stone_furnace_recipe.ingredients[0].count} {stone_furnace_recipe.ingredients[0].name}")

# Fetch and print recipe for iron plate
iron_plate_recipe = get_prototype_recipe(Prototype.IronPlate)
print(f"Iron Plate Recipe: Needs {iron_plate_recipe.ingredients[0].count} {iron_plate_recipe.ingredients[0].name}")

"""
Step 2: Craft stone furnace
"""
# Mine stone for crafting the stone furnace
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=5)

# Craft the stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 Stone Furnace")

# Move to origin and place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed Stone Furnace at {furnace.position}")

"""
Step 3: Mine resources
"""
# Mine iron ore
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
harvested_iron = harvest_resource(iron_ore_position, quantity=10)
print(f"Mined {harvested_iron} Iron Ore")

# Mine coal for fuel
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvested_coal = harvest_resource(coal_position, quantity=5)
print(f"Mined {harvested_coal} Coal")

"""
Step 4: Set up iron plate production
"""
# Move back to the furnace
move_to(furnace.position)

# Add coal to the furnace as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=5)
print("Inserted Coal into the Stone Furnace")

# Add iron ore to the furnace
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
if iron_ore_in_inventory > 0:
    updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
    print("Inserted Iron Ore into the Stone Furnace")
else:
    print("No Iron Ore found in inventory!")

"""
Step 5: Smelt iron plates
"""
# Wait for smelting to complete
smelting_time = 0.7 * iron_ore_in_inventory  # 0.7 seconds per iron plate
sleep(smelting_time)

# Extract iron plates
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    iron_plates_in_inventory = inspect_inventory()[Prototype.IronPlate]
    if iron_plates_in_inventory >= 10:
        break
    sleep(5)  # Allow extra time if needed

print(f"Extracted {iron_plates_in_inventory} Iron Plates")

# Final assertion to verify if we have produced enough iron plates
assert iron_plates_in_inventory >= 10, f"Failed to produce required number of Iron Plates! Current count: {iron_plates_in_inventory}"

print("Successfully set up initial iron plate production!")

