

from factorio_instance import *

"""
Objective: Craft a fast-underground-belt from scratch

Planning:
We need to craft a fast-underground-belt, which requires 2 underground belts and 20 iron gear wheels.
There are no entities on the map and the inventory is empty, so we need to start from scratch.
We'll need to mine iron ore, smelt it into iron plates, craft iron gear wheels, and then craft the underground belts.
Finally, we'll craft the fast-underground-belt.
"""

"""
Step 1: Print recipe for fast-underground-belt
"""
recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
print("FastUndergroundBelt Recipe:")
print(f"Ingredients: {recipe.ingredients}")

"""
Step 2: Calculate iron plates needed
We need 2 underground belts and 20 iron gear wheels
Each underground belt requires 10 iron gear wheels and 5 iron plates (for the transport belt)
Each iron gear wheel requires 2 iron plates
Total iron plates needed = 2 * (10 * 2 + 5) + 20 * 2 = 100
"""
total_iron_plates_needed = 100

"""
Step 3: Gather resources
- Mine iron ore
- Smelt iron ore into iron plates
"""
iron_ore_per_plate = 1
iron_ore_needed = total_iron_plates_needed * iron_ore_per_plate

# Find and mine iron ore
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
harvested = harvest_resource(iron_ore_position, iron_ore_needed)
print(f"Harvested {harvested} iron ore")

# Verify iron ore quantity
inventory = inspect_inventory()
assert inventory.get(Prototype.IronOre, 0) >= iron_ore_needed, "Failed to gather enough iron ore"

# Find and move to stone patch for furnace
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, 5)

# Craft and place furnace
craft_item(Prototype.StoneFurnace, 1)
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=iron_ore_position.x+2, y=iron_ore_position.y))

# Insert iron ore and coal into furnace
insert_item(Prototype.IronOre, furnace, iron_ore_needed)
insert_item(Prototype.Coal, furnace, 50)

# Wait for smelting
sleep(10)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, total_iron_plates_needed)

# Verify iron plates quantity
inventory = inspect_inventory()
assert inventory.get(Prototype.IronPlate, 0) >= total_iron_plates_needed, "Failed to smelt enough iron plates"

print(f"Gathered and smelted {inventory.get(Prototype.IronPlate, 0)} iron plates")

"""
Step 4: Craft iron gear wheels
"""
iron_plates_for_gears = 40  # 20 gear wheels * 2 iron plates each
craft_item(Prototype.IronGearWheel, 20)
print("Crafted 20 iron gear wheels")

"""
Step 5: Craft underground belts
"""
iron_plates_for_underground_belts = 10  # 2 underground belts * 5 iron plates each
craft_item(Prototype.UndergroundBelt, 2)
print("Crafted 2 underground belts")

"""
Step 6: Craft fast-underground-belt
"""
craft_item(Prototype.FastUndergroundBelt, 1)
print("Crafted 1 fast-underground-belt")

"""
Step 7: Verify crafting
"""
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, "Failed to craft fast-underground-belt"
print("Successfully crafted fast-underground-belt")

