
from factorio_instance import *

"""
Step 1: Print recipes
"""
"""
The recipes we need to print are:
- stone-furnace
- fast-underground-belt
- iron-gear-wheel
"""
# Print recipe for stone-furnace
print("Recipe for stone-furnace:")
print("Crafting requires 5 stone")

# Print recipe for fast-underground-belt
print("Recipe for fast-underground-belt:")
print("Crafting requires 1 underground-belt and 2 iron gear wheels")

# Print recipe for iron-gear-wheel
print("Recipe for iron-gear-wheel:")
print("Crafting requires 2 iron plates")

"""
Step 2: Gather resources
- Mine at least 44 iron ore
- Mine at least 10 stone
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 44),
    (Resource.Stone, 10)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    # Move to the resource position
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
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 44, "Not enough Iron Ore"
assert final_inventory.get(Resource.Stone, 0) >= 10, "Not enough Stone"

print("Successfully gathered all required resources")

"""
Step 3: Craft intermediate items
- Craft 2 stone furnaces
- Craft 10 iron gear wheels
"""
# Craft 2 stone furnaces
stone_furnaces_crafted = craft_item(Prototype.StoneFurnace, quantity=2)
inventory_after_crafting_furnaces = inspect_inventory()
assert inventory_after_crafting_furnaces.get(Prototype.StoneFurnace, 0) >= 2, "Failed to craft 2 stone furnaces"

# Craft 10 iron gear wheels
iron_gear_wheels_crafted = craft_item(Prototype.IronGearWheel, quantity=10)
inventory_after_crafting_gears = inspect_inventory()
assert inventory_after_crafting_gears.get(Prototype.IronGearWheel, 0) >= 10, "Failed to craft 10 iron gear wheels"

print("Successfully crafted all intermediate items")
print(f"Current inventory: {inventory_after_crafting_gears}")

"""
Step 4: Craft final item
- Craft 1 fast-underground-belt
"""
# Craft 1 fast-underground-belt
fast_underground_belt_crafted = craft_item(Prototype.FastUndergroundBelt, quantity=1)
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, "Failed to craft 1 fast-underground-belt"

print("Successfully crafted 1 fast-underground-belt")
print(f"Final inventory: {final_inventory}")

print("Objective completed successfully!")

