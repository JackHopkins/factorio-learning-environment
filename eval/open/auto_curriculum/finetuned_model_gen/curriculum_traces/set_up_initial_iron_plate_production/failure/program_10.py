
from instance import *

"""
Step 1: Craft and place furnace
- Craft 1 stone furnace from 5 stone
- Place furnace at origin
"""
# Get stone for furnace
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=5)

# Craft stone furnace
craft_item(Prototype.StoneFurnace, 1)

# Place furnace at origin
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed furnace at {furnace.position}")

"""
Step 2: Gather resources
- Mine at least 10 iron ore by hand
- Mine at least 10 coal for fuel
"""
# Get iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvested_iron = harvest_resource(iron_pos, quantity=10)
print(f"Harvested {harvested_iron} iron ore")

# Get coal
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvested_coal = harvest_resource(coal_pos, quantity=10)
print(f"Harvested {harvested_coal} coal")

"""
Step 3: Set up smelting
- Insert coal into furnace as fuel
- Insert iron ore into furnace
"""
# Move back to furnace
move_to(furnace.position)

# Insert coal as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=10)
print("Inserted coal into furnace")

# Insert iron ore
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=10)
print("Inserted iron ore into furnace")

"""
Step 4: Produce iron plates
- Wait for approximately 7 seconds for smelting (0.7 seconds per plate)
- Extract iron plates from furnace
- Verify at least 10 iron plates were produced
"""
sleep(7)

# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=10)
    inventory = inspect_inventory()
    iron_plates = inventory.get(Prototype.IronPlate, 0)
    if iron_plates >= 10:
        break
    sleep(2)

print(f"Extracted iron plates, current inventory count: {iron_plates}")

# Final verification
inventory = inspect_inventory()
iron_plates = inventory.get(Prototype.IronPlate, 0)
assert iron_plates >= 10, f"Failed to produce required iron plates! Only have {iron_plates}"
print(f"Successfully produced {iron_plates} iron plates")

