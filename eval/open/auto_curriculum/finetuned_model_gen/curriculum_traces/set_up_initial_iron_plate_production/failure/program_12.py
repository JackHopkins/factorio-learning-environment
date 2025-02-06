

from instance import *

"""
Step 1: Craft and place a stone furnace
"""
# Move to origin
move_to(Position(x=0, y=0))

# Mine stone for furnace
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=5)

# Craft stone furnace
craft_item(Prototype.StoneFurnace, 1)

# Place stone furnace
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=2))

"""
Step 2: Gather resources
"""
# Mine coal
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=10)

# Mine iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=10)

"""
Step 3: Set up and operate the furnace
"""
# Move back to furnace
move_to(furnace.position)

# Insert coal as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=5)

# Insert iron ore for smelting
insert_item(Prototype.IronOre, updated_furnace, quantity=10)

# Wait for smelting
sleep(10)

"""
Step 4: Extract and verify iron plates
"""
# Extract iron plates
extract_item(Prototype.IronPlate, updated_furnace.position, quantity=10)

# Verify production
inventory = inspect_inventory()
iron_plates = inventory.get(Prototype.IronPlate, 0)
assert iron_plates >= 5, f"Failed to produce enough iron plates. Only produced {iron_plates}"
