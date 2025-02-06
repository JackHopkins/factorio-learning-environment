
from instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- Fast-Underground-Belt
- Underground-Belt
- Iron Gear Wheel
- Stone Furnace
We need to gather all resources and craft the intermediate products ourselves.
"""

# Print recipe for Fast-Underground-Belt
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
print("Fast-Underground-Belt Recipe:")
print(fast_underground_belt_recipe)

# Print recipe for Underground-Belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print("Underground-Belt Recipe:")
print(underground_belt_recipe)

# Print recipe for Iron Gear Wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print("Iron Gear Wheel Recipe:")
print(iron_gear_wheel_recipe)

# Print recipe for Stone Furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print("Stone Furnace Recipe:")
print(stone_furnace_recipe)

"""
Step 2: Gather resources. We need to gather the following resources:
- stone: 12
- iron ore: at least 40
- coal: at least 20
We need to mine these resources as there are no entities on the map or in our inventory.
"""

# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 12),
    (Resource.IronOre, 40),
    (Resource.Coal, 20)
]

# Loop through each resource type
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest resource patch
    resource_position = nearest(resource_type)
    
    # Move to the resource position
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    
    # Check if we harvested enough
    inventory = inspect_inventory()
    actual_quantity = inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
for resource_type, required_quantity in resources_to_gather:
    actual_quantity = final_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Final check failed for {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"

print("Successfully gathered all required resources")
print(f"Final inventory: {final_inventory}")

"""
Step 3: Craft stone furnaces. We need to craft 2 stone furnaces.
- Craft 2 stone furnaces using 10 stone
"""

# Craft 2 stone furnaces
crafted_count = craft_item(Prototype.StoneFurnace, quantity=2)

# Verify that we crafted the correct number of stone furnaces
inventory = inspect_inventory()
stone_furnaces = inventory.get(Prototype.StoneFurnace, 0)
assert stone_furnaces >= 2, f"Failed to craft 2 Stone Furnaces. Actual: {stone_furnaces}"

print(f"Successfully crafted {crafted_count} Stone Furnaces")
print(f"Current inventory: {inventory}")

"""
Step 4: Set up smelting operation. We need to set up a smelting operation to produce iron plates:
- Place a stone furnace
- Add coal as fuel to the furnace
- Smelt iron ore into iron plates (we need at least 40 iron plates)
"""

# Place a stone furnace
origin = Position(x=0, y=0)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
move_to(origin)

# Add coal as fuel to the furnace
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
assert coal_in_inventory >= 10, f"Insufficient coal in inventory. Expected at least 10, but found {coal_in_inventory}"
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=10)

# Smelt iron ore into iron plates
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
assert iron_ore_in_inventory >= 40, f"Insufficient iron ore in inventory. Expected at least 40, but found {iron_ore_in_inventory}"
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=40)

# Wait for smelting to complete
smelting_time_per_unit = 0.7  # Average smelting time per unit
estimated_total_smelting_time = int(smelting_time_per_unit * 40)
sleep(estimated_total_smelting_time)

# Extract iron plates from the furnace
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=40)
    iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
    if iron_plates_in_inventory >= 40:
        break
    sleep(10)  # Allow additional time if needed

# Verify that we have at least 40 iron plates
assert iron_plates_in_inventory >= 40, f"Failed to obtain required number of iron plates. Expected at least 40 but found {iron_plates_in_inventory}"

print(f"Successfully smelted {iron_plates_in_inventory} Iron Plates")
print(f"Current inventory: {inspect_inventory()}")

"""
Step 5: Craft iron gear wheels. We need to craft 40 iron gear wheels:
- Each iron gear wheel requires 2 iron plates
- Craft 40 iron gear wheels using 80 iron plates
"""

# Craft 40 iron gear wheels
crafted_count = craft_item(Prototype.IronGearWheel, quantity=40)

# Verify that we crafted the correct number of iron gear wheels
inventory = inspect_inventory()
iron_gear_wheels = inventory.get(Prototype.IronGearWheel, 0)
assert iron_gear_wheels >= 40, f"Failed to craft 40 Iron Gear Wheels. Actual: {iron_gear_wheels}"

print(f"Successfully crafted {crafted_count} Iron Gear Wheels")
print(f"Current inventory: {inventory}")

"""
Step 6: Craft underground-belts. We need to craft 2 underground-belts:
- Each underground-belt requires 10 iron gear wheels and 4 iron plates
- Craft 2 underground-belts using 20 iron gear wheels and 8 iron plates
"""

# Craft 2 underground-belts
crafted_count = craft_item(Prototype.UndergroundBelt, quantity=2)

# Verify that we crafted the correct number of underground-belts
inventory = inspect_inventory()
underground_belts = inventory.get(Prototype.UndergroundBelt, 0)
assert underground_belts >= 2, f"Failed to craft 2 Underground Belts. Actual: {underground_belts}"

print(f"Successfully crafted {crafted_count} Underground Belts")
print(f"Current inventory: {inventory}")

"""
Step 7: Craft fast-underground-belt. We need to craft 1 fast-underground-belt:
- Each fast-underground-belt requires 2 underground-belts and 10 iron gear wheels
- Craft 1 fast-underground-belt using 2 underground-belts and 10 iron gear wheels
"""

# Craft 1 fast-underground-belt
crafted_count = craft_item(Prototype.FastUndergroundBelt, quantity=1)

# Verify that we crafted the correct number of fast-underground-belts
inventory = inspect_inventory()
fast_underground_belts = inventory.get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belts >= 1, f"Failed to craft 1 Fast Underground Belt. Actual: {fast_underground_belts}"

print(f"Successfully crafted {crafted_count} Fast Underground Belts")
print(f"Current inventory: {inventory}")

"""
Step 8: Final verification. We need to verify that we have crafted the required item:
- Check that we have at least 1 fast-underground-belt in our inventory
"""

# Final verification: Check that we have at least 1 fast-underground-belt in our inventory
final_inventory = inspect_inventory()
fast_underground_belts = final_inventory.get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belts >= 1, f"Failed to verify required number of Fast Underground Belts. Expected at least 1 but found {fast_underground_belts}"

print("Successfully completed all steps and crafted the required Fast Underground Belt")

# Print final inventory
print(f"Final inventory: {final_inventory}")

