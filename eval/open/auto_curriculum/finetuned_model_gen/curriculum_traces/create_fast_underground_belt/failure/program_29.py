

from instance import *

"""
Objective: Craft a fast-underground-belt from raw materials

Planning:
We need to craft a fast-underground-belt, which requires 2 underground-belts and 40 iron-gear-wheels.
We have nothing in our inventory, so we need to gather all resources from scratch.
We'll need to set up a basic mining and smelting operation to get the iron plates and coal.
We'll need to craft intermediate components like iron gear wheels and underground belts.
Finally, we'll craft the fast-underground-belt.
"""

"""
Step 1: Craft and place a burner mining drill
- We need to craft a burner mining drill
- This requires 3 iron gear wheels, 3 iron plates, and 1 stone furnace
- We need to mine iron ore and stone by hand
"""

# Mine iron ore by hand
iron_ore_pos = nearest(Resource.IronOre)
move_to(iron_ore_pos)
harvest_resource(iron_ore_pos, quantity=9)
print(f"Mined iron ore. Current inventory: {inspect_inventory()}")

# Craft iron gear wheels (3)
craft_item(Prototype.IronGearWheel, quantity=3)
print(f"Crafted 3 iron gear wheels. Current inventory: {inspect_inventory()}")

# Mine stone by hand for the furnace
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=5)
print(f"Mined stone. Current inventory: {inspect_inventory()}")

# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted stone furnace. Current inventory: {inspect_inventory()}")

# Craft burner mining drill
craft_item(Prototype.BurnerMiningDrill, quantity=1)
print(f"Crafted burner mining drill. Current inventory: {inspect_inventory()}")

# Place the burner mining drill on an iron ore patch
iron_ore_pos = nearest(Resource.IronOre)
move_to(iron_ore_pos)
drill = place_entity(Prototype.BurnerMiningDrill, position=iron_ore_pos, direction=Direction.UP)
print(f"Placed burner mining drill at {drill.position}")

# Add fuel to the burner mining drill
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=5)
move_to(drill.position)
insert_item(Prototype.Coal, drill, quantity=5)
print(f"Inserted coal into burner mining drill")

# Verify that the drill is working
sleep(5)
inspection = inspect_entities(position=drill.position, radius=1)
drill_status = inspection.get_entity(Prototype.BurnerMiningDrill)
assert drill_status.status != EntityStatus.NO_FUEL, "Drill has no fuel"
print("Burner mining drill is working")

"""
Step 2: Set up a stone furnace for iron smelting
- We need to craft and place a stone furnace
- We need to mine coal for fuel
- We need to smelt iron ore into iron plates
"""

# Place the stone furnace
furnace = place_entity_next_to(Prototype.StoneFurnace, reference_position=drill.position)
print(f"Placed stone furnace at {furnace.position}")

# Mine coal for fuel
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=10)
print(f"Mined coal. Current inventory: {inspect_inventory()}")

# Add fuel to the stone furnace
move_to(furnace.position)
insert_item(Prototype.Coal, furnace, quantity=5)
print(f"Inserted coal into stone furnace")

"""
Step 3: Smelt iron plates
- We need to wait for the burner mining drill to produce iron ore
- We need to smelt the iron ore into iron plates
"""

# Wait for the burner mining drill to produce iron ore
sleep(10)

# Extract iron ore from the drill
extract_item(Prototype.IronOre, drill.position, quantity=10)
print(f"Extracted iron ore. Current inventory: {inspect_inventory()}")

# Insert iron ore into the furnace
insert_item(Prototype.IronOre, furnace, quantity=10)
print(f"Inserted iron ore into stone furnace")

# Wait for smelting
sleep(15)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=10)
print(f"Extracted iron plates. Current inventory: {inspect_inventory()}")

"""
Step 4: Craft intermediate components
- Craft 40 iron gear wheels
- Craft 2 underground belts
"""

# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=40)
print(f"Crafted 40 iron gear wheels. Current inventory: {inspect_inventory()}")

# Craft underground belts
craft_item(Prototype.UndergroundBelt, quantity=2)
print(f"Crafted 2 underground belts. Current inventory: {inspect_inventory()}")

"""
Step 5: Craft fast-underground-belt
- We need to use the crafted components to create the fast-underground-belt
"""

# Craft fast-underground-belt
craft_item(Prototype.FastUndergroundBelt, quantity=1)
print(f"Crafted fast-underground-belt. Current inventory: {inspect_inventory()}")

# Verify that we have crafted the fast-underground-belt
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, "Failed to craft fast-underground-belt"
print("Successfully crafted fast-underground-belt")

