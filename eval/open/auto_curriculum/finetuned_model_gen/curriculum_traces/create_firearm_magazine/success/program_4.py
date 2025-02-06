

from instance import *


"""
Objective: Craft a firearm magazine from scratch

Planning:
We need to craft a firearm magazine, which requires 4 iron plates.
There are no entities on the map or in the inventory, so we need to gather all resources and craft all necessary items.
We need to mine iron ore and coal, smelt the iron ore into plates, and then craft the magazine.
A stone furnace is also needed for smelting.
"""

"""
Step 1: Print recipes
"""
print("Recipes:")
print("Stone Furnace: 5 stone")
print("Firearm Magazine: 4 iron plates")

"""
Step 2: Gather raw resources
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 6),
    (Resource.IronOre, 14),
    (Resource.Coal, 7)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    print(f"Nearest {resource_type} found at: {resource_position}")

    # Move to the resource
    move_to(resource_position)
    print(f"Moved to {resource_type} patch")

    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    print(f"Harvested {harvested} {resource_type}")

    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")

# Assert that we have all the required resources
assert final_inventory.get(Resource.Stone, 0) >= 6, "Not enough Stone"
assert final_inventory.get(Resource.IronOre, 0) >= 14, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 7, "Not enough Coal"

print("Successfully gathered all required resources")

"""
Step 3: Craft stone furnace
"""
print("Crafting stone furnace")
craft_item(Prototype.StoneFurnace, 1)

# Verify that we have the stone furnace
stone_furnace_count = inspect_inventory().get(Prototype.StoneFurnace, 0)
assert stone_furnace_count >= 1, f"Failed to craft stone furnace. Expected at least 1, but got {stone_furnace_count}"
print(f"Successfully crafted {stone_furnace_count} stone furnace(s)")

"""
Step 4: Set up smelting area
"""
# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)

# Insert coal into the furnace as fuel
insert_item(Prototype.Coal, furnace, quantity=6)
print("Inserted coal into the furnace")

"""
Step 5: Smelt iron plates
"""
# Insert iron ore into the furnace
insert_item(Prototype.IronOre, furnace, quantity=14)
print("Inserted iron ore into the furnace")

# Wait for smelting to complete
smelting_time = 14 * 0.7  # 0.7 seconds per iron ore
sleep(int(smelting_time))

# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, furnace.position, quantity=14)
    iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if iron_plate_count >= 14:
        break
    sleep(10)

print(f"Extracted iron plates; current inventory count: {iron_plate_count}")

# Verify that we have enough iron plates
assert iron_plate_count >= 14, f"Failed to obtain enough iron plates. Expected: at least 14, Actual: {iron_plate_count}"
print("Successfully obtained required number of iron plates")

"""
Step 6: Craft firearm magazine
"""
print("Crafting firearm magazine")
craft_item(Prototype.FirearmMagazine, 1)

# Verify that we have crafted the firearm magazine
firearm_magazine_count = inspect_inventory().get(Prototype.FirearmMagazine, 0)
assert firearm_magazine_count >= 1, f"Failed to craft firearm magazine. Expected at least 1, but got {firearm_magazine_count}"
print(f"Successfully crafted {firearm_magazine_count} firearm magazine(s)")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Firearm Magazine: {final_inventory.get(Prototype.FirearmMagazine, 0)}")
print(f"Remaining Iron Plates: {final_inventory.get(Prototype.IronPlate, 0)}")

print("Successfully crafted firearm magazine from scratch!")

