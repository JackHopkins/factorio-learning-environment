
from factorio_instance import *

"""
Step 1: Craft the stone furnace
- Check if stone furnace is in inventory
- If not, gather stone and craft a stone furnace
"""
# Check current inventory
inventory = inspect_inventory()
print(f"Current inventory: {inventory}")

# Check if we already have a stone furnace
if inventory.get(Prototype.StoneFurnace, 0) < 1:
    # Get stone for furnace
    stone_position = nearest(Resource.Stone)
    move_to(stone_position)
    stone_needed = 5
    harvested_stone = harvest_resource(stone_position, quantity=stone_needed)
    print(f"Harvested {harvested_stone} stone")

    # Craft stone furnace
    crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
    print(f"Crafted {crafted_furnaces} stone furnaces")

# Verify we have a stone furnace
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace) >= 1, "Failed to obtain stone furnace"
print("Successfully obtained stone furnace")

"""
Step 2: Set up the furnace
- Place the stone furnace
- Gather coal for fuel
- Gather iron ore for smelting
"""
# Place stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed stone furnace at {furnace.position}")

# Get coal for fuel
coal_position = nearest(Resource.Coal)
move_to(coal_position)
coal_needed = 10
harvested_coal = harvest_resource(coal_position, quantity=coal_needed)
print(f"Harvested {harvested_coal} coal")

# Insert coal into furnace
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=coal_needed)
print("Inserted coal into furnace")

# Get iron ore
iron_position = nearest(Resource.IronOre)
move_to(iron_position)
iron_needed = 10
harvested_iron = harvest_resource(iron_position, quantity=iron_needed)
print(f"Harvested {harvested_iron} iron ore")

# Move back to furnace and insert iron ore
move_to(updated_furnace.position)
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_needed)
print("Inserted iron ore into furnace")

"""
Step 3: Smelt iron plates
- Smelt iron plates
- Extract iron plates from the furnace
"""
# Wait for smelting to complete
smelting_time = 0.7 * iron_needed
sleep(smelting_time)

# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_needed)
    inventory = inspect_inventory()
    if inventory.get(Prototype.IronPlate, 0) >= iron_needed:
        break
    sleep(5)

print(f"Extracted iron plates; current inventory: {inventory}")

"""
Step 4: Craft steel plate
- Craft steel plate using iron plates
"""
# Craft steel plate
crafted_steel_plates = craft_item(Prototype.SteelPlate, quantity=1)
print(f"Crafted {crafted_steel_plates} steel plates")

# Verify we have crafted a steel plate
inventory = inspect_inventory()
assert inventory.get(Prototype.SteelPlate) >= 1, "Failed to craft steel plate"
print("Successfully crafted steel plate")

"""
Step 5: Craft transport belts
- Craft iron gear wheels
- Craft transport belts
"""
# Craft iron gear wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=2)
print(f"Crafted {crafted_gear_wheels} iron gear wheels")

# Craft transport belts
crafted_transport_belts = craft_item(Prototype.TransportBelt, quantity=4)
print(f"Crafted {crafted_transport_belts} transport belts")

# Verify we have crafted transport belts
inventory = inspect_inventory()
assert inventory.get(Prototype.TransportBelt) >= 4, "Failed to craft transport belts"
print("Successfully crafted transport belts")

"""
Final verification
- Check if we have all the required items
"""
inventory = inspect_inventory()
print(f"Final inventory: {inventory}")

# Check if we have all required items
assert inventory.get(Prototype.SteelPlate, 0) >= 1, "Missing steel plate"
assert inventory.get(Prototype.TransportBelt, 0) >= 4, "Missing transport belts"
assert inventory.get(Prototype.IronGearWheel, 0) >= 1, "Missing iron gear wheel"
assert inventory.get(Prototype.IronPlate, 0) >= 3, "Missing iron plates"

print("Successfully completed all tasks!")
