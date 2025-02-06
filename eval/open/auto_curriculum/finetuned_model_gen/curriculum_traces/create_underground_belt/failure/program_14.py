
from instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- underground-belt
- stone-furnace
- iron-gear-wheel
- transport-belt
"""
# Get the recipe for underground-belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)

# Get the recipe for stone-furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)

# Get the recipe for iron-gear-wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)

# Get the recipe for transport-belt
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)

# Print all recipes
print("Recipes:")
print(f"Underground Belt: {underground_belt_recipe}")
print(f"Stone Furnace: {stone_furnace_recipe}")
print(f"Iron Gear Wheel: {iron_gear_wheel_recipe}")
print(f"Transport Belt: {transport_belt_recipe}")

"""
Step 2: Craft stone furnace. We need to gather stone and craft a stone furnace.
- Print recipe for stone furnace
- Mine 6 stone
- Craft 1 stone furnace
"""
# Print recipe for stone furnace
print("Stone Furnace Recipe: 5 stone")

# Mine 6 stone
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=6)

# Craft 1 stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)

# Check if stone furnace is crafted
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace) >= 1, "Failed to craft stone furnace"
print("Successfully crafted stone furnace")

"""
Step 3: Set up iron smelting. We need to set up a basic iron smelting operation.
- Place stone furnace
- Mine 10 iron ore
- Mine 5 coal
- Insert coal into furnace as fuel
- Insert iron ore into furnace
- Wait for smelting
- Extract iron plates (we need at least 14)
"""
# Place stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)

# Mine 10 iron ore
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
harvest_resource(iron_ore_position, quantity=10)

# Mine 5 coal
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, quantity=5)

# Move back to furnace and insert coal
move_to(furnace.position)
insert_item(Prototype.Coal, furnace, quantity=5)

# Insert iron ore into furnace
insert_item(Prototype.IronOre, furnace, quantity=10)

# Wait for smelting
sleep(10)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=10)

# Check if we have enough iron plates
inventory = inspect_inventory()
assert inventory.get(Prototype.IronPlate) >= 10, "Failed to smelt enough iron plates"
print("Successfully smelted iron plates")

"""
Step 4: Craft transport belts. We need to craft transport belts as they're a component of underground belts.
- Print recipe for transport belts
- Craft 5 transport belts (requires 10 iron plates, 10 iron gear wheels)
"""
# Print recipe for transport belts
print("Transport Belt Recipe: 1 iron plate, 1 iron gear wheel")

# Craft iron gear wheels (5 for transport belts)
craft_item(Prototype.IronGearWheel, quantity=5)

# Craft transport belts (5)
craft_item(Prototype.TransportBelt, quantity=5)

# Check if transport belts are crafted
inventory = inspect_inventory()
assert inventory.get(Prototype.TransportBelt) >= 5, "Failed to craft transport belts"
print("Successfully crafted transport belts")

"""
Step 5: Craft underground belts. We need to craft the underground belts.
- Print recipe for underground belts
- Craft 1 underground belt (requires 10 iron plates, 10 iron gear wheels, 5 transport belts)
"""
# Print recipe for underground belts
print("Underground Belt Recipe: 10 iron plates, 10 iron gear wheels, 5 transport belts")

# Craft underground belt (1)
craft_item(Prototype.UndergroundBelt, quantity=1)

# Check if underground belt is crafted
inventory = inspect_inventory()
assert inventory.get(Prototype.UndergroundBelt) >= 1, "Failed to craft underground belt"
print("Successfully crafted underground belt")

"""
Step 6: Verify crafting. We need to verify that we've crafted all the required items.
- Check inventory for underground belt
"""
# Check if underground belt is in inventory
inventory = inspect_inventory()
assert inventory.get(Prototype.UndergroundBelt) >= 1, "Underground belt not found in inventory"
print("Underground belt found in inventory")

print("Successfully completed all steps")
