

from instance import *


"""
Step 1: Print recipes. We need to print the recipes for the items we need to craft
"""
# get the recipe for fast-underground-belt
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)

# print the recipes
print(f"Recipe for fast-underground-belt: {fast_underground_belt_recipe}")

"""
Step 2: Crafting and setting up the smelting area
- craft and place 1 stone furnace
- mine 40 iron ore
- mine 20 coal
- smelt 40 iron plates
"""
# Craft the stone furnace
# We need 5 stone to craft a stone furnace
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=5)
craft_item(Prototype.StoneFurnace, 1)

# Place the stone furnace
origin = Position(x=0, y=0)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed stone furnace at {furnace.position}")

# Mine iron ore
iron_position = nearest(Resource.IronOre)
move_to(iron_position)
harvest_resource(iron_position, quantity=40)
print("Mined 40 iron ore")

# Mine coal
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, quantity=20)
print("Mined 20 coal")

# Move back to the furnace
move_to(furnace.position)

# Insert coal into the furnace as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=10)
print("Inserted coal into the furnace")

# Insert iron ore into the furnace
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=40)
print("Inserted iron ore into the furnace")

# Wait for the smelting to complete
smelting_time = 40 * 0.7  # 0.7 seconds per iron plate
sleep(smelting_time)

# Extract the iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=40)
    inventory = inspect_inventory()
    if inventory.get(Prototype.IronPlate, 0) >= 40:
        break
    sleep(10)

print(f"Extracted iron plates; Current inventory: {inspect_inventory()}")

"""
Step 3: Crafting intermediate products
- craft 20 iron gear wheels (requires 40 iron plates)
- craft 2 underground belts (requires 10 iron gear wheels, 4 iron plates)
"""
# Craft 20 iron gear wheels
craft_item(Prototype.IronGearWheel, 20)
print("Crafted 20 iron gear wheels")

# Check if we have enough iron plates left
inventory = inspect_inventory()
remaining_iron_plates = inventory.get(Prototype.IronPlate, 0)
assert remaining_iron_plates >= 4, f"Not enough iron plates to craft underground belts; need at least 4, have {remaining_iron_plates}"

# Craft 2 underground belts
craft_item(Prototype.UndergroundBelt, 2)
print("Crafted 2 underground belts")

"""
Step 4: Craft the fast-underground-belt
- craft 1 fast-underground-belt (requires 2 underground belts, 20 iron gear wheels)
"""
# Craft 1 fast-underground-belt
craft_item(Prototype.FastUndergroundBelt, 1)
print("Crafted 1 fast-underground-belt")

# Check the inventory to ensure we have the fast-underground-belt
inventory = inspect_inventory()
fast_underground_belt_count = inventory.get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belt_count >= 1, f"Failed to craft fast-underground-belt; expected at least 1, found {fast_underground_belt_count}"

print(f"Successfully crafted {fast_underground_belt_count} fast-underground-belt(s)")

craft_item(Prototype.FastUndergroundBelt, quantity=1)
