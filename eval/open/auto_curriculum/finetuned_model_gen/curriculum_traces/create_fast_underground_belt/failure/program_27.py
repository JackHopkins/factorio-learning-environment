
from instance import *

"""
Step 1: Craft a stone furnace
"""
# Gather stone for furnace
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=5)

# Craft stone furnace
craft_item(Prototype.StoneFurnace, 1)

# Verify we have the furnace
furnace_in_inventory = inspect_inventory().get(Prototype.StoneFurnace, 0)
assert furnace_in_inventory >= 1, "Failed to craft stone furnace"

"""
Step 2: Place and set up the furnace
"""
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=2, y=0))

"""
Step 3: Gather and smelt iron plates
"""
# Gather iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=60)

# Gather coal for fuel
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=30)

# Move to furnace and add fuel
move_to(furnace.position)
insert_item(Prototype.Coal, furnace, quantity=15)

# Smelt iron plates
insert_item(Prototype.IronOre, furnace, quantity=30)
sleep(10)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=30)

# Verify we have enough iron plates
iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
assert iron_plates >= 30, f"Failed to smelt enough iron plates, only have {iron_plates}"

"""
Step 4: Craft iron gear wheels
"""
craft_item(Prototype.IronGearWheel, 20)

# Verify we have iron gear wheels
gear_count = inspect_inventory().get(Prototype.IronGearWheel, 0)
assert gear_count >= 20, f"Failed to craft enough iron gear wheels, only have {gear_count}"

"""
Step 5: Craft underground belts
"""
craft_item(Prototype.UndergroundBelt, 2)

# Verify we have underground belts
underground_belt_count = inspect_inventory().get(Prototype.UndergroundBelt, 0)
assert underground_belt_count >= 2, f"Failed to craft enough underground belts, only have {underground_belt_count}"

"""
Step 6: Craft fast-underground-belt
"""
craft_item(Prototype.FastUndergroundBelt, 1)

# Verify we have fast-underground-belt
fast_underground_belt_count = inspect_inventory().get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belt_count >= 1, f"Failed to craft fast-underground-belt, only have {fast_underground_belt_count}"

print("Successfully crafted fast-underground-belt!")
