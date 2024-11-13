
from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipes for fast-underground-belt, iron-gear-wheel, and transport-belt. This will help us understand the ingredients required for each item.
"""
# Get the recipe for fast-underground-belt
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)

# Get the recipe for iron-gear-wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)

# Get the recipe for transport-belt
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)

# Print the recipes
print("Fast Underground Belt Recipe:", fast_underground_belt_recipe)
print("Iron Gear Wheel Recipe:", iron_gear_wheel_recipe)
print("Transport Belt Recipe:", transport_belt_recipe)

"""
Step 2: Gather raw resources. We need to mine iron ore (at least 48 iron ore) and coal (at least 10 coal). We also need to mine stone (at least 5 stone) to craft a stone furnace.
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 48),
    (Resource.Coal, 10),
    (Resource.Stone, 5)
]

# Loop over each resource type and quantity
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
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory after gathering resources:")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")

# Ensure we have at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 48, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 10, "Not enough Coal"
assert final_inventory.get(Resource.Stone, 0) >= 5, "Not enough Stone"

print("Successfully gathered all required raw resources")

"""
Step 3: Craft and set up smelting infrastructure. We need to craft a stone furnace and place it. Then, we need to smelt the iron ore into iron plates.
"""
# Craft a stone furnace
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted {crafted_furnaces} stone furnaces")

# Check if we successfully crafted the stone furnace
assert crafted_furnaces == 1, "Failed to craft the stone furnace"

# Place the stone furnace near the current position
current_position = Position(x=0, y=0)  # Assume we're at the origin for simplicity
furnace = place_entity(Prototype.StoneFurnace, position=current_position)
print(f"Placed stone furnace at {furnace.position}")

# Insert coal into the furnace as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=5)
print("Inserted coal into the stone furnace")

# Insert iron ore into the furnace
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=48)
print("Inserted iron ore into the stone furnace")

# Wait for smelting to complete
smelting_time = 0.7 * 48  # Each iron ore takes approximately 0.7 seconds to smelt
sleep(smelting_time)
print("Smelting completed")

# Extract iron plates from the furnace
max_attempts = 5
for attempt in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=48)
    current_inventory = inspect_inventory()
    iron_plate_count = current_inventory.get(Prototype.IronPlate, 0)
    if iron_plate_count >= 48:
        break
    sleep(10)  # Wait a bit longer if not all plates are ready

print(f"Extracted iron plates; Current inventory: {iron_plate_count} Iron Plates")
assert iron_plate_count >= 48, f"Failed to obtain required number of Iron Plates; Expected: 48, Actual: {iron_plate_count}"

print("Successfully crafted and set up smelting infrastructure")
print("Iron plates are ready for crafting")

"""
Step 4: Craft intermediate items. We need to craft at least 24 iron gear wheels and 2 transport belts. This requires 48 iron plates for the gear wheels and 2 iron plates + 2 gear wheels for the transport belts.
"""
# Craft Iron Gear Wheels
gear_wheels_crafted = craft_item(Prototype.IronGearWheel, quantity=24)
print(f"Crafted {gear_wheels_crafted} Iron Gear Wheels")

# Verify crafting of Iron Gear Wheels
current_inventory = inspect_inventory()
iron_gear_wheel_count = current_inventory.get(Prototype.IronGearWheel, 0)
assert iron_gear_wheel_count >= 24, f"Failed to craft required number of Iron Gear Wheels; Expected: 24, Actual: {iron_gear_wheel_count}"

# Craft Transport Belts
transport_belts_crafted = craft_item(Prototype.TransportBelt, quantity=2)
print(f"Crafted {transport_belts_crafted} Transport Belts")

# Verify crafting of Transport Belts
transport_belt_count = current_inventory.get(Prototype.TransportBelt, 0)
assert transport_belt_count >= 2, f"Failed to craft required number of Transport Belts; Expected: 2, Actual: {transport_belt_count}"

print("Successfully crafted all intermediate items")

"""
Step 5: Craft underground-belts. We need to craft 2 underground-belts, each requiring 10 iron gear wheels and 1 transport belt.
"""
# Craft Underground Belts
underground_belts_crafted = craft_item(Prototype.UndergroundBelt, quantity=2)
print(f"Crafted {underground_belts_crafted} Underground Belts")

# Verify crafting of Underground Belts
current_inventory = inspect_inventory()
underground_belt_count = current_inventory.get(Prototype.UndergroundBelt, 0)
assert underground_belt_count >= 2, f"Failed to craft required number of Underground Belts; Expected: 2, Actual: {underground_belt_count}"

print("Successfully crafted all required Underground Belts")

"""
Step 6: Craft fast-underground-belt. We need to craft 1 fast-underground-belt using the 2 underground-belts we just crafted.
"""
# Craft Fast Underground Belts
fast_underground_belts_crafted = craft_item(Prototype.FastUndergroundBelt, quantity=1)
print(f"Crafted {fast_underground_belts_crafted} Fast Underground Belts")

# Verify crafting of Fast Underground Belts
current_inventory = inspect_inventory()
fast_underground_belt_count = current_inventory.get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belt_count >= 1, f"Failed to craft required number of Fast Underground Belts; Expected: 1, Actual: {fast_underground_belt_count}"

print("Successfully crafted all required Fast Underground Belts")
print("Final Inventory:")
print(f"Fast Underground Belts: {fast_underground_belt_count}")

