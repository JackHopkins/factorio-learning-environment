

from instance import *

"""
Step 1: Craft a stone furnace
"""
# Get stone for the furnace
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=5)

# Craft the stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)

# Verify that we have the stone furnace
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace) >= 1, "Failed to craft stone furnace"

"""
Step 2: Mine resources
"""
# Mine iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=98)

# Mine coal
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=7)

"""
Step 3: Set up smelting
"""
# Place the stone furnace near the coal patch
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=coal_pos.x+2, y=coal_pos.y))

# Insert coal into the furnace
insert_item(Prototype.Coal, furnace, quantity=7)

# Insert iron ore into the furnace
insert_item(Prototype.IronOre, furnace, quantity=98)

# Wait for smelting to complete
sleep(50)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=98)

# Verify that we have the iron plates
inventory = inspect_inventory()
assert inventory.get(Prototype.IronPlate) >= 98, "Failed to obtain required amount of iron plates"

"""
Step 4: Craft fast-underground-belt
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=40)

# Craft underground belts (each requires 5 iron gear wheels and 10 iron plates)
craft_item(Prototype.UndergroundBelt, quantity=2)

# Craft fast-underground-belt (requires 2 underground belts and 40 iron gear wheels)
craft_item(Prototype.FastUndergroundBelt, quantity=1)

# Verify that we have the fast-underground-belt
inventory = inspect_inventory()
assert inventory.get(Prototype.FastUndergroundBelt) >= 1, "Failed to craft fast-underground-belt"

print("Successfully crafted fast-underground-belt!")

