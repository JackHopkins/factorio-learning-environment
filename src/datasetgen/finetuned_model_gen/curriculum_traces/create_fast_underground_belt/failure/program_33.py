
from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipe for fast-underground-belt
"""
# Print recipe for fast-underground-belt
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
print(f"fast-underground-belt recipe: {fast_underground_belt_recipe}")

"""
Step 2: Gather raw resources
- Mine at least 30 iron ore
- Mine at least 10 coal
- Mine at least 5 stone (for furnace)
"""
# Define required resources
resources_needed = [
    (Resource.IronOre, 30),
    (Resource.Coal, 10),
    (Resource.Stone, 5)
]

# Loop through each resource type and quantity needed
for resource_type, required_quantity in resources_needed:
    # Find nearest patch of this resource
    resource_position = nearest(resource_type)
    print(f"Nearest {resource_type} found at {resource_position}")
    
    # Move to the resource position
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    print(f"Harvested {harvested} units of {resource_type}")
    
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} units of {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory after gathering:", final_inventory)

# Assert that we have at least the required quantities of each resource
assert final_inventory.get(Resource.IronOre, 0) >= 30, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 10, "Not enough Coal"
assert final_inventory.get(Resource.Stone, 0) >= 5, "Not enough Stone"

print("Successfully gathered all required resources")

"""
Step 3: Craft and set up smelting infrastructure
- Craft 1 stone furnace
- Place the furnace and add coal as fuel
"""
# Craft 1 stone furnace
print("Crafting 1 stone furnace...")
craft_item(Prototype.StoneFurnace, 1)

# Find optimal position for placing furnace
current_position = inspect_entities().player_position
furnace_position = Position(x=current_position[0] + 2, y=current_position[1])

# Place the stone furnace
furnace = place_entity(Prototype.StoneFurnace, Direction.UP, furnace_position)
print(f"Placed stone furnace at {furnace_position}")

# Add coal as fuel to the furnace
coal_in_inventory = inspect_inventory()[Prototype.Coal]
updated_furnace = insert_item(Prototype.Coal, furnace, min(10, coal_in_inventory))
print("Inserted coal into stone furnace")

# Validate that coal was inserted successfully
assert updated_furnace.fuel.get(Prototype.Coal, 0) > 0, "Failed to insert coal into stone furnace"
print("Successfully set up smelting infrastructure")

"""
Step 4: Smelt iron plates
- Smelt 30 iron ore into iron plates
"""
# Insert iron ore into the furnace
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, min(30, iron_ore_in_inventory))
print("Inserted iron ore into stone furnace")

# Wait for smelting to complete
smelting_time = 0.7 * min(30, iron_ore_in_inventory)
sleep(smelting_time)

# Extract iron plates from the furnace
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, min(30, iron_ore_in_inventory))
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= 30:
        break
    sleep(5)  # Additional wait time if needed

print(f"Extracted iron plates; Current count: {current_iron_plate_count}")

# Verify that we have enough iron plates
assert current_iron_plate_count >= 30, f"Failed to obtain required number of iron plates. Expected: 30, Actual: {current_iron_plate_count}"
print("Successfully obtained required number of iron plates")

"""
Step 5: Craft intermediate items
- Craft 2 iron gear wheels
- Craft 2 underground belts

Note: We'll need to craft iron gear wheels first as it's a component of underground belts
"""
# Craft 2 iron gear wheels
print("Crafting 2 iron gear wheels...")
craft_item(Prototype.IronGearWheel, 2)

# Verify crafting success
iron_gear_wheel_count = inspect_inventory().get(Prototype.IronGearWheel, 0)
assert iron_gear_wheel_count >= 2, f"Failed to craft required number of iron gear wheels. Expected: 2, Actual: {iron_gear_wheel_count}"
print(f"Successfully crafted {iron_gear_wheel_count} iron gear wheels")

# Craft 2 underground belts
print("Crafting 2 underground belts...")
craft_item(Prototype.UndergroundBelt, 2)

# Verify crafting success
underground_belt_count = inspect_inventory().get(Prototype.UndergroundBelt, 0)
assert underground_belt_count >= 2, f"Failed to craft required number of underground belts. Expected: 2, Actual: {underground_belt_count}"
print(f"Successfully crafted {underground_belt_count} underground belts")

print("Successfully completed crafting intermediate items")

"""
Step 6: Craft fast-underground-belt
- Craft 1 fast-underground-belt using the crafted components
"""
# Craft 1 fast-underground-belt
print("Crafting 1 fast-underground-belt...")
craft_item(Prototype.FastUndergroundBelt, 1)

# Verify crafting success
fast_underground_belt_count = inspect_inventory().get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belt_count >= 1, f"Failed to craft required number of fast-underground-belts. Expected: 1, Actual: {fast_underground_belt_count}"
print(f"Successfully crafted {fast_underground_belt_count} fast-underground-belts")

print("Successfully completed all steps")

