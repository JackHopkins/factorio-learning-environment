

from instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- fast-underground-belt
- iron-gear-wheel
- underground-belt
"""

"""
Print recipe for fast-underground-belt
"""
# Get the recipe for fast-underground-belt
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)

# Print the recipe details
print("fast-underground-belt Recipe:")
print(fast_underground_belt_recipe)

"""
Print recipe for iron-gear-wheel
"""
# Get the recipe for iron-gear-wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)

# Print the recipe details
print("\nIron Gear Wheel Recipe:")
print(iron_gear_wheel_recipe)

"""
Print recipe for underground-belt
"""
# Get the recipe for underground-belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)

# Print the recipe details
print("\nUnderground Belt Recipe:")
print(underground_belt_recipe)


"""
Step 2: Gather resources. We need to gather the following resources:
- Mine at least 20 iron ore
- Mine at least 5 stone
- Gather at least 10 coal for fuel
"""
from instance import *

# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 40),
    (Resource.Stone, 5),
    (Resource.Coal, 10)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    
    # Move to the resource location
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    
    # Get current inventory count for this resource
    current_inventory = inspect_inventory()[resource_type]
    
    # Assert that we have at least as much as we wanted
    assert current_inventory >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {current_inventory}"
    
    print(f"Successfully gathered {current_inventory} units of {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
print(final_inventory)

# Specific assertions for each resource
assert final_inventory[Resource.IronOre] >= 40, f"Insufficient Iron Ore! Expected at least 40 but got {final_inventory[Resource.IronOre]}"
assert final_inventory[Resource.Stone] >= 5, f"Insufficient Stone! Expected at least 5 but got {final_inventory[Resource.Stone]}"
assert final_inventory[Resource.Coal] >= 10, f"Insufficient Coal! Expected at least 10 but got {final_inventory[Resource.Coal]}"

print("Successfully gathered all required resources.")


"""
Step 3: Craft stone furnace. We need to craft a stone furnace using 5 stone.
"""
from instance import *

# Print current inventory before crafting
current_inventory = inspect_inventory()
print(f"Current inventory before crafting: {current_inventory}")

# Ensure we have enough stone
assert current_inventory[Resource.Stone] >= 5, f"Insufficient Stone! Expected at least 5 but got {current_inventory[Resource.Stone]}"

# Craft the stone furnace
crafted_quantity = craft_item(Prototype.StoneFurnace, quantity=1)

# Verify that exactly one stone furnace was crafted
assert crafted_quantity == 1, f"Failed to craft Stone Furnace! Expected to craft 1 but crafted {crafted_quantity}"

# Print success message
print("Successfully crafted a Stone Furnace.")

# Print updated inventory after crafting
updated_inventory = inspect_inventory()
print(f"Updated inventory after crafting: {updated_inventory}")

# Verify that stone count has decreased by at least five
assert updated_inventory[Resource.Stone] <= current_inventory[Resource.Stone] - 5, "Stone count did not decrease as expected after crafting"

# Verify presence of at least one stone furnace in inventory
assert updated_inventory[Prototype.StoneFurnace] >= 1, "Failed to craft or add Stone Furnace into inventory"

# Check final condition for successful crafting process
assert updated_inventory[Prototype.StoneFurnace] >= 1, "Failed to craft Stone Furnace"

print("Stone Furnace successfully crafted and verified.")


"""
Step 4: Set up smelting operation. We need to set up a smelting operation to produce iron plates:
- Place the stone furnace
- Add coal as fuel to the furnace
- Smelt iron ore into iron plates (we need at least 40 iron plates)
"""
from instance import *

# Step 1: Place the stone furnace
"""
We need to place the stone furnace in the world
"""
# Define where we want to place the furnace
furnace_position = Position(x=0, y=0)

# Move to the position
move_to(furnace_position)

# Place the stone furnace
furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)
print(f"Placed stone furnace at {furnace_position}")

# Step 2: Add coal as fuel to the furnace
"""
We need to add coal as fuel to the furnace
"""
# Insert coal into the furnace
coal_inserted = insert_item(Prototype.Coal, furnace, quantity=10)
print("Inserted coal into the furnace.")

# Verify that coal was successfully inserted
furnace_inventory = inspect_inventory(furnace)
assert furnace_inventory[Prototype.Coal] > 0, "Failed to insert coal into the furnace"
print("Coal successfully added as fuel.")

# Step 3: Smelt iron ore into iron plates
"""
We need to smelt iron ore into iron plates
"""
# Insert iron ore into the furnace
iron_ore_inserted = insert_item(Prototype.IronOre, furnace, quantity=40)
print("Inserted iron ore into the furnace.")

# Wait for smelting process to complete
smelting_time_per_unit = 3.2  # Assuming a smelting time of 3.2 seconds per unit
total_smelting_time = int(smelting_time_per_unit * iron_ore_inserted)
sleep(total_smelting_time)

# Extract iron plates from the furnace
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    # Attempt to extract all available iron plates
    extract_item(Prototype.IronPlate, furnace.position, quantity=40)
    
    # Check how many are now in your inventory
    current_iron_plate_count = inspect_inventory()[Prototype.IronPlate]
    
    # If you've reached or exceeded your goal number of plates then break out early
    if current_iron_plate_count >= 40:
        break
    
    sleep(10)  # Allow additional time if needed

print("Smelting operation complete.")

# Final assertion check on produced quantity
final_inventory = inspect_inventory()
assert final_inventory[Prototype.IronPlate] >= 40, f"Failed to produce required number of Iron Plates! Expected at least 40 but got {final_inventory[Prototype.IronPlate]}"
print(f"Successfully produced {final_inventory[Prototype.IronPlate]} Iron Plates.")

# Clean up by picking up the furnace
pickup_entity(Prototype.StoneFurnace, furnace.position)

print("Smelting operation completed successfully.")


"""
Step 5: Craft iron gear wheels. We need to craft 40 iron gear wheels, which requires 80 iron plates.
"""
from instance import *

# Print current inventory before crafting
current_inventory = inspect_inventory()
print(f"Current inventory before crafting: {current_inventory}")

# Ensure we have enough iron plates
assert current_inventory[Prototype.IronPlate] >= 80, f"Insufficient Iron Plates! Expected at least 80 but got {current_inventory[Prototype.IronPlate]}"

# Craft the iron gear wheels
crafted_quantity = craft_item(Prototype.IronGearWheel, quantity=40)

# Verify that exactly forty iron gear wheels were crafted
assert crafted_quantity == 40, f"Failed to craft Iron Gear Wheels! Expected to craft 40 but crafted {crafted_quantity}"

# Print success message
print("Successfully crafted 40 Iron Gear Wheels.")

# Print updated inventory after crafting
updated_inventory = inspect_inventory()
print(f"Updated inventory after crafting: {updated_inventory}")

# Verify presence of at least forty iron gear wheels in inventory
assert updated_inventory[Prototype.IronGearWheel] >= 40, "Failed to craft or add Iron Gear Wheels into inventory"

# Check final condition for successful crafting process
assert updated_inventory[Prototype.IronGearWheel] >= 40, "Failed to craft required number of Iron Gear Wheels"

print("Iron Gear Wheels successfully crafted and verified.")


"""
Step 6: Craft underground belts. We need to craft 2 underground belts, which requires 20 iron gear wheels and 10 iron plates.
"""
from instance import *

# Print current inventory before crafting
current_inventory = inspect_inventory()
print(f"Current inventory before crafting: {current_inventory}")

# Ensure we have enough iron gear wheels and iron plates
assert current_inventory[Prototype.IronGearWheel] >= 20, f"Insufficient Iron Gear Wheels! Expected at least 20 but got {current_inventory[Prototype.IronGearWheel]}"
assert current_inventory[Prototype.IronPlate] >= 10, f"Insufficient Iron Plates! Expected at least 10 but got {current_inventory[Prototype.IronPlate]}"

# Craft the underground belts
crafted_quantity = craft_item(Prototype.UndergroundBelt, quantity=2)

# Verify that exactly two underground belts were crafted
assert crafted_quantity == 2, f"Failed to craft Underground Belts! Expected to craft 2 but crafted {crafted_quantity}"

# Print success message
print("Successfully crafted 2 Underground Belts.")

# Print updated inventory after crafting
updated_inventory = inspect_inventory()
print(f"Updated inventory after crafting: {updated_inventory}")

# Verify presence of at least two underground belts in inventory
assert updated_inventory[Prototype.UndergroundBelt] >= 2, "Failed to craft or add Underground Belts into inventory"

# Check final condition for successful crafting process
assert updated_inventory[Prototype.UndergroundBelt] >= 2, "Failed to craft required number of Underground Belts"

print("Underground Belts successfully crafted and verified.")


"""
Step 7: Craft fast underground belt. We need to craft 1 fast underground belt, which requires 2 iron gear wheels and 1 underground belt.
"""
from instance import *

# Print current inventory before crafting
current_inventory = inspect_inventory()
print(f"Current inventory before crafting: {current_inventory}")

# Ensure we have enough iron gear wheels and underground belts
assert current_inventory[Prototype.IronGearWheel] >= 2, f"Insufficient Iron Gear Wheels! Expected at least 2 but got {current_inventory[Prototype.IronGearWheel]}"
assert current_inventory[Prototype.UndergroundBelt] >= 1, f"Insufficient Underground Belts! Expected at least 1 but got {current_inventory[Prototype.UndergroundBelt]}"

# Craft the fast underground belt
crafted_quantity = craft_item(Prototype.FastUndergroundBelt, quantity=1)

# Verify that exactly one fast underground belt was crafted
assert crafted_quantity == 1, f"Failed to craft Fast Underground Belt! Expected to craft 1 but crafted {crafted_quantity}"

# Print success message
print("Successfully crafted a Fast Underground Belt.")

# Print updated inventory after crafting
updated_inventory = inspect_inventory()
print(f"Updated inventory after crafting: {updated_inventory}")

# Verify presence of at least one fast underground belt in inventory
assert updated_inventory[Prototype.FastUndergroundBelt] >= 1, "Failed to craft or add Fast Underground Belt into inventory"

# Check final condition for successful crafting process
assert updated_inventory[Prototype.FastUndergroundBelt] >= 1, "Failed to craft required number of Fast Underground Belts"

print("Fast Underground Belt successfully crafted and verified.")


"""
Step 8: Verify the result. We need to check if we have successfully crafted the fast underground belt by checking our inventory.
"""
from instance import *

# Inspect the current inventory
final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

# Check for presence of Fast Underground Belt in the inventory
fast_underground_belt_count = final_inventory.get(Prototype.FastUndergroundBelt, 0)

# Verify that at least one Fast Underground Belt is present
assert fast_underground_belt_count >= 1, f"Verification failed! Expected at least 1 Fast Underground Belt but found {fast_underground_belt_count}"

# Print success message if verification passes
print("Verification successful: Fast Underground Belt is present in the inventory.")

