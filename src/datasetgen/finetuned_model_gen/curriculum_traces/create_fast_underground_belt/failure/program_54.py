
from factorio_instance import *

"""
Step 1: Print out recipes for the items we need to craft
"""

# Print recipe for iron-gear-wheel
print("Iron Gear Wheel Recipe:")
print("Ingredients: 2 iron plates")
print("Crafting time: 0.5 seconds")

# Print recipe for underground-belt
print("\nUnderground Belt Recipe:")
print("Ingredients: 10 iron gear wheels, 10 iron plates")
print("Crafting time: 1 second")

# Print recipe for fast-underground-belt
print("\nFast Underground Belt Recipe:")
print("Ingredients: 2 underground belts, 40 iron gear wheels")
print("Crafting time: 1 second")


"""
Step 2: Gather resources. We need to mine iron ore and coal. Let's get at least 60 iron ore and 30 coal.
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 60),
    (Resource.Coal, 30)
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
    print(f"Harvested {harvested} units of {resource_type}")

    # Check inventory to confirm successful harvesting
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}. Current inventory: {current_inventory}")

print("Finished gathering all necessary resources.")
print(f"Final inventory: {inspect_inventory()}")

"""
Step 3: Set up smelting operation. We need to craft and place a stone furnace, then smelt the iron ore into iron plates.
"""
# Craft a stone furnace
stone_furnace_crafted = craft_item(Prototype.StoneFurnace, quantity=1)
assert stone_furnace_crafted == 1, f"Failed to craft stone furnace. Expected to craft 1, but crafted {stone_furnace_crafted}"
print("Successfully crafted a stone furnace")

# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed stone furnace at {furnace.position}")

# Insert coal into the stone furnace as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=30)
coal_in_furnace = updated_furnace.fuel.get(Prototype.Coal, 0)
print(f"Inserted {coal_in_furnace} coal into the stone furnace")

# Insert iron ore into the stone furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} iron ore into the stone furnace")

# Wait for smelting to complete
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_in_inventory)
sleep(total_smelting_time)

# Extract iron plates from the furnace
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
    if iron_plates_in_inventory >= iron_ore_in_inventory:
        break
    sleep(10)

print(f"Extracted {iron_plates_in_inventory} iron plates from the stone furnace")

# Verify that we have enough iron plates
required_iron_plates = 60
assert iron_plates_in_inventory >= required_iron_plates, f"Failed to obtain enough iron plates. Required: {required_iron_plates}, Actual: {iron_plates_in_inventory}"
print(f"Successfully obtained {iron_plates_in_inventory} iron plates")

"""
Step 4: Craft iron-gear-wheels. We need to craft 40 iron-gear-wheels.
"""
# Craft 40 iron gear wheels
iron_gear_wheels_crafted = craft_item(Prototype.IronGearWheel, quantity=40)
print(f"Crafted {iron_gear_wheels_crafted} iron gear wheels")

# Verify that we have crafted enough iron gear wheels
iron_gear_wheels_in_inventory = inspect_inventory().get(Prototype.IronGearWheel, 0)
required_iron_gear_wheels = 40
assert iron_gear_wheels_in_inventory >= required_iron_gear_wheels, f"Failed to craft enough iron gear wheels. Required: {required_iron_gear_wheels}, Actual: {iron_gear_wheels_in_inventory}"
print(f"Successfully crafted {iron_gear_wheels_in_inventory} iron gear wheels")

"""
Step 5: Craft underground-belts. We need to craft 4 underground-belts.
"""
# Craft 4 underground belts
underground_belts_crafted = craft_item(Prototype.UndergroundBelt, quantity=4)
print(f"Crafted {underground_belts_crafted} underground belts")

# Verify that we have crafted enough underground belts
underground_belts_in_inventory = inspect_inventory().get(Prototype.UndergroundBelt, 0)
required_underground_belts = 4
assert underground_belts_in_inventory >= required_underground_belts, f"Failed to craft enough underground belts. Required: {required_underground_belts}, Actual: {underground_belts_in_inventory}"
print(f"Successfully crafted {underground_belts_in_inventory} underground belts")

"""
Step 6: Craft fast-underground-belt. We need to craft 1 fast-underground-belt.
"""
# Craft 1 fast underground belt
fast_underground_belt_crafted = craft_item(Prototype.FastUndergroundBelt, quantity=1)
print(f"Crafted {fast_underground_belt_crafted} fast underground belt")

# Verify that we have crafted a fast underground belt
fast_underground_belts_in_inventory = inspect_inventory().get(Prototype.FastUndergroundBelt, 0)
required_fast_underground_belts = 1
assert fast_underground_belts_in_inventory >= required_fast_underground_belts, f"Failed to craft a fast underground belt. Required: {required_fast_underground_belts}, Actual: {fast_underground_belts_in_inventory}"
print(f"Successfully crafted {fast_underground_belts_in_inventory} fast underground belt")

print("Objective completed successfully!")

