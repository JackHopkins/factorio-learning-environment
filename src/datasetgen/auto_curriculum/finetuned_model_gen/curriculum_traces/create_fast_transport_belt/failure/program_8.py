

from factorio_instance import *

"""
Step 1: Craft a burner mining drill
- Gather resources: stone, iron ore, coal
- Craft stone furnace and iron gear wheels
- Craft burner mining drill
"""

# Step 1: Craft a burner mining drill
# Get stone for furnaces
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=12)

# get iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=15)

# get coal
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=5)

# Craft stone furnaces
craft_item(Prototype.StoneFurnace, 2)

# Place furnace to make iron plates
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=coal_pos.x + 2, y=coal_pos.y))
insert_item(Prototype.Coal, furnace, 3)
insert_item(Prototype.IronOre, furnace, 10)

# Wait for smelting
sleep(5)

# Get iron plates
extract_item(Prototype.IronPlate, furnace.position, 10)

# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, 5)

# Craft burner mining drill
craft_item(Prototype.BurnerMiningDrill, 1)

assert inspect_inventory()[Prototype.BurnerMiningDrill] >= 1, "Failed to craft burner mining drill"

# Step 2: Place and fuel the burner mining drill
# Move to iron ore patch
iron_patch = nearest(Resource.IronOre)
move_to(iron_patch)

# Place burner mining drill
drill = place_entity(Prototype.BurnerMiningDrill, position=iron_patch, direction=Direction.DOWN)

# Fuel the burner mining drill
insert_item(Prototype.Coal, drill, 2)

# move away from the drill
move_to(Position(x=drill.position.x + 2, y=drill.position.y + 2))

"""
Step 3: Set up iron ore mining
- Place burner mining drill on iron ore patch
- Fuel the drill with coal
- Verify that iron ore is being mined
"""

# Wait for mining to start
sleep(5)

# Check drill status
drill = get_entity(Prototype.BurnerMiningDrill, drill.position)
assert drill.status != EntityStatus.NO_FUEL, "Drill is out of fuel"

# Check for iron ore in drill's output area
iron_ore_count = inspect_inventory(drill)[Prototype.IronOre]
assert iron_ore_count > 0, "No iron ore being mined"

"""
Step 4: Craft and set up smelting operation
- Craft additional stone furnace
- Place furnace near drill
- Fuel furnace with coal
- Smelt iron ore into iron plates (need at least 18 iron plates)
- Craft iron gear wheels
"""

# get stone for furnace
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=5)

# Craft additional stone furnace
craft_item(Prototype.StoneFurnace, 1)

# Place furnace near drill
drill_pos = drill.position
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=drill_pos.x + 2, y=drill_pos.y))

# Fuel the furnace
insert_item(Prototype.Coal, furnace, 2)

# Wait for iron ore to accumulate
sleep(10)

# Extract iron ore from drill
iron_ore = extract_item(Prototype.IronOre, drill.drop_position, 15)
assert iron_ore > 0, "Failed to extract iron ore"

# Insert iron ore into furnace
insert_item(Prototype.IronOre, furnace, 15)

# Wait for smelting
sleep(10)

# Extract iron plates
iron_plate_count = extract_item(Prototype.IronPlate, furnace.position, 15)
assert iron_plate_count >= 15, f"Failed to get enough iron plates; got {iron_plate_count}"

# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, 7)

"""
Step 5: Craft fast transport belt
- Craft transport belt (requires 1 iron gear wheel, 1 iron plate)
- Craft fast transport belt (requires 4 iron gear wheels, 2 transport belts)
"""

# Craft transport belt first
craft_item(Prototype.TransportBelt, 1)

# Now craft fast transport belt
craft_item(Prototype.FastTransportBelt, 1)

# Verify we have the fast transport belt
assert inspect_inventory()[Prototype.FastTransportBelt] >= 1, "Failed to craft fast transport belt"

