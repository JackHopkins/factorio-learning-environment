

from factorio_instance import *

"""
Objective: Craft 2 fast-underground-belts from scratch

Planning:
We need to craft 2 fast-underground-belts. Looking at the recipe for fast-underground-belt, we need the following components:
- 1 underground-belt
- 20 iron gear wheels

We need to craft 2 fast-underground-belts, so we need 2 underground-belts and 40 iron gear wheels in total.

There are no entities on the map, so we need to craft everything from scratch.
We'll need to gather raw resources, smelt them into plates, craft intermediate products (iron gear wheels and underground-belts), and then craft the final product.

Steps:
1. Gather raw resources
2. Set up smelting operation
3. Craft intermediate products
4. Craft final product
5. Verify the crafting
"""

"""
Step 1: Gather raw resources
- We need to mine iron ore, copper ore, and coal (for fuel)
- We also need to mine stone to craft a furnace
"""

# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 44),  # 40 for iron gear wheels, 4 for underground-belts
    (Resource.CopperOre, 4), # 4 for underground-belts
    (Resource.Coal, 10),     # For fueling the furnace
    (Resource.Stone, 5)      # For crafting a stone furnace
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    # Move to the resource
    move_to(resource_position)
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to harvest enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully harvested {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory after gathering resources:")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Copper Ore: {final_inventory.get(Resource.CopperOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 44, "Not enough Iron Ore"
assert final_inventory.get(Resource.CopperOre, 0) >= 4, "Not enough Copper Ore"
assert final_inventory.get(Resource.Coal, 0) >= 10, "Not enough Coal"
assert final_inventory.get(Resource.Stone, 0) >= 5, "Not enough Stone"

print("Successfully gathered all required resources!")

"""
Step 2: Set up smelting operation
- Craft a stone furnace
- Smelt iron ore into iron plates
- Smelt copper ore into copper plates
"""

# Craft a stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted a stone furnace")

# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed stone furnace at {furnace.position}")

# Add coal to the furnace as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=5)
print("Inserted coal into the furnace")

# Insert iron ore and copper ore into the furnace and smelt them in batches
for ore_type, plate_type, total_quantity in [(Prototype.IronOre, Prototype.IronPlate, 44), (Prototype.CopperOre, Prototype.CopperPlate, 4)]:
    remaining_quantity = total_quantity
    while remaining_quantity > 0:
        batch_size = min(20, remaining_quantity)  # Smelt in batches of 20 or less
        updated_furnace = insert_item(ore_type, updated_furnace, quantity=batch_size)
        sleep(5)  # Wait for smelting to complete
        extract_item(plate_type, updated_furnace.position, batch_size)
        remaining_quantity -= batch_size
        print(f"Extracted {batch_size} {plate_type}, {remaining_quantity} remaining")

# Verify we have the required number of plates
iron_plates = inspect_inventory()[Prototype.IronPlate]
copper_plates = inspect_inventory()[Prototype.CopperPlate]
print(f"Iron Plates: {iron_plates}, Copper Plates: {copper_plates}")
assert iron_plates >= 44, f"Failed to obtain required number of Iron Plates. Expected: 44, Actual: {iron_plates}"
assert copper_plates >= 4, f"Failed to obtain required number of Copper Plates. Expected: 4, Actual: {copper_plates}"
print("Successfully obtained required number of Iron and Copper Plates")

"""
Step 3: Craft intermediate products
- Craft 40 iron gear wheels
- Craft 2 underground-belts
"""

# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=40)
print("Crafted 40 iron gear wheels")

# Craft underground-belts
craft_item(Prototype.UndergroundBelt, quantity=2)
print("Crafted 2 underground-belts")

"""
Step 4: Craft final product
- Craft 2 fast-underground-belts
"""

# Craft fast-underground-belts
craft_item(Prototype.FastUndergroundBelt, quantity=2)
print("Crafted 2 fast-underground-belts")

"""
Step 5: Verify the crafting
- Check the inventory to ensure we have 2 fast-underground-belts
"""

# Check the inventory for fast-underground-belts
final_inventory = inspect_inventory()
fast_underground_belt_count = final_inventory.get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belt_count >= 2, f"Failed to craft required number of Fast Underground Belts. Expected: 2, Actual: {fast_underground_belt_count}"
print("Successfully crafted required number of Fast Underground Belts")

print("All steps completed successfully!")

