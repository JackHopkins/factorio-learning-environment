
from factorio_instance import *

"""
Step 1: Set up temporary mining and smelting operation
- Craft and place a burner mining drill and stone furnace
- Mine and smelt iron plates
"""
# Get stone for furnace
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=5)

# Craft stone furnace
craft_item(Prototype.StoneFurnace, 1)

# Get iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=20)

# Get coal for fuel
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=10)

# Place furnace near iron ore
move_to(Position(x=iron_pos.x+2, y=iron_pos.y))
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=iron_pos.x+2, y=iron_pos.y))

# Start smelting iron plates
insert_item(Prototype.Coal, furnace, 5)
insert_item(Prototype.IronOre, furnace, 10)

# Wait for smelting
sleep(10)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, 10)

"""
Step 2: Craft assembling machine for iron gear wheels
- Craft and place an assembling machine
"""
# Get more iron plates for assembling machine
insert_item(Prototype.Coal, furnace, 5)
insert_item(Prototype.IronOre, furnace, 10)
sleep(10)
extract_item(Prototype.IronPlate, furnace.position, 10)

# Craft assembling machine (requires 3 iron gear wheels and 5 iron plates)
craft_item(Prototype.IronGearWheel, 3)
craft_item(Prototype.AssemblingMachine1, 1)

# Place assembling machine
move_to(Position(x=0, y=0))
assembler = place_entity(Prototype.AssemblingMachine1, position=Position(x=0, y=0))

"""
Step 3: Craft intermediate products
- Craft iron gear wheels
- Craft underground-belts
"""
# Set recipe for iron gear wheels
set_entity_recipe(assembler, Prototype.IronGearWheel)

# Craft iron gear wheels (20 needed for 2 underground-belts, 20 for fast-underground-belt)
craft_item(Prototype.IronGearWheel, 40)

# Craft underground-belts (requires 1 iron gear wheel and 1 iron plate each)
craft_item(Prototype.TransportBelt, 2)

"""
Step 4: Craft fast-underground-belt
- Use the crafted underground-belts and iron gear wheels to craft the fast-underground-belt
"""
# Craft fast-underground-belt
craft_item(Prototype.FastUndergroundBelt, 1)

# Verify we have the fast-underground-belt
inventory = inspect_inventory()
assert inventory.get(Prototype.FastUndergroundBelt) >= 1, "Failed to craft fast-underground-belt"

print("Successfully crafted fast-underground-belt!")
