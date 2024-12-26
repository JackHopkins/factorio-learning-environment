
from factorio_instance import *

"""
Step 1: Print recipes. We need to craft iron-gear-wheels and underground-belts
"""
print("Recipes:")
print("Iron-gear-wheel: 2 iron plates")
print("Underground-belt: 1 iron gear wheel, 1 iron plate")

"""
Step 2: Gather resources. We need to mine iron ore, coal, and stone
"""
# Mine iron ore
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
iron_ore_mined = harvest_resource(iron_ore_position, quantity=86)  # 80 for iron plates, 6 for underground-belts
print(f"Mined {iron_ore_mined} iron ore")
assert iron_ore_mined >= 86, f"Failed to mine enough iron ore. Expected at least 86, but got {iron_ore_mined}"

# Mine coal
coal_position = nearest(Resource.Coal)
move_to(coal_position)
coal_mined = harvest_resource(coal_position, quantity=20)  # Extra for safety
print(f"Mined {coal_mined} coal")
assert coal_mined >= 20, f"Failed to mine enough coal. Expected at least 20, but got {coal_mined}"

# Mine stone
stone_position = nearest(Resource.Stone)
move_to(stone_position)
stone_mined = harvest_resource(stone_position, quantity=5)  # 5 stone for furnace
print(f"Mined {stone_mined} stone")
assert stone_mined >= 5, f"Failed to mine enough stone. Expected at least 5, but got {stone_mined}"

"""
Step 3: Craft and set up smelting operation
"""
# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 stone furnace")

# Place stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print("Placed stone furnace")

# Add coal to furnace as fuel
insert_item(Prototype.Coal, furnace, quantity=10)
print("Inserted coal into stone furnace")

"""
Step 4: Smelt iron plates
"""
# Insert iron ore into furnace
insert_item(Prototype.IronOre, furnace, quantity=86)
print("Inserted iron ore into stone furnace")

# Wait for smelting to complete
smelting_time = 0.7 * 86  # 0.7 seconds per iron ore for safety
sleep(smelting_time)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=86)
print("Extracted iron plates from stone furnace")

# Verify we have enough iron plates
inventory = inspect_inventory()
iron_plates = inventory.get(Prototype.IronPlate, 0)
assert iron_plates >= 86, f"Failed to obtain enough iron plates. Expected at least 86, but got {iron_plates}"

"""
Step 5: Craft iron-gear-wheels
"""
craft_item(Prototype.IronGearWheel, quantity=40)
print("Crafted 40 iron-gear-wheels")

"""
Step 6: Craft underground-belts
"""
craft_item(Prototype.UndergroundBelt, quantity=2)
print("Crafted 2 underground-belts")

"""
Step 7: Craft fast-underground-belt
"""
craft_item(Prototype.FastUndergroundBelt, quantity=1)
print("Crafted 1 fast-underground-belt")

"""
Step 8: Verify final inventory
"""
final_inventory = inspect_inventory()
fast_underground_belts = final_inventory.get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belts >= 1, f"Failed to craft fast-underground-belt. Expected at least 1, but got {fast_underground_belts}"
print("Successfully crafted fast-underground-belt")

