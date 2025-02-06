

from instance import *

"""
Step 1: Gather resources
"""
# Get stone for furnace
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=12)

# Get iron ore for plates
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=31)

# Get coal for fuel
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=2)

"""
Step 2: Craft and place stone furnace
"""
# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)

# Place furnace near player
player_pos = inspect_entities().player_position
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=player_pos[0]+2, y=player_pos[1]))

"""
Step 3: Set up burner mining drill
"""
# Craft burner mining drill
craft_item(Prototype.BurnerMiningDrill, quantity=1)

# Place drill on iron patch
drill = place_entity(Prototype.BurnerMiningDrill, position=iron_pos)

# Fuel drill
insert_item(Prototype.Coal, drill, quantity=1)

"""
Step 4: Smelt iron plates
"""
# Move to furnace and fuel it
move_to(furnace.position)
insert_item(Prototype.Coal, furnace, quantity=1)

# Insert iron ore
insert_item(Prototype.IronOre, furnace, quantity=31)

# Wait for smelting
sleep(15)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=31)

"""
Step 5: Craft components
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=8)

# Craft transport belt
craft_item(Prototype.TransportBelt, quantity=1)

"""
Step 6: Craft fast-transport-belt
"""
craft_item(Prototype.FastTransportBelt, quantity=1)

"""
Step 7: Verify crafting
"""
inventory = inspect_inventory()
assert inventory.get(Prototype.FastTransportBelt) >= 1, "Failed to craft fast-transport-belt"

print("Successfully crafted fast-transport-belt!")

