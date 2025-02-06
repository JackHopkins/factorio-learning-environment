
from instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- stone-furnace
- fast-underground-belt
- iron-gear-wheel
- underground-belt
"""
# Print recipes for stone-furnace
print("stone-furnace recipe:")
print(get_prototype_recipe(Prototype.StoneFurnace))

# Print recipes for fast-underground-belt
print("fast-underground-belt recipe:")
print(get_prototype_recipe(Prototype.FastUndergroundBelt))

# Print recipes for iron-gear-wheel
print("iron-gear-wheel recipe:")
print(get_prototype_recipe(Prototype.IronGearWheel))

# Print recipes for underground-belt
print("underground-belt recipe:")
print(get_prototype_recipe(Prototype.UndergroundBelt))

"""
Step 2: Gather resources. We need to gather the following resources:
- Stone: 10 (for 2 stone furnaces)
- Iron ore: 40 (for 40 iron plates)
- Coal: 20 (for fuel)
"""
# Define required resources
required_resources = {
    Resource.Stone: 10,
    Resource.IronOre: 40,
    Resource.Coal: 20
}

# Loop through each required resource
for resource_type, required_quantity in required_resources.items():
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    # Move to the resource
    move_to(resource_position)
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    # Check if we successfully harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
for resource_type, required_quantity in required_resources.items():
    actual_quantity = final_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Final check failed for {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
print("Successfully gathered all required resources")
print(f"Final inventory: {final_inventory}")

"""
Step 3: Craft stone furnaces. We need to craft 2 stone furnaces.
"""
# Craft stone furnaces
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=2)
print(f"Crafted {crafted_furnaces} stone furnaces")

# Check if we successfully crafted the stone furnaces
current_inventory = inspect_inventory()
furnaces_in_inventory = current_inventory.get(Prototype.StoneFurnace, 0)
assert furnaces_in_inventory >= 2, f"Failed to craft enough stone furnaces. Expected: 2, Actual: {furnaces_in_inventory}"
print("Successfully crafted 2 stone furnaces")
print(f"Current inventory after crafting: {current_inventory}")

"""
Step 4: Set up smelting area. We need to:
- Place 2 stone furnaces
- Fuel them with coal
"""
# Define the origin point
origin = Position(x=0, y=0)

# Place first stone furnace at the origin
move_to(origin)
furnace1 = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed first stone furnace at {furnace1.position}")

# Place second stone furnace to the right of the first one
furnace2 = place_entity_next_to(Prototype.StoneFurnace, direction=Direction.RIGHT, reference_position=furnace1.position)
print(f"Placed second stone furnace at {furnace2.position}")

# Now let's fuel both furnaces with coal
for furnace in [furnace1, furnace2]:
    # Insert 10 coal into each furnace
    fueled_furnace = insert_item(Prototype.Coal, furnace, quantity=10)
    # Check if coal was successfully inserted
    coal_in_furnace = fueled_furnace.fuel.get(Prototype.Coal, 0)
    assert coal_in_furnace > 0, "Failed to fuel stone furnace with coal"
    print(f"Fueled stone furnace at {fueled_furnace.position} with {coal_in_furnace} pieces of coal")

print("Successfully set up smelting area with two fueled stone furnaces")

"""
Step 5: Smelt iron plates. We need to:
- Smelt 40 iron ore into 40 iron plates
"""
# First, move to the first furnace
move_to(furnace1.position)

# Insert 20 iron ore into the first furnace
updated_furnace1 = insert_item(Prototype.IronOre, furnace1, quantity=20)
print("Inserted 20 Iron Ore into Furnace 1")

# Move to the second furnace
move_to(furnace2.position)

# Insert 20 iron ore into the second furnace
updated_furnace2 = insert_item(Prototype.IronOre, furnace2, quantity=20)
print("Inserted 20 Iron Ore into Furnace 2")

# Wait for smelting to complete (approximately 1 second per ore)
sleep(30)

# Attempt to extract iron plates from both furnaces
max_attempts = 5
for _ in range(max_attempts):
    # Extract from first furnace
    extract_item(Prototype.IronPlate, updated_furnace1.position, quantity=20)
    # Extract from second furnace
    extract_item(Prototype.IronPlate, updated_furnace2.position, quantity=20)
    # Check inventory
    current_inventory = inspect_inventory()
    iron_plates_in_inventory = current_inventory.get(Prototype.IronPlate, 0)
    if iron_plates_in_inventory >= 40:
        break
    sleep(10)

print(f"Extracted Iron Plates; Current Inventory: {current_inventory}")

# Final assertion to ensure we have enough iron plates
assert iron_plates_in_inventory >= 40, f"Failed to obtain required number of Iron Plates. Expected: 40, Actual: {iron_plates_in_inventory}"
print("Successfully obtained 40 Iron Plates")

"""
Step 6: Craft iron gear wheels. We need to:
- Craft 40 iron gear wheels (requires 80 iron plates)
"""
# Craft 40 Iron Gear Wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=40)
print(f"Crafted {crafted_gear_wheels} Iron Gear Wheels")

# Check if we successfully crafted the required number of gear wheels
current_inventory = inspect_inventory()
gear_wheels_in_inventory = current_inventory.get(Prototype.IronGearWheel, 0)
assert gear_wheels_in_inventory >= 40, f"Failed to craft required number of Iron Gear Wheels. Expected: 40, Actual: {gear_wheels_in_inventory}"
print(f"Successfully crafted 40 Iron Gear Wheels; Current Inventory: {current_inventory}")

"""
Step 7: Craft underground-belts. We need to:
- Craft 2 underground-belts (requires 20 iron gear wheels)
"""
# Craft 2 Underground Belts
crafted_underground_belts = craft_item(Prototype.UndergroundBelt, quantity=2)
print(f"Crafted {crafted_underground_belts} Underground Belts")

# Check if we successfully crafted the required number of underground belts
current_inventory = inspect_inventory()
underground_belts_in_inventory = current_inventory.get(Prototype.UndergroundBelt, 0)
assert underground_belts_in_inventory >= 2, f"Failed to craft required number of Underground Belts. Expected: 2, Actual: {underground_belts_in_inventory}"
print(f"Successfully crafted 2 Underground Belts; Current Inventory: {current_inventory}")

"""
Step 8: Craft fast-underground-belt. We need to:
- Craft 1 fast-underground-belt (requires 2 underground-belts and 20 iron gear wheels)
"""
# Craft 1 fast-underground-belt
crafted_fast_underground_belt = craft_item(Prototype.FastUndergroundBelt, quantity=1)
print(f"Crafted {crafted_fast_underground_belt} Fast Underground Belt")

# Check if we successfully crafted the required number of fast underground belts
current_inventory = inspect_inventory()
fast_underground_belts_in_inventory = current_inventory.get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belts_in_inventory >= 1, f"Failed to craft required number of Fast Underground Belts. Expected: 1, Actual: {fast_underground_belts_in_inventory}"
print(f"Successfully crafted 1 Fast Underground Belt; Current Inventory: {current_inventory}")

print("All objectives completed successfully!")

