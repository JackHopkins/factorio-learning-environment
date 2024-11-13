
from factorio_instance import *

"""
Step 1: Craft and place a stone furnace
- Need to gather stone for the furnace
- Craft the stone furnace
- Place the furnace
"""
# Get stone for the furnace
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=5)

# Verify we got the stone
inventory = inspect_inventory()
assert inventory.get(Prototype.Stone) >= 5, "Failed to get enough stone"

# Craft the stone furnace
craft_item(Prototype.StoneFurnace, 1)

# Place the furnace near player
player_pos = inspect_entities().player_position
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=player_pos[0]+2, y=player_pos[1]))

"""
Step 2: Gather resources
- Mine iron ore
- Mine coal for fuel
"""
# Get iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=10)

# Get coal
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=5)

# Verify we got the resources
inventory = inspect_inventory()
assert inventory.get(Prototype.IronOre) >= 10, "Failed to get enough iron ore"
assert inventory.get(Prototype.Coal) >= 5, "Failed to get enough coal"

"""
Step 3: Set up and operate the furnace
- Add fuel to the furnace
- Add iron ore to the furnace
- Wait for smelting and collect iron plates
"""
# Move to furnace and add fuel
move_to(furnace.position)
furnace = insert_item(Prototype.Coal, furnace, quantity=5)

# Insert iron ore and start smelting
furnace = insert_item(Prototype.IronOre, furnace, quantity=10)

# Wait for smelting
sleep(15)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=10)

# Verify we got the iron plates
inventory = inspect_inventory()
assert inventory.get(Prototype.IronPlate) >= 10, "Failed to produce enough iron plates"

print("Successfully set up initial iron plate production!")
