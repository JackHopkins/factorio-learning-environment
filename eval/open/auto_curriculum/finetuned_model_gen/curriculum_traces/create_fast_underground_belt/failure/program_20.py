

from instance import *

"""
Analysis:
- We need to craft a fast-underground-belt
- There are no entities on the map and the inventory is empty
- We need to craft everything from scratch
"""

"""
Recipes:
- Fast-underground-belt requires 2 iron gear wheels and 1 underground-belt
- Underground-belt requires 1 iron gear wheel and 1 iron plate
- Iron gear wheel requires 2 iron plates
- We need a stone furnace for smelting iron plates
"""

"""
Step 1: Print recipes
"""
# Get the recipe for iron gear wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(f"Iron Gear Wheel Recipe: {iron_gear_wheel_recipe}")

# Get the recipe for underground-belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print(f"Underground Belt Recipe: {underground_belt_recipe}")

# Get the recipe for fast-underground-belt
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
print(f"Fast Underground Belt Recipe: {fast_underground_belt_recipe}")

"""
Step 2: Craft stone furnace
"""
# We need 5 stone to craft a stone furnace
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=5)

# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)

"""
Step 3: Setup smelting
"""
# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)

# Get coal for fuel
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, quantity=10)  # Get extra for fueling

# Fuel the furnace
move_to(furnace.position)
fueled_furnace = insert_item(Prototype.Coal, furnace, quantity=5)

"""
Step 4: Smelt iron plates
"""
# We need 4 iron plates per iron gear wheel, so let's smelt 8 iron plates
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
harvest_resource(iron_ore_position, quantity=8)

# Insert iron ore into the furnace
move_to(furnace.position)
insert_item(Prototype.IronOre, fueled_furnace, quantity=8)

# Wait for smelting
sleep(10)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=8)

# Verify we have iron plates
inventory = inspect_inventory()
assert inventory.get(Prototype.IronPlate) >= 8, "Failed to get enough iron plates"

"""
Step 5: Craft iron gear wheels
"""
craft_item(Prototype.IronGearWheel, quantity=4)

"""
Step 6: Craft underground-belts
"""
craft_item(Prototype.UndergroundBelt, quantity=2)

"""
Step 7: Craft fast-underground-belt
"""
craft_item(Prototype.FastUndergroundBelt, quantity=1)

"""
Step 8: Verify crafting
"""
inventory = inspect_inventory()
assert inventory.get(Prototype.FastUndergroundBelt) >= 1, "Failed to craft fast-underground-belt"
print("Successfully crafted fast-underground-belt")

