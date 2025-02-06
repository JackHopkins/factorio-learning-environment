
from instance import *

"""
Step 1: Gather initial resources
- Gather 12 stone (5 for stone furnace, 7 for burner-mining-drill)
- Gather 2 coal (for fueling the furnace)
- Gather 31 iron ore (18 for iron plates, 14 for burner-mining-drill)
"""
# Gather stone
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=12)
inventory = inspect_inventory()
assert inventory.get(Prototype.Stone) >= 12, "Failed to gather enough stone"

# Gather coal
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=2)
inventory = inspect_inventory()
assert inventory.get(Prototype.Coal) >= 2, "Failed to gather enough coal"

# Gather iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=31)
inventory = inspect_inventory()
assert inventory.get(Prototype.IronOre) >= 31, "Failed to gather enough iron ore"

"""
Step 2: Craft necessary items
- Craft 1 stone-furnace
- Craft 1 burner-mining-drill
"""
# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace) >= 1, "Failed to craft stone furnace"

# Craft burner-mining-drill
craft_item(Prototype.BurnerMiningDrill, quantity=1)
inventory = inspect_inventory()
assert inventory.get(Prototype.BurnerMiningDrill) >= 1, "Failed to craft burner-mining-drill"

"""
Step 3: Set up mining and smelting
- Place the burner-mining-drill on an iron ore patch
- Place the stone-furnace next to the drill
- Fuel both the drill and the furnace with coal
"""
# Place burner-mining-drill
move_to(iron_pos)
drill = place_entity(Prototype.BurnerMiningDrill, position=iron_pos)
assert drill is not None, "Failed to place burner-mining-drill"

# Place stone-furnace
furnace = place_entity_next_to(Prototype.StoneFurnace, direction=Direction.RIGHT, reference_position=drill.position)
assert furnace is not None, "Failed to place stone-furnace"

# Fuel entities
insert_item(Prototype.Coal, drill, quantity=1)
insert_item(Prototype.Coal, furnace, quantity=1)

"""
Step 4: Smelt iron plates
- Wait for the furnace to produce 31 iron plates
"""
# Insert iron ore into furnace
insert_item(Prototype.IronOre, furnace, quantity=31)

# Wait for smelting
sleep(30)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=31)
inventory = inspect_inventory()
assert inventory.get(Prototype.IronPlate) >= 31, "Failed to smelt enough iron plates"

"""
Step 5: Craft intermediate items
- Craft 8 iron-gear-wheels
"""
craft_item(Prototype.IronGearWheel, quantity=8)
inventory = inspect_inventory()
assert inventory.get(Prototype.IronGearWheel) >= 8, "Failed to craft iron-gear-wheels"

"""
Step 6: Craft transport-belt
"""
craft_item(Prototype.TransportBelt, quantity=1)
inventory = inspect_inventory()
assert inventory.get(Prototype.TransportBelt) >= 1, "Failed to craft transport-belt"

"""
Step 7: Craft fast-transport-belt
"""
craft_item(Prototype.FastTransportBelt, quantity=1)
inventory = inspect_inventory()
assert inventory.get(Prototype.FastTransportBelt) >= 1, "Failed to craft fast-transport-belt"

print("Successfully crafted fast-transport-belt!")
