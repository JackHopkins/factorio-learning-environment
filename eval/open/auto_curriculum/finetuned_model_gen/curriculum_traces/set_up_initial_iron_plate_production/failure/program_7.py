
from instance import *

"""
Step 1: Craft and place stone furnace
- Crafting requires 5 stone
"""
# Mine stone for stone furnace
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=5)

# Verify we have enough stone
inventory = inspect_inventory()
assert inventory.get(Prototype.Stone) >= 5, "Failed to mine enough stone for furnace"

# Craft stone furnace
craft_item(Prototype.StoneFurnace, 1)

# Verify we have stone furnace in inventory
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace) >= 1, "Failed to craft stone furnace"

# Place furnace near player position
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=2))
assert furnace is not None, "Failed to place furnace"

"""
Step 2: Gather resources
- Mine coal for fuel
- Mine iron ore
"""
# Mine coal
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=5)

# Verify we have coal
inventory = inspect_inventory()
assert inventory.get(Prototype.Coal) >= 5, "Failed to mine enough coal"

# Mine iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=10)

# Verify we have iron ore
inventory = inspect_inventory()
assert inventory.get(Prototype.IronOre) >= 10, "Failed to mine enough iron ore"

"""
Step 3: Set up iron smelting
- Insert fuel into the furnace
- Insert iron ore into the furnace
"""
# Move back to furnace
move_to(furnace.position)

# Insert coal as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=5)
assert updated_furnace.fuel.get(Prototype.Coal) >= 5, "Failed to insert coal into furnace"

# Insert iron ore
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=10)
assert updated_furnace.furnace_source.get(Prototype.IronOre) >= 10, "Failed to insert iron ore into furnace"

"""
Step 4: Wait for smelting and collect iron plates
"""
# Wait for smelting (10 iron ore * 3.5 seconds per ore = 35 seconds)
sleep(35)

# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=10)
    inventory = inspect_inventory()
    if inventory.get(Prototype.IronPlate) >= 10:
        break
    sleep(5)

# Final verification
assert inventory.get(Prototype.IronPlate) >= 10, f"Failed to produce enough iron plates. Current count: {inventory.get(Prototype.IronPlate)}"

print(f"Successfully produced {inventory.get(Prototype.IronPlate)} iron plates!")
