
from factorio_instance import *

"""
Step 1: Gather iron ore and smelt it into iron plates
"""
# We need 40 iron gear wheels and 2 underground belts
# Each gear wheel requires 2 iron plates, each underground belt requires 4 iron plates
# Total iron plates needed: (40 * 2) + (2 * 4) = 88
# Let's mine some extra iron ore to be safe

iron_ore_needed = 100
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
print(f"Moved to iron ore patch at {iron_ore_position}")

# Mine iron ore
iron_ore_mined = harvest_resource(iron_ore_position, iron_ore_needed)
print(f"Mined {iron_ore_mined} iron ore")

# Check if we need to craft a furnace
inventory = inspect_inventory() 
if inventory.get(Prototype.StoneFurnace, 0) == 0:
    # Get stone for furnace
    stone_position = nearest(Resource.Stone)
    move_to(stone_position)
    harvest_resource(stone_position, 5)
    craft_item(Prototype.StoneFurnace, 1) 

# Place furnace and smelt iron plates
player_pos = inspect_entities().player_position
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=player_pos[0]+1, y=player_pos[1]))
insert_item(Prototype.Coal, furnace, quantity=50)
insert_item(Prototype.IronOre, furnace, quantity=iron_ore_mined)
sleep(30)

# Extract iron plates
iron_plates = extract_item(Prototype.IronPlate, furnace.position, quantity=88)
print(f"Extracted {iron_plates} iron plates")
assert iron_plates >= 88, f"Failed to get enough iron plates, only got {iron_plates}"

"""
Step 2: Craft iron gear wheels
"""
craft_item(Prototype.IronGearWheel, 40)
print("Crafted 40 iron gear wheels")

"""
Step 3: Craft underground belts
"""
craft_item(Prototype.UndergroundBelt, 2)
print("Crafted 2 underground belts")

"""
Step 4: Craft fast-underground-belt
"""
craft_item(Prototype.FastUndergroundBelt, 1)
print("Crafted 1 fast-underground-belt")

# Verify final inventory
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, "Failed to craft fast-underground-belt"
print("Successfully crafted fast-underground-belt")
