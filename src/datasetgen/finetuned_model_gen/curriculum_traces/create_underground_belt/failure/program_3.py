

from factorio_instance import *

"""
Planning:

1. Gather initial resources:
   - Mine iron ore and stone
   - Craft stone furnaces
   - Craft burner mining drills and burner inserters

2. Set up iron plate production:
   - Place burner mining drill on iron ore patch
   - Place stone furnace
   - Place burner inserter to feed furnace
   - Fuel all machines
   - Start producing iron plates

3. Craft intermediate products:
   - Craft iron gear wheels
   - Craft transport belts

4. Craft underground-belt
"""

"""
Step 1: Gather initial resources and set up production
"""
# Gather stone for furnaces
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=12)

# Craft stone furnaces
craft_item(Prototype.StoneFurnace, quantity=2)

# Gather coal for fuel
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=20)  # Get extra for fueling machines

# Gather iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=40)

# Craft burner mining drill
craft_item(Prototype.BurnerMiningDrill, quantity=1)

# Craft burner inserter
craft_item(Prototype.BurnerInserter, quantity=1)

# Place and fuel burner mining drill
drill = place_entity(Prototype.BurnerMiningDrill, position=iron_pos, direction=Direction.DOWN)
insert_item(Prototype.Coal, drill, quantity=10)

# Place and fuel furnace
furnace = place_entity_next_to(Prototype.StoneFurnace, reference_position=drill.position, direction=Direction.DOWN, spacing=2)
insert_item(Prototype.Coal, furnace, quantity=5)

# Place and fuel inserter
inserter = place_entity_next_to(Prototype.BurnerInserter, reference_position=furnace.position, direction=Direction.RIGHT)
rotate_entity(inserter, Direction.LEFT)
insert_item(Prototype.Coal, inserter, quantity=5)

# Connect drill to furnace with transport belt
connect_entities(drill.drop_position, inserter.pickup_position, Prototype.TransportBelt)

"""
Step 2: Produce iron plates
"""
# Wait for initial iron plate production
sleep(10)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=40)

"""
Step 3: Craft intermediate products
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=10)

# Craft transport belts
craft_item(Prototype.TransportBelt, quantity=4)

"""
Step 4: Craft underground-belt
"""
craft_item(Prototype.UndergroundBelt, quantity=1)

# Check final inventory
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.UndergroundBelt, 0) >= 1, "Failed to craft underground-belt"
print("Successfully crafted underground-belt")

