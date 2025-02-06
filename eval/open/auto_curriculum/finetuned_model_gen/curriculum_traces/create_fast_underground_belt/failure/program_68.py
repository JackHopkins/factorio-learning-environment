
from instance import *


"""
Step 1: Print recipes. We need to craft the following items:
- 2 underground-belts (each requires 5 iron gear wheels and 1 transport belt)
- 1 fast-underground-belt (requires 2 underground-belts and 8 iron gear wheels)

Step 2: Calculate total resources needed. We need at least 40 iron plates to craft 8 iron gear wheels and 2 transport belts.
- 8 iron gear wheels (each requires 2 iron plates)
- 4 iron plates for 2 transport belts (each requires 1 iron plate)

Step 3: Gather raw resources. We need to mine at least 40 iron ore.
- Move to the nearest iron ore patch
- Mine 40 iron ore

Step 4: Set up smelting operation. We need to smelt 40 iron ore into 40 iron plates.
- Move to the origin (0,0)
- Craft and place a stone furnace
- Insert 40 iron ore and coal into the furnace
- Wait for smelting to complete (approximately 20 seconds)
- Extract 40 iron plates from the furnace

Step 5: Craft intermediate items. We need to craft 8 iron gear wheels and 2 transport belts.
- Craft 8 iron gear wheels
- Craft 2 transport belts

Step 6: Craft final products. We need to craft 2 underground-belts and 1 fast-underground-belt.
- Craft 2 underground-belts
- Craft 1 fast-underground-belt

Step 7: Verify success. Check that we have 1 fast-underground-belt in our inventory.
"""

"""
Step 1: Print recipes
"""
# Get the recipes for underground-belt and fast-underground-belt
recipes = [
    get_prototype_recipe(Prototype.UndergroundBelt),
    get_prototype_recipe(Prototype.FastUndergroundBelt)
]

# Print the recipes
for recipe in recipes:
    print(f"Recipe for {recipe.name}:")
    print(f"Ingredients: {recipe.ingredients}")

"""
Step 2: Calculate total resources needed
"""
# Calculate total iron plates needed
iron_gear_wheels = 8 * 2  # 8 iron gear wheels, each requires 2 iron plates
transport_belts = 2 * 1   # 2 transport belts, each requires 1 iron plate
total_iron_plates = iron_gear_wheels + transport_belts

print(f"Total iron plates needed: {total_iron_plates}")

"""
Step 3: Gather raw resources
"""
# Find the nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
print(f"Nearest iron ore found at: {iron_ore_position}")

# Move to the iron ore position
move_to(iron_ore_position)

# Mine 40 iron ore
harvested_iron = harvest_resource(iron_ore_position, quantity=40)
print(f"Harvested iron ore: {harvested_iron}")

# Verify that we have enough iron ore
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronOre) >= 40, f"Failed to gather enough iron ore. Current inventory: {current_inventory}"

"""
Step 4: Set up smelting operation
"""
# Move to the origin
origin = Position(x=0, y=0)
move_to(origin)

# Craft a stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)

# Place the stone furnace
furnace = place_entity(Prototype.StoneFurnace, position=origin)

# Insert iron ore and coal into the furnace
insert_item(Prototype.IronOre, furnace, quantity=40)
insert_item(Prototype.Coal, furnace, quantity=20)  # Assuming we have coal, otherwise need to mine it

# Wait for smelting to complete
smelting_time = int(40 * 0.5)  # 0.5 seconds per iron ore
sleep(smelting_time)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=40)

# Verify that we have enough iron plates
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronPlate) >= 40, f"Failed to smelt enough iron plates. Current inventory: {current_inventory}"

"""
Step 5: Craft intermediate items
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=8)

# Craft transport belts
craft_item(Prototype.TransportBelt, quantity=2)

"""
Step 6: Craft final products
"""
# Craft underground-belts
craft_item(Prototype.UndergroundBelt, quantity=2)

# Craft fast-underground-belt
craft_item(Prototype.FastUndergroundBelt, quantity=1)

"""
Step 7: Verify success
"""
# Check inventory for fast-underground-belt
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.FastUndergroundBelt) >= 1, f"Failed to craft fast-underground-belt. Current inventory: {final_inventory}"

print("Successfully crafted fast-underground-belt!")
print(f"Final inventory: {final_inventory}")

