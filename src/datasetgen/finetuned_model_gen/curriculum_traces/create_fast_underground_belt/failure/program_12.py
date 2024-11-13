
from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- iron-gear-wheel
- underground-belt
- fast-underground-belt
"""
# Get and print the recipe for iron-gear-wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(f"Iron Gear Wheel Recipe: {iron_gear_wheel_recipe}")

# Get and print the recipe for underground-belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print(f"Underground Belt Recipe: {underground_belt_recipe}")

# Get and print the recipe for fast-underground-belt
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
print(f"Fast Underground Belt Recipe: {fast_underground_belt_recipe}")

"""
Step 2: Gather resources. We need to mine the following resources:
- Iron ore (at least 48)
- Coal (at least 10 for smelting)
- Stone (at least 5 for crafting a furnace)
"""
# Define the required resources and their quantities
required_resources = [
    (Resource.IronOre, 48),
    (Resource.Coal, 10),
    (Resource.Stone, 5)
]

# Loop through each required resource
for resource_type, required_quantity in required_resources:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    print(f"Nearest {resource_type} found at {resource_position}")

    # Move to the resource's position
    move_to(resource_position)
    print(f"Moved to {resource_type} at {resource_position}")

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
print(f"Final inventory: {final_inventory}")

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 48, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 10, "Not enough Coal"
assert final_inventory.get(Resource.Stone, 0) >= 5, "Not enough Stone"

print("Successfully gathered all required resources!")

"""
Step 3: Craft and set up a furnace. We need to:
- Craft a stone furnace
- Place the furnace
- Add coal to the furnace as fuel
"""
# Craft a stone furnace
print("Crafting a stone furnace...")
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
assert crafted_furnaces == 1, f"Failed to craft stone furnace. Expected 1, but got {crafted_furnaces}"
print("Successfully crafted a stone furnace.")

# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed stone furnace at {furnace.position}")

# Add coal to the furnace as fuel
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
assert coal_in_inventory >= 10, f"Insufficient coal in inventory. Expected at least 10, but got {coal_in_inventory}"
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=10)
print("Inserted coal into the stone furnace.")

# Verify that the furnace is properly fueled
fueled_coal = updated_furnace.fuel.get(Prototype.Coal, 0)
assert fueled_coal > 0, "Failed to fuel the furnace with coal."
print("Stone furnace successfully set up and fueled.")

"""
Step 4: Smelt iron plates. We need to:
- Smelt 48 iron ore into 48 iron plates
- Check the furnace output and collect the iron plates
"""
# Insert iron ore into the furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
assert iron_ore_in_inventory >= 48, f"Insufficient iron ore. Expected at least 48, but got {iron_ore_in_inventory}"
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=48)
print("Inserted iron ore into the stone furnace.")

# Wait for the smelting process to complete
smelting_time_per_unit = 3.2  # Time taken to smelt one unit of iron ore into an iron plate
total_smelting_time = int(smelting_time_per_unit * 48)
print(f"Waiting for {total_smelting_time} seconds for smelting to complete...")
sleep(total_smelting_time)

# Attempt to extract iron plates from the furnace multiple times if needed
max_attempts = 10
for _ in range(max_attempts):
    # Extract iron plates from the furnace
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=48)
    
    # Check current inventory for iron plates
    current_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
    print(f"Current iron plates in inventory: {current_iron_plates}")
    
    # Check if we have extracted all required iron plates
    if current_iron_plates >= 48:
        break
    
    # Wait a bit before trying again
    sleep(5)

# Final assertion to ensure all required iron plates are in inventory
assert current_iron_plates >= 48, f"Failed to obtain required number of iron plates. Expected: 48, Actual: {current_iron_plates}"
print("Successfully obtained 48 iron plates.")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory after smelting: {final_inventory}")

# Check if there are any remaining items in the furnace and extract them if necessary
furnace_inventory = updated_furnace.furnace_result
remaining_iron_plates = furnace_inventory.get(Prototype.IronPlate, 0)
if remaining_iron_plates > 0:
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=remaining_iron_plates)
    print(f"Extracted additional {remaining_iron_plates} iron plates from the furnace.")

# Final confirmation of successful completion of step
print("Successfully completed Step 4: Smelted 48 iron ore into 48 iron plates.")

"""
Step 5: Craft iron gear wheels. We need to:
- Craft 40 iron gear wheels using 80 iron plates
"""
# Check initial inventory for iron plates
initial_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
print(f"Initial iron plates in inventory: {initial_iron_plates}")

# Verify that we have enough iron plates to craft 40 iron gear wheels
assert initial_iron_plates >= 80, f"Insufficient iron plates. Expected at least 80, but got {initial_iron_plates}"

# Craft 40 iron gear wheels
print("Crafting 40 iron gear wheels...")
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=40)
assert crafted_gear_wheels == 40, f"Failed to craft required number of iron gear wheels. Expected: 40, Actual: {crafted_gear_wheels}"
print("Successfully crafted 40 iron gear wheels.")

# Check final inventory for iron gear wheels and remaining iron plates
final_inventory = inspect_inventory()
iron_gear_wheels_in_inventory = final_inventory.get(Prototype.IronGearWheel, 0)
remaining_iron_plates = final_inventory.get(Prototype.IronPlate, 0)

print(f"Final inventory: {final_inventory}")
print(f"Iron gear wheels in inventory: {iron_gear_wheels_in_inventory}")
print(f"Remaining iron plates: {remaining_iron_plates}")

# Assert that we have crafted 40 iron gear wheels
assert iron_gear_wheels_in_inventory >= 40, f"Failed to craft required number of iron gear wheels. Expected: 40, Actual: {iron_gear_wheels_in_inventory}"

# Assert that we have used 80 iron plates to craft the gear wheels
expected_remaining_iron_plates = initial_iron_plates - 80
assert remaining_iron_plates == expected_remaining_iron_plates, f"Unexpected number of remaining iron plates. Expected: {expected_remaining_iron_plates}, Actual: {remaining_iron_plates}"

print("Successfully completed Step 5: Crafted 40 iron gear wheels.")

"""
Step 6: Craft underground belts. We need to:
- Craft 2 underground belts using 80 iron plates
"""
# Check initial inventory for iron plates
initial_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
initial_iron_gear_wheels = inspect_inventory().get(Prototype.IronGearWheel, 0)

print(f"Initial iron plates in inventory: {initial_iron_plates}")
print(f"Initial iron gear wheels in inventory: {initial_iron_gear_wheels}")

# Verify that we have enough iron plates and iron gear wheels to craft 2 underground belts
assert initial_iron_plates >= 80, f"Insufficient iron plates. Expected at least 80, but got {initial_iron_plates}"
assert initial_iron_gear_wheels >= 40, f"Insufficient iron gear wheels. Expected at least 40, but got {initial_iron_gear_wheels}"

# Craft 2 underground belts
print("Crafting 2 underground belts...")
crafted_underground_belts = craft_item(Prototype.UndergroundBelt, quantity=2)
assert crafted_underground_belts == 2, f"Failed to craft required number of underground belts. Expected: 2, Actual: {crafted_underground_belts}"
print("Successfully crafted 2 underground belts.")

# Check final inventory for underground belts and remaining resources
final_inventory = inspect_inventory()
underground_belts_in_inventory = final_inventory.get(Prototype.UndergroundBelt, 0)
remaining_iron_plates = final_inventory.get(Prototype.IronPlate, 0)
remaining_iron_gear_wheels = final_inventory.get(Prototype.IronGearWheel, 0)

print(f"Final inventory: {final_inventory}")
print(f"Underground belts in inventory: {underground_belts_in_inventory}")
print(f"Remaining iron plates: {remaining_iron_plates}")
print(f"Remaining iron gear wheels: {remaining_iron_gear_wheels}")

# Assert that we have crafted 2 underground belts
assert underground_belts_in_inventory >= 2, f"Failed to craft required number of underground belts. Expected: 2, Actual: {underground_belts_in_inventory}"

# Assert that we have used the correct number of iron plates and iron gear wheels
expected_remaining_iron_plates = initial_iron_plates - 80
expected_remaining_iron_gear_wheels = initial_iron_gear_wheels - 40

assert remaining_iron_plates == expected_remaining_iron_plates, f"Unexpected number of remaining iron plates. Expected: {expected_remaining_iron_plates}, Actual: {remaining_iron_plates}"
assert remaining_iron_gear_wheels == expected_remaining_iron_gear_wheels, f"Unexpected number of remaining iron gear wheels. Expected: {expected_remaining_iron_gear_wheels}, Actual: {remaining_iron_gear_wheels}"

print("Successfully completed Step 6: Crafted 2 underground belts.")

"""
Step 7: Craft fast-underground-belt. We need to:
- Craft 1 fast-underground-belt using 2 underground belts and 40 iron gear wheels
"""
# Check initial inventory for underground belts and iron gear wheels
initial_underground_belts = inspect_inventory().get(Prototype.UndergroundBelt, 0)
initial_iron_gear_wheels = inspect_inventory().get(Prototype.IronGearWheel, 0)

print(f"Initial underground belts in inventory: {initial_underground_belts}")
print(f"Initial iron gear wheels in inventory: {initial_iron_gear_wheels}")

# Verify that we have enough underground belts and iron gear wheels to craft 1 fast-underground-belt
assert initial_underground_belts >= 2, f"Insufficient underground belts. Expected at least 2, but got {initial_underground_belts}"
assert initial_iron_gear_wheels >= 40, f"Insufficient iron gear wheels. Expected at least 40, but got {initial_iron_gear_wheels}"

# Craft 1 fast-underground-belt
print("Crafting 1 fast-underground-belt...")
crafted_fast_underground_belts = craft_item(Prototype.FastUndergroundBelt, quantity=1)
assert crafted_fast_underground_belts == 1, f"Failed to craft required number of fast-underground-belts. Expected: 1, Actual: {crafted_fast_underground_belts}"
print("Successfully crafted 1 fast-underground-belt.")

# Check final inventory for fast-underground-belt and remaining resources
final_inventory = inspect_inventory()
fast_underground_belts_in_inventory = final_inventory.get(Prototype.FastUndergroundBelt, 0)
remaining_underground_belts = final_inventory.get(Prototype.UndergroundBelt, 0)
remaining_iron_gear_wheels = final_inventory.get(Prototype.IronGearWheel, 0)

print(f"Final inventory: {final_inventory}")
print(f"Fast-underground-belts in inventory: {fast_underground_belts_in_inventory}")
print(f"Remaining underground belts: {remaining_underground_belts}")
print(f"Remaining iron gear wheels: {remaining_iron_gear_wheels}")

# Assert that we have crafted 1 fast-underground-belt
assert fast_underground_belts_in_inventory >= 1, f"Failed to craft required number of fast-underground-belts. Expected: 1, Actual: {fast_underground_belts_in_inventory}"

# Assert that we have used the correct number of underground belts and iron gear wheels
expected_remaining_underground_belts = initial_underground_belts - 2
expected_remaining_iron_gear_wheels = initial_iron_gear_wheels - 40

assert remaining_underground_belts == expected_remaining_underground_belts, f"Unexpected number of remaining underground belts. Expected: {expected_remaining_underground_belts}, Actual: {remaining_underground_belts}"
assert remaining_iron_gear_wheels == expected_remaining_iron_gear_wheels, f"Unexpected number of remaining iron gear wheels. Expected: {expected_remaining_iron_gear_wheels}, Actual: {remaining_iron_gear_wheels}"

print("Successfully completed Step 7: Crafted 1 fast-underground-belt.")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory after crafting fast-underground-belt: {final_inventory}")

# Assert that we have at least 1 fast-underground-belt in our inventory
assert final_inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, "Failed to craft required number of fast-underground-belts."

print("Successfully crafted all required fast-underground-belts!")

# Print the final inventory
print("Final inventory:")
print(f"Fast underground belts: {final_inventory.get(Prototype.FastUndergroundBelt, 0)}")
print(f"Underground belts: {final_inventory.get(Prototype.UndergroundBelt, 0)}")
print(f"Iron gear wheels: {final_inventory.get(Prototype.IronGearWheel, 0)}")
