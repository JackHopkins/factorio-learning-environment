

from instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- stone-furnace
- fast-underground-belt

Step 2: Gather resources. We need to gather the following resources:
- Mine at least 12 stone
- Mine at least 40 iron ore
- Mine at least 40 coal

Step 3: Craft stone furnaces. We need to craft 2 stone furnaces using 10 stone.

Step 4: Set up smelting operation. We need to:
- Place one stone furnace
- Fuel the furnace with coal
- Smelt iron ore into iron plates (at least 40 iron plates)

Step 5: Craft iron gear wheels. We need to craft 40 iron gear wheels using 80 iron plates.

Step 6: Craft underground belts. We need to craft 2 underground belts using 20 iron gear wheels and 20 iron plates.

Step 7: Craft fast-underground-belt. We need to craft 1 fast-underground-belt using 2 underground belts and 20 iron gear wheels.

Step 8: Verify the crafted item. We need to check the inventory to ensure we have 1 fast-underground-belt.
"""

"""
Step 1: Print recipes for the required items
"""
# Get the recipes for the required items
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)

# Print the recipes
print("Stone Furnace Recipe:", stone_furnace_recipe)
print("Fast Underground Belt Recipe:", fast_underground_belt_recipe)

"""
Step 2: Gather resources
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 12),
    (Resource.IronOre, 40),
    (Resource.Coal, 40)
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
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory after gathering resources:")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")

# Assert that we have gathered enough of each resource
assert final_inventory.get(Resource.Stone, 0) >= 12, "Not enough Stone"
assert final_inventory.get(Resource.IronOre, 0) >= 40, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 40, "Not enough Coal"

print("Successfully gathered all required resources!")

"""
Step 3: Craft stone furnaces
"""
# Craft 2 stone furnaces
crafted = craft_item(Prototype.StoneFurnace, quantity=2)
print(f"Crafted {crafted} Stone Furnaces")

# Verify that we have crafted 2 stone furnaces
stone_furnaces_in_inventory = inspect_inventory().get(Prototype.StoneFurnace, 0)
assert stone_furnaces_in_inventory >= 2, f"Failed to craft 2 Stone Furnaces. Actual: {stone_furnaces_in_inventory}"

"""
Step 4: Set up smelting operation
"""
# Place the first stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed Stone Furnace at {furnace.position}")

# Move to the furnace and insert coal
move_to(furnace.position)
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=20)
print("Inserted coal into the furnace")

# Insert iron ore into the furnace
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=40)
print("Inserted iron ore into the furnace")

# Wait for smelting to complete
smelting_time = 40 * 0.7  # 0.7 seconds per iron ore
sleep(smelting_time)

# Extract iron plates
iron_plates_needed = 40
max_attempts = 5
for _ in range(max_attempts):
    extracted = extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_plates_needed)
    if extracted:
        break
    sleep(10)  # Wait for more smelting if needed

# Verify that we have enough iron plates
iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
assert iron_plates_in_inventory >= iron_plates_needed, f"Failed to obtain enough Iron Plates. Needed: {iron_plates_needed}, Actual: {iron_plates_in_inventory}"
print(f"Successfully obtained {iron_plates_in_inventory} Iron Plates")

"""
Step 5: Craft iron gear wheels
"""
iron_gear_wheels_to_craft = 40
iron_plates_required_for_gears = iron_gear_wheels_to_craft * 2

# Verify we have enough iron plates
assert iron_plates_in_inventory >= iron_plates_required_for_gears, f"Not enough Iron Plates to craft Iron Gear Wheels. Required: {iron_plates_required_for_gears}, Actual: {iron_plates_in_inventory}"

# Craft Iron Gear Wheels
crafted_gears = craft_item(Prototype.IronGearWheel, quantity=iron_gear_wheels_to_craft)
print(f"Crafted {crafted_gears} Iron Gear Wheels")

# Verify that we have crafted the correct number of Iron Gear Wheels
iron_gear_wheels_in_inventory = inspect_inventory().get(Prototype.IronGearWheel, 0)
assert iron_gear_wheels_in_inventory >= iron_gear_wheels_to_craft, f"Failed to craft enough Iron Gear Wheels. Required: {iron_gear_wheels_to_craft}, Actual: {iron_gear_wheels_in_inventory}"
print(f"Successfully crafted {iron_gear_wheels_in_inventory} Iron Gear Wheels")

"""
Step 6: Craft underground belts
"""
# Craft 2 underground belts
crafted_underground_belts = craft_item(Prototype.UndergroundBelt, quantity=2)
print(f"Crafted {crafted_underground_belts} Underground Belts")

# Verify that we have crafted 2 underground belts
underground_belts_in_inventory = inspect_inventory().get(Prototype.UndergroundBelt, 0)
assert underground_belts_in_inventory >= 2, f"Failed to craft 2 Underground Belts. Actual: {underground_belts_in_inventory}"

"""
Step 7: Craft fast-underground-belt
"""
# Craft 1 fast-underground-belt
crafted_fast_underground_belts = craft_item(Prototype.FastUndergroundBelt, quantity=1)
print(f"Crafted {crafted_fast_underground_belts} Fast Underground Belts")

# Verify that we have crafted 1 fast-underground-belt
fast_underground_belts_in_inventory = inspect_inventory().get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belts_in_inventory >= 1, f"Failed to craft 1 Fast Underground Belt. Actual: {fast_underground_belts_in_inventory}"

"""
Step 8: Verify the crafted item
"""
final_inventory = inspect_inventory()
print("Final inventory after crafting:")
print(f"Fast Underground Belts: {final_inventory.get(Prototype.FastUndergroundBelt, 0)}")

# Assert that we have at least one fast-underground-belt
assert final_inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, "Crafting failed: Not enough Fast Underground Belts in inventory"

print("Successfully crafted Fast Underground Belt!")

