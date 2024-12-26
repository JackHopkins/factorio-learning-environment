

from factorio_instance import *

"""
Objective: Create fast-transport-belt

Planning:
We need to create a fast-transport-belt from scratch. We have no items in our inventory or on the map, so we need to gather all resources and craft all necessary items.
We'll need to craft some intermediate items and set up some basic production.
"""

"""
Step 1: Print recipe for fast-transport-belt
"""
print("Recipe for fast-transport-belt:")
print("fast-transport-belt requires 1 iron gear wheel and 1 transport belt")

"""
Step 2: Craft stone-furnace
- Mine 5 stone
- Craft 1 stone-furnace
"""
# Mine stone
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=5)

# Craft stone-furnace
craft_item(Prototype.StoneFurnace, quantity=1)

# Verify we have the stone-furnace
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace) >= 1, "Failed to craft stone-furnace"

"""
Step 3: Set up iron plate production
- Place the stone-furnace
- Mine 10 coal for fuel
- Mine 20 iron ore
- Insert coal and iron ore into the stone-furnace
- Wait for smelting and extract 20 iron plates
"""
# Place the furnace
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))

# Mine coal
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, quantity=10)

# Mine iron ore
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
harvest_resource(iron_ore_position, quantity=20)

# Insert coal and iron ore into the furnace
insert_item(Prototype.Coal, furnace, quantity=5)
insert_item(Prototype.IronOre, furnace, quantity=20)

# Wait for smelting
sleep(10)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=20)

# Verify we have the iron plates
inventory = inspect_inventory()
assert inventory.get(Prototype.IronPlate) >= 20, "Failed to produce iron plates"

"""
Step 4: Craft burner-mining-drill
- Print recipe for burner-mining-drill
- Craft 3 iron gear wheels
- Craft 1 stone-furnace
- Craft 1 burner-mining-drill
"""
# Print recipe for burner-mining-drill
print("Recipe for burner-mining-drill:")
print("burner-mining-drill requires 3 iron gear wheels, 1 stone furnace, 3 iron plates")

# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=3)

# Craft stone-furnace
craft_item(Prototype.StoneFurnace, quantity=1)

# Craft burner-mining-drill
craft_item(Prototype.BurnerMiningDrill, quantity=1)

# Verify we have the burner-mining-drill
inventory = inspect_inventory()
assert inventory.get(Prototype.BurnerMiningDrill) >= 1, "Failed to craft burner-mining-drill"

"""
Step 5: Set up automated iron mining
- Place the burner-mining-drill on iron ore patch
- Insert coal into the burner-mining-drill as fuel
"""
# Place the burner-mining-drill
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
drill = place_entity(Prototype.BurnerMiningDrill, position=iron_ore_position)

# Insert coal into the drill
insert_item(Prototype.Coal, drill, quantity=5)

"""
Step 6: Craft iron gear wheels
- Wait for the burner-mining-drill to mine iron ore
- Gather mined iron ore
- Smelt iron ore into iron plates (need at least 6 iron plates)
- Craft 3 iron gear wheels
"""
# Wait for mining
sleep(10)

# Gather mined iron ore
move_to(drill.position)
iron_ore_mined = extract_item(Prototype.IronOre, drill.position, quantity=10)

# Smelt into iron plates
insert_item(Prototype.IronOre, furnace, quantity=iron_ore_mined)
sleep(5)
extract_item(Prototype.IronPlate, furnace.position, quantity=iron_ore_mined)

# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=3)

# Verify we have the iron gear wheels
inventory = inspect_inventory()
assert inventory.get(Prototype.IronGearWheel) >= 3, "Failed to craft iron gear wheels"

"""
Step 7: Craft transport-belt
- Print recipe for transport-belt
- Craft 1 transport-belt
"""
# Print recipe for transport-belt
print("Recipe for transport-belt:")
print("transport-belt requires 1 iron gear wheel, 1 iron plate")

# Craft transport-belt
craft_item(Prototype.TransportBelt, quantity=1)

# Verify we have the transport-belt
inventory = inspect_inventory()
assert inventory.get(Prototype.TransportBelt) >= 1, "Failed to craft transport-belt"

"""
Step 8: Craft fast-transport-belt
- Craft 1 fast-transport-belt
"""
# Craft fast-transport-belt
craft_item(Prototype.FastTransportBelt, quantity=1)

# Verify we have the fast-transport-belt
inventory = inspect_inventory()
assert inventory.get(Prototype.FastTransportBelt) >= 1, "Failed to craft fast-transport-belt"

print("Successfully crafted fast-transport-belt")

