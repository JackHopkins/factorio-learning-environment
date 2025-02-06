
from instance import *

"""
Step 1: Gather resources
- Mine 12 stone
- Mine at least 80 iron ore
- Mine some coal for fuel
"""
# Move to the nearest stone patch and mine stone
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=12)

# Move to the nearest iron ore patch and mine iron ore
iron_position = nearest(Resource.IronOre)
move_to(iron_position)
harvest_resource(iron_position, quantity=80)

# Move to the nearest coal patch and mine coal
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, quantity=20)  # Get some extra coal for fuel

# Verify that we have gathered the required resources
inventory = inspect_inventory()
assert inventory.get(Resource.Stone, 0) >= 12, f"Failed to gather enough stone. Current inventory: {inventory}"
assert inventory.get(Resource.IronOre, 0) >= 80, f"Failed to gather enough iron ore. Current inventory: {inventory}"
assert inventory.get(Resource.Coal, 0) >= 20, f"Failed to gather enough coal. Current inventory: {inventory}"

print(f"Successfully gathered resources. Current inventory: {inventory}")

"""
Step 2: Craft 2 stone furnaces
- Craft 2 stone furnaces using 10 stone
"""
# Craft 2 stone furnaces
craft_item(Prototype.StoneFurnace, quantity=2)

# Verify that we have crafted 2 stone furnaces
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace, 0) >= 2, f"Failed to craft 2 stone furnaces. Current inventory: {inventory}"

print(f"Successfully crafted 2 stone furnaces. Current inventory: {inventory}")

"""
Step 3: Set up iron plate production
- Place one stone furnace
- Add coal to the furnace as fuel
- Smelt 80 iron ore into 80 iron plates
"""
# Place the first stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)

# Add coal to the furnace as fuel
insert_item(Prototype.Coal, furnace, quantity=10)

# Smelt iron ore into iron plates
insert_item(Prototype.IronOre, furnace, quantity=80)

# Wait for smelting to complete (approximately 56 seconds for 80 iron ore)
sleep(56)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=80)

# Verify that we have 80 iron plates
inventory = inspect_inventory()
assert inventory.get(Prototype.IronPlate, 0) >= 80, f"Failed to smelt 80 iron plates. Current inventory: {inventory}"

print(f"Successfully set up iron plate production. Current inventory: {inventory}")

"""
Step 4: Craft iron gear wheels
- Use the second stone furnace to craft 40 iron gear wheels (2 iron plates per gear wheel, so 80 iron plates total)
"""
# Move to the second stone furnace
second_furnace_pos = Position(x=2, y=0)  # Assume we placed it at x=2, y=0
move_to(second_furnace_pos)

# Place the second stone furnace
second_furnace = place_entity(Prototype.StoneFurnace, position=second_furnace_pos)

# Add coal to the second furnace as fuel
insert_item(Prototype.Coal, second_furnace, quantity=10)

# Craft 40 iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=40)

# Verify that we have crafted 40 iron gear wheels
inventory = inspect_inventory()
assert inventory.get(Prototype.IronGearWheel, 0) >= 40, f"Failed to craft 40 iron gear wheels. Current inventory: {inventory}"

print(f"Successfully crafted 40 iron gear wheels. Current inventory: {inventory}")

"""
Step 5: Craft an underground-belt
- Use 10 iron gear wheels to craft an underground-belt
"""
# Craft 1 underground-belt
craft_item(Prototype.UndergroundBelt, quantity=1)

# Verify that we have crafted 1 underground-belt
inventory = inspect_inventory()
assert inventory.get(Prototype.UndergroundBelt, 0) >= 1, f"Failed to craft 1 underground-belt. Current inventory: {inventory}"

print(f"Successfully crafted 1 underground-belt. Current inventory: {inventory}")

"""
Step 6: Craft a fast-underground-belt
- Use the underground-belt and 40 iron gear wheels to craft a fast-underground-belt
"""
# Craft 1 fast-underground-belt
craft_item(Prototype.FastUndergroundBelt, quantity=1)

# Verify that we have crafted 1 fast-underground-belt
inventory = inspect_inventory()
assert inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, f"Failed to craft 1 fast-underground-belt. Current inventory: {inventory}"

print(f"Successfully crafted 1 fast-underground-belt. Current inventory: {inventory}")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

