

from instance import *

"""
Step 1: Craft stone furnace
- We need to craft a stone furnace as we have none in our inventory or on the map
- A stone furnace requires 5 stone to craft
"""
# Print recipe for stone furnace
print("Stone Furnace Recipe: 5 stone")

# Check current inventory for stone
inventory = inspect_inventory()
stone_needed = max(5 - inventory.get(Prototype.Stone, 0), 0)

# Mine stone if needed
if stone_needed > 0:
    stone_position = nearest(Resource.Stone)
    move_to(stone_position)
    harvest_resource(stone_position, quantity=stone_needed)

# Verify we have enough stone
inventory = inspect_inventory()
assert inventory.get(Prototype.Stone) >= 5, f"Failed to gather enough stone. Current inventory: {inventory}"

# Craft the stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)

# Verify we have the stone furnace
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace) >= 1, f"Failed to craft stone furnace. Current inventory: {inventory}"

print("Successfully crafted a stone furnace")
print(f"Current inventory: {inventory}")


"""
Step 2: Set up iron smelting
- Place the stone furnace
- Mine 98 iron ore
- Smelt iron ore into iron plates
"""
# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)

# Mine iron ore
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
harvest_resource(iron_ore_position, quantity=98)

# Get coal for fuel
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, quantity=20)  # Get extra coal for safety

# Move back to the furnace and insert materials
move_to(furnace.position)
insert_item(Prototype.Coal, furnace, quantity=10)
insert_item(Prototype.IronOre, furnace, quantity=98)

# Wait for smelting
smelting_time = 98 * 0.7  # 0.7 seconds per iron plate
sleep(smelting_time)

# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, furnace.position, quantity=98)
    inventory = inspect_inventory()
    if inventory.get(Prototype.IronPlate) >= 98:
        break
    sleep(10)  # Allow more time if needed

# Final verification
inventory = inspect_inventory()
assert inventory.get(Prototype.IronPlate) >= 98, f"Failed to obtain required iron plates. Current inventory: {inventory}"

print("Successfully set up iron smelting and obtained 98 iron plates")
print(f"Current inventory: {inventory}")


"""
Step 3: Craft iron gear wheels
- Use 40 iron plates to craft 40 iron gear wheels
"""
# Print recipe for iron gear wheels
print("Iron Gear Wheel Recipe: 2 iron plates per wheel")

# Check current inventory for iron plates
inventory = inspect_inventory()
iron_plates_needed = max(80 - inventory.get(Prototype.IronPlate, 0), 0)

# Verify we have enough iron plates
assert inventory.get(Prototype.IronPlate) >= 80, f"Not enough iron plates. Current inventory: {inventory}"

# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=40)

# Verify we have the iron gear wheels
inventory = inspect_inventory()
assert inventory.get(Prototype.IronGearWheel) >= 40, f"Failed to craft iron gear wheels. Current inventory: {inventory}"

print("Successfully crafted 40 iron gear wheels")
print(f"Current inventory: {inventory}")


"""
Step 4: Craft underground belt
- Use 20 iron gear wheels and 20 iron plates to craft 2 underground belts
"""
# Print recipe for underground belt
print("Underground Belt Recipe: 10 iron gear wheels, 10 iron plates per belt")

# Check current inventory for required items
inventory = inspect_inventory()
iron_gear_wheels_needed = max(20 - inventory.get(Prototype.IronGearWheel, 0), 0)
iron_plates_needed = max(20 - inventory.get(Prototype.IronPlate, 0), 0)

# Verify we have enough materials
assert inventory.get(Prototype.IronGearWheel) >= 20, f"Not enough iron gear wheels. Current inventory: {inventory}"
assert inventory.get(Prototype.IronPlate) >= 20, f"Not enough iron plates. Current inventory: {inventory}"

# Craft underground belts
craft_item(Prototype.UndergroundBelt, quantity=2)

# Verify we have the underground belts
inventory = inspect_inventory()
assert inventory.get(Prototype.UndergroundBelt) >= 2, f"Failed to craft underground belts. Current inventory: {inventory}"

print("Successfully crafted 2 underground belts")
print(f"Current inventory: {inventory}")


"""
Step 5: Craft fast underground belt
- Use 20 iron gear wheels and 1 underground belt to craft 1 fast underground belt
"""
# Print recipe for fast underground belt
print("Fast Underground Belt Recipe: 10 iron gear wheels, 1 underground belt per belt")

# Check current inventory for required items
inventory = inspect_inventory()
iron_gear_wheels_needed = max(10 - inventory.get(Prototype.IronGearWheel, 0), 0)
underground_belts_needed = max(1 - inventory.get(Prototype.UndergroundBelt, 0), 0)

# Verify we have enough materials
assert inventory.get(Prototype.IronGearWheel) >= 10, f"Not enough iron gear wheels. Current inventory: {inventory}"
assert inventory.get(Prototype.UndergroundBelt) >= 1, f"Not enough underground belts. Current inventory: {inventory}"

# Craft fast underground belt
craft_item(Prototype.FastUndergroundBelt, quantity=1)

# Verify we have the fast underground belt
inventory = inspect_inventory()
assert inventory.get(Prototype.FastUndergroundBelt) >= 1, f"Failed to craft fast underground belt. Current inventory: {inventory}"

print("Successfully crafted 1 fast underground belt")
print(f"Current inventory: {inventory}")

