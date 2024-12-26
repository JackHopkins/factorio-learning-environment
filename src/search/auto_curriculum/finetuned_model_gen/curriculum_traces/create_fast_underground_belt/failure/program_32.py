
from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipes for the entities we need to craft.
"""
# Get the recipe for fast-underground-belt
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)

# Print the recipe details
print("fast-underground-belt Recipe:")
print(fast_underground_belt_recipe)

# Get the recipe for iron-gear-wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)

# Print the recipe details
print("Iron Gear Wheel Recipe:")
print(iron_gear_wheel_recipe)

# Get the recipe for underground-belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)

# Print the recipe details
print("Underground Belt Recipe:")
print(underground_belt_recipe)

"""
Step 2: Craft and set up a stone furnace. We need to craft a stone furnace and place it on the map.
"""
# Get stone for the furnace
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=5)

# Craft the stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)

# Place the stone furnace
current_pos = Position(x=0, y=0)
furnace = place_entity(Prototype.StoneFurnace, position=current_pos)

"""
Step 3: Prepare materials. We need to mine iron ore and coal, and smelt iron plates.
"""
# Mine iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=80)  # We need 80 iron plates for the recipes

# Mine coal for fuel
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=20)  # Get extra coal for future use

# Move back to the furnace
move_to(furnace.position)

# Insert coal into the furnace as fuel
furnace = insert_item(Prototype.Coal, furnace, quantity=10)

# Insert iron ore into the furnace
furnace = insert_item(Prototype.IronOre, furnace, quantity=80)

# Wait for smelting to complete
sleep(20)

# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, furnace.position, quantity=80)
    inventory = inspect_inventory()
    if inventory.get(Prototype.IronPlate, 0) >= 80:
        break
    sleep(5)

assert inventory.get(Prototype.IronPlate, 0) >= 80, "Failed to obtain required iron plates"

"""
Step 4: Craft iron gear wheels. We need to craft 40 iron gear wheels.
"""
craft_item(Prototype.IronGearWheel, quantity=40)

# Verify that we have the required iron gear wheels
inventory = inspect_inventory()
assert inventory.get(Prototype.IronGearWheel, 0) >= 40, "Failed to craft required iron gear wheels"

"""
Step 5: Craft underground-belts. We need to craft 2 underground-belts.
"""
craft_item(Prototype.UndergroundBelt, quantity=2)

# Verify that we have the required underground-belts
inventory = inspect_inventory()
assert inventory.get(Prototype.UndergroundBelt, 0) >= 2, "Failed to craft required underground-belts"

"""
Step 6: Craft fast-underground-belt. We need to craft 1 fast-underground-belt.
"""
craft_item(Prototype.FastUndergroundBelt, quantity=1)

# Verify that we have crafted the fast-underground-belt
inventory = inspect_inventory()
assert inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, "Failed to craft required fast-underground-belt"

print("Successfully crafted a fast-underground-belt!")
