
from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipe for fast-underground-belt, iron-gear-wheel, and underground-belt.
"""
# Print the recipe for fast-underground-belt
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
print("Fast Underground Belt Recipe:")
print(fast_underground_belt_recipe)

# Print the recipe for iron-gear-wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print("\nIron Gear Wheel Recipe:")
print(iron_gear_wheel_recipe)

# Print the recipe for underground-belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print("\nUnderground Belt Recipe:")
print(underground_belt_recipe)

"""
Step 2: Gather raw resources.
- Mine at least 10 iron ore (5 for plates, 5 for gear wheels)
- Mine at least 5 coal for fuel
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 10),
    (Resource.Coal, 5)
]

# Loop through each resource and gather it
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest resource patch
    resource_position = nearest(resource_type)
    
    # Move to the resource position
    move_to(resource_position)
    
    # Harvest the resource
    harvested_quantity = harvest_resource(resource_position, required_quantity)
    
    # Log the result
    print(f"Harvested {harvested_quantity} of {resource_type}. Required: {required_quantity}")

# Check the inventory to ensure we have gathered enough
current_inventory = inspect_inventory()
print("Current inventory after gathering resources:")
print(f"Iron Ore: {current_inventory.get(Prototype.IronOre, 0)}")
print(f"Coal: {current_inventory.get(Prototype.Coal, 0)}")

# Assert to ensure we have gathered enough resources
assert current_inventory.get(Prototype.IronOre, 0) >= 10, "Failed to gather sufficient Iron Ore"
assert current_inventory.get(Prototype.Coal, 0) >= 5, "Failed to gather sufficient Coal"

print("Successfully gathered required resources.")

"""
Step 3: Set up smelting operation.
- Craft a stone furnace (requires 5 stone)
- Place the furnace and add coal as fuel
- Smelt 5 iron ore into 5 iron plates
"""
# Craft a stone furnace (requires 5 stone)
# First, gather stone
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvested_stone = harvest_resource(stone_position, 5)

# Ensure we have enough stone
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.Stone, 0) >= 5, "Failed to gather sufficient Stone"
print(f"Gathered {current_inventory.get(Prototype.Stone, 0)} Stone")

# Craft the Stone Furnace
crafted_quantity = craft_item(Prototype.StoneFurnace, 1)
print(f"Crafted {crafted_quantity} Stone Furnace(s)")

# Place the Stone Furnace
furnace_position = Position(x=0, y=0)  # Arbitrary position for placing
move_to(furnace_position)
stone_furnace = place_entity(Prototype.StoneFurnace, Direction.UP, furnace_position)
print(f"Placed Stone Furnace at {stone_furnace.position}")

# Add coal as fuel to the furnace
coal_quantity = 5  # Use all available coal as fuel
updated_furnace = insert_item(Prototype.Coal, stone_furnace, coal_quantity)
print(f"Inserted {coal_quantity} Coal into the Stone Furnace")

# Smelt 5 iron ore into 5 iron plates
iron_ore_quantity = 5
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, iron_ore_quantity)
print(f"Inserted {iron_ore_quantity} Iron Ore into the Stone Furnace")

# Wait for smelting to complete
smelting_time = 5 * 0.7  # Assuming it takes 0.7 seconds per unit of ore
sleep(smelting_time)

# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, iron_ore_quantity)
    current_inventory = inspect_inventory()
    if current_inventory.get(Prototype.IronPlate, 0) >= iron_ore_quantity:
        break
    sleep(1)

print(f"Extracted {current_inventory.get(Prototype.IronPlate, 0)} Iron Plates")

# Final inventory check
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.IronPlate, 0) >= 5, "Failed to obtain sufficient Iron Plates"
print("Successfully set up smelting operation and obtained Iron Plates.")

"""
Step 4: Craft iron gear wheels.
- Craft 2 iron gear wheels (requires 4 iron plates)
"""
# Ensure we have enough iron plates
current_inventory = inspect_inventory()
iron_plates_available = current_inventory.get(Prototype.IronPlate, 0)
assert iron_plates_available >= 4, f"Insufficient Iron Plates: Required 4, Available {iron_plates_available}"

# Craft 2 Iron Gear Wheels
crafted_quantity = craft_item(Prototype.IronGearWheel, 2)
print(f"Crafted {crafted_quantity} Iron Gear Wheels")

# Verify the crafting process
gear_wheels_in_inventory = inspect_inventory().get(Prototype.IronGearWheel, 0)
assert gear_wheels_in_inventory >= 2, f"Failed to craft required number of Iron Gear Wheels: Expected 2, Found {gear_wheels_in_inventory}"

print(f"Successfully crafted {gear_wheels_in_inventory} Iron Gear Wheels")

# Check remaining Iron Plates
remaining_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
print(f"Remaining Iron Plates: {remaining_iron_plates}")

# Final assertion check
assert remaining_iron_plates >= 0, f"Unexpected state: Negative number of remaining Iron Plates ({remaining_iron_plates})"

print("Successfully completed crafting of Iron Gear Wheels.")

"""
Step 5: Craft underground belt.
- Craft 1 underground belt (requires 1 iron gear wheel and 1 iron plate)
"""
# Ensure we have enough iron gear wheels and iron plates
current_inventory = inspect_inventory()
iron_gear_wheels_available = current_inventory.get(Prototype.IronGearWheel, 0)
iron_plates_available = current_inventory.get(Prototype.IronPlate, 0)
assert iron_gear_wheels_available >= 1, f"Insufficient Iron Gear Wheels: Required 1, Available {iron_gear_wheels_available}"
assert iron_plates_available >= 1, f"Insufficient Iron Plates: Required 1, Available {iron_plates_available}"

# Craft 1 Underground Belt
crafted_quantity = craft_item(Prototype.UndergroundBelt, 1)
print(f"Crafted {crafted_quantity} Underground Belt")

# Verify the crafting process
underground_belts_in_inventory = inspect_inventory().get(Prototype.UndergroundBelt, 0)
assert underground_belts_in_inventory >= 1, f"Failed to craft required number of Underground Belts: Expected 1, Found {underground_belts_in_inventory}"

print(f"Successfully crafted {underground_belts_in_inventory} Underground Belt")

# Check remaining resources
remaining_iron_gear_wheels = inspect_inventory().get(Prototype.IronGearWheel, 0)
remaining_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
print(f"Remaining Iron Gear Wheels: {remaining_iron_gear_wheels}")
print(f"Remaining Iron Plates: {remaining_iron_plates}")

# Final assertion check
assert remaining_iron_gear_wheels >= 0, f"Unexpected state: Negative number of remaining Iron Gear Wheels ({remaining_iron_gear_wheels})"
assert remaining_iron_plates >= 0, f"Unexpected state: Negative number of remaining Iron Plates ({remaining_iron_plates})"

print("Successfully completed crafting of Underground Belt.")

"""
Step 6: Craft fast-underground-belt.
- Craft 1 fast-underground-belt (requires 1 iron gear wheel and 1 underground belt)
"""
# Ensure we have enough iron gear wheels and underground belts
current_inventory = inspect_inventory()
iron_gear_wheels_available = current_inventory.get(Prototype.IronGearWheel, 0)
underground_belts_available = current_inventory.get(Prototype.UndergroundBelt, 0)
assert iron_gear_wheels_available >= 1, f"Insufficient Iron Gear Wheels: Required 1, Available {iron_gear_wheels_available}"
assert underground_belts_available >= 1, f"Insufficient Underground Belts: Required 1, Available {underground_belts_available}"

# Craft 1 Fast Underground Belt
crafted_quantity = craft_item(Prototype.FastUndergroundBelt, 1)
print(f"Crafted {crafted_quantity} Fast Underground Belt")

# Verify the crafting process
fast_underground_belts_in_inventory = inspect_inventory().get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belts_in_inventory >= 1, f"Failed to craft required number of Fast Underground Belts: Expected 1, Found {fast_underground_belts_in_inventory}"

print(f"Successfully crafted {fast_underground_belts_in_inventory} Fast Underground Belt")

# Check remaining resources
remaining_iron_gear_wheels = inspect_inventory().get(Prototype.IronGearWheel, 0)
remaining_underground_belts = inspect_inventory().get(Prototype.UndergroundBelt, 0)
print(f"Remaining Iron Gear Wheels: {remaining_iron_gear_wheels}")
print(f"Remaining Underground Belts: {remaining_underground_belts}")

# Final assertion check
assert remaining_iron_gear_wheels >= 0, f"Unexpected state: Negative number of remaining Iron Gear Wheels ({remaining_iron_gear_wheels})"
assert remaining_underground_belts >= 0, f"Unexpected state: Negative number of remaining Underground Belts ({remaining_underground_belts})"

print("Successfully completed crafting of Fast Underground Belt.")

"""
Step 7: Verify success.
- Check that 1 fast-underground-belt is in the inventory
"""
# Check the inventory for Fast Underground Belt
current_inventory = inspect_inventory()
fast_underground_belts_in_inventory = current_inventory.get(Prototype.FastUndergroundBelt, 0)

# Assert that we have at least 1 Fast Underground Belt
assert fast_underground_belts_in_inventory >= 1, f"Verification failed: Expected 1 Fast Underground Belt, Found {fast_underground_belts_in_inventory}"

print("Verification successful: Fast Underground Belt is in the inventory.")
print(f"Current inventory: {current_inventory}")

