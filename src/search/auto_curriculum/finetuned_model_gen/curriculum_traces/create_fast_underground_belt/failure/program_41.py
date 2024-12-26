
from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipes for fast-underground-belt and stone-furnace
"""
# Print the recipes for fast-underground-belt and stone-furnace
print("fast-underground-belt recipe: 5 iron gear wheels, 1 underground belt")
print("stone-furnace recipe: 5 stone")

"""
Step 2: Craft a stone furnace. We need to gather 5 stone and craft a stone furnace
"""
# Gather 5 stone
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=5)

# Craft a stone furnace
craft_item(Prototype.StoneFurnace, 1)

"""
Step 3: Set up iron smelting. We need to gather coal for fuel, mine iron ore, and set up a stone furnace to smelt iron plates
"""
# Gather coal for fuel
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, quantity=10)

# Mine iron ore
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
harvest_resource(iron_ore_position, quantity=98)

# Place stone furnace near the player
player_position = Position(x=0, y=0)
move_to(player_position)
furnace = place_entity(Prototype.StoneFurnace, position=player_position)

# Add coal to the furnace
insert_item(Prototype.Coal, furnace, quantity=5)

# Add iron ore to the furnace
insert_item(Prototype.IronOre, furnace, quantity=98)

"""
Step 4: Craft iron gear wheels. We need to craft 40 iron gear wheels
"""
# Extract iron plates
for _ in range(5):  # Attempt to extract multiple times to ensure all plates are collected
    extract_item(Prototype.IronPlate, furnace.position, quantity=98)
    inventory = inspect_inventory()
    if inventory.get(Prototype.IronPlate, 0) >= 98:
        break
    sleep(1)

# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, 40)

"""
Step 5: Craft underground belts. We need to craft 2 underground belts
"""
# Craft 2 underground belts
craft_item(Prototype.UndergroundBelt, 2)

"""
Step 6: Craft fast-underground-belt. We need to craft 1 fast-underground-belt
"""
# Craft 1 fast-underground-belt
craft_item(Prototype.FastUndergroundBelt, 1)

"""
Step 7: Verify crafting. We need to check if the fast-underground-belt was crafted successfully
"""
# Check the inventory for fast-underground-belt
inventory = inspect_inventory()
assert inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, "Fast-underground-belt not crafted successfully"

# Final inventory check
print("Final inventory:")
print(f"Fast-underground-belt: {inventory.get(Prototype.FastUndergroundBelt, 0)}")
