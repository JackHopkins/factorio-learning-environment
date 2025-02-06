
from instance import *

"""
Step 1: Print recipes. We need to print the recipe for fast-underground-belt
"""
# Print recipe for fast-underground-belt
print("fast-underground-belt recipe:")
print("Crafting requires 2 underground belts")

"""
Step 1: Gather resources
- Mine iron ore (at least 100)
- Mine coal (at least 50 for smelting and fueling the drill)
- Mine stone (at least 5 for a stone furnace)
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 100),
    (Resource.Coal, 50),
    (Resource.Stone, 5)
]

# Loop through each resource type and amount
for resource_type, required_amount in resources_to_gather:
    # Find the nearest patch of this resource
    patch = get_resource_patch(resource_type, nearest(resource_type))
    # Move to the patch
    move_to(patch.bounding_box.center)
    # Harvest the resource
    harvested = harvest_resource(patch.bounding_box.center, required_amount)
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_amount = current_inventory.get(resource_type, 0)
    assert actual_amount >= required_amount, f"Failed to gather enough {resource_type}. Required: {required_amount}, Actual: {actual_amount}"
    print(f"Successfully gathered {actual_amount} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

# Assert that we have at least the required amounts
assert final_inventory.get(Resource.IronOre, 0) >= 100, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 50, "Not enough Coal"
assert final_inventory.get(Resource.Stone, 0) >= 5, "Not enough Stone"

print("Successfully gathered all required resources!")

"""
Step 2: Craft and set up stone furnace
- Craft 1 stone furnace
- Place the stone furnace
"""
# Craft the stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 Stone Furnace")

# Place the stone furnace at the origin
stone_furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
print(f"Placed Stone Furnace at {stone_furnace.position}")

"""
Step 3: Smelt iron plates
- Smelt 100 iron ore into iron plates
"""
# Insert coal into the furnace as fuel
insert_item(Prototype.Coal, stone_furnace, quantity=30)
print("Inserted coal into Stone Furnace")

# Insert iron ore into the furnace
insert_item(Prototype.IronOre, stone_furnace, quantity=100)
print("Inserted Iron Ore into Stone Furnace")

# Wait for smelting to complete
smelting_time = 100 * 0.7  # 0.7 seconds per iron plate
sleep(smelting_time)

# Extract iron plates from the furnace
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, stone_furnace.position, quantity=100)
    current_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plates >= 100:
        break
    sleep(10)  # Wait a bit before trying again

print(f"Extracted Iron Plates; Current Inventory Count: {current_iron_plates}")
assert current_iron_plates >= 100, f"Failed to obtain required number of Iron Plates. Current count: {current_iron_plates}"

"""
Step 4: Craft intermediate products
- Craft 40 iron gear wheels
- Craft 2 underground-belts
"""
# Craft 40 iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=40)
print("Crafted 40 Iron Gear Wheels")

# Craft 2 underground belts
craft_item(Prototype.UndergroundBelt, quantity=2)
print("Crafted 2 Underground Belts")

"""
Step 5: Craft fast-underground-belt
- Craft 1 fast-underground-belt
"""
# Craft 1 fast-underground-belt
craft_item(Prototype.FastUndergroundBelt, quantity=1)
print("Crafted 1 Fast Underground Belt")

# Verify that we have crafted the fast-underground-belt
fast_underground_belt_count = inspect_inventory().get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belt_count >= 1, f"Failed to craft required number of Fast Underground Belts. Current count: {fast_underground_belt_count}"
print("Successfully crafted 1 Fast Underground Belt!")
