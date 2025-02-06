Sure! Here's a policy to achieve the objective of creating a fast-underground-belt

"""
To craft a fast-underground-belt, we need 2 iron gear wheels and 2 underground belts.
There are no entities on the map or in our inventory, so we need to craft everything from scratch.

1) We need to craft the following items:
- 2 iron gear wheels
- 2 underground belts
- 1 fast-underground-belt
2) We need to craft and place the following entities:
- burner mining drill
- stone furnace
3) We need to gather the following resources:
- iron ore
- coal
- stone for furnace
4) We need to smelt the iron ore into iron plates
5) We need to craft the intermediate products (iron gear wheels, underground belts)
6) We need to craft the final product (fast-underground-belt)
"""
from instance import *

"""
Step 1: Craft necessary entities
- We need to craft a burner mining drill and a stone furnace
- We need to gather resources for crafting and smelting
"""
# Get stone for furnace
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=5)

# Craft stone furnace
craft_item(Prototype.StoneFurnace, 1)

# Get iron for drill
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=10)

# Get coal for fuel
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=10)

# Craft burner mining drill (requires 3 iron gear wheels, 3 iron plates)
craft_item(Prototype.IronGearWheel, 3)
craft_item(Prototype.BurnerMiningDrill, 1)

"""
Step 2: Set up mining and smelting operations
- Place the burner mining drill on an iron ore patch
- Place the stone furnace next to the drill
- Connect them with an inserter
"""
# Place drill on iron patch
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
drill = place_entity(Prototype.BurnerMiningDrill, position=iron_pos)
assert drill, "Failed to place burner mining drill"

# Place furnace next to drill
furnace = place_entity_next_to(Prototype.StoneFurnace, reference_position=drill.position, direction=Direction.RIGHT)
assert furnace, "Failed to place stone furnace"

# Connect with inserter
inserter = place_entity_next_to(Prototype.BurnerInserter, reference_position=furnace.position, direction=Direction.RIGHT)
assert inserter, "Failed to place inserter"

# Rotate inserter to put items into furnace
inserter = rotate_entity(inserter, Direction.LEFT)

# Fuel both entities
insert_item(Prototype.Coal, drill, 5)
insert_item(Prototype.Coal, furnace, 5)

"""
Step 3: Gather resources
- Mine iron ore and coal
- Smelt iron plates
"""
# Wait for smelting
sleep(10)

# Collect iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=10)
iron_plates = inspect_inventory()[Prototype.IronPlate]
assert iron_plates >= 10, f"Failed to gather enough iron plates. Expected at least 10, got {iron_plates}"

"""
Step 4: Craft intermediate products
- Craft 2 iron gear wheels
- Craft 2 underground belts
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, 2)

# Craft underground belts
craft_item(Prototype.UndergroundBelt, 2)

"""
Step 5: Craft fast-underground-belt
- Use the crafted materials to make a fast-underground-belt
"""
# Craft fast-underground-belt
craft_item(Prototype.FastUndergroundBelt, 1)

# Check if we have the fast-underground-belt
inventory = inspect_inventory()
assert inventory[Prototype.FastUndergroundBelt] >= 1, "Failed to craft fast-underground-belt"

print("Successfully crafted a fast-underground-belt!")
print(f"Final inventory: {inventory}")

"""
This script takes into account the recipes and resources needed for crafting a fast-underground-belt from scratch. 
It follows the steps of gathering resources, setting up mining and smelting operations, crafting intermediate products, and finally crafting the fast-underground-belt.
"""
