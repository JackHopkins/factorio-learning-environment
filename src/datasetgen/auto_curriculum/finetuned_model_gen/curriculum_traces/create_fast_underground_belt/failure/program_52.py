

from factorio_instance import *


"""
Step 1: Print recipes. We need to print the recipes for fast-underground-belt, underground-belt and iron-gear-wheel
"""
# Print the recipe for fast-underground-belt
print("FastUndergroundBelt recipe:")
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
print(fast_underground_belt_recipe)

# Print the recipe for underground-belt
print("UndergroundBelt recipe:")
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print(underground_belt_recipe)

# Print the recipe for iron-gear-wheel
print("IronGearWheel recipe:")
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(iron_gear_wheel_recipe)

"""
Step 2: Gather resources. We need to gather iron ore and coal. We need at least 40 iron plates for the gear wheels and underground belts, and some coal for fuel.
"""

# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 40),
    (Resource.Coal, 20),
    (Resource.Stone, 5)  # We need stone to craft a furnace
]

# Loop through each resource and gather it
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
print(f"Final inventory: {final_inventory}")

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 40, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 20, "Not enough Coal"
assert final_inventory.get(Resource.Stone, 0) >= 5, "Not enough Stone"

print("Successfully gathered all required resources")

"""
Step 3: Set up smelting. We need to craft a stone furnace and set it up to smelt the iron ore into iron plates. We need to ensure we have enough coal for fuel.
"""

# Craft a stone furnace
print("Crafting stone furnace...")
craft_item(Prototype.StoneFurnace, 1)

# Place the stone furnace near the player's current position
player_position = Position(x=0, y=0)  # Assume player is at origin for simplicity
furnace = place_entity(Prototype.StoneFurnace, position=player_position)

print(f"Placed stone furnace at {furnace.position}")

# Insert coal into the furnace as fuel
coal_quantity = 10  # Use 10 units of coal for fuel
updated_furnace = insert_item(Prototype.Coal, furnace, coal_quantity)
print(f"Inserted {coal_quantity} units of coal into the furnace")

# Insert iron ore into the furnace
iron_ore_quantity = 40  # Use all available iron ore
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, iron_ore_quantity)
print(f"Inserted {iron_ore_quantity} units of iron ore into the furnace")

# Wait for smelting to complete
smelting_time = 40 * 0.7  # 0.7 seconds per unit of iron ore
sleep(smelting_time)

# Extract iron plates from the furnace
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, iron_ore_quantity)
    iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
    if iron_plates_in_inventory >= 40:
        break
    sleep(10)  # Wait a bit before trying again

print(f"Extracted {iron_ore_quantity} iron plates from the furnace")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory after smelting: {final_inventory}")

# Assert that we have at least the required quantities
assert final_inventory.get(Prototype.IronPlate, 0) >= 40, "Not enough Iron Plates"

print("Successfully completed smelting process")

"""
Step 4: Craft iron gear wheels. We need to craft 40 iron gear wheels, which requires 80 iron plates.
"""

# Print the recipe for Iron Gear Wheel
recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(f"Iron Gear Wheel Recipe: {recipe}")

# Check current inventory for Iron Plates
iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
print(f"Current Iron Plates in Inventory: {iron_plates_in_inventory}")

# Ensure there are enough Iron Plates to craft Iron Gear Wheels
required_iron_plates = 80
assert iron_plates_in_inventory >= required_iron_plates, f"Not enough Iron Plates to craft Iron Gear Wheels. Required: {required_iron_plates}, Available: {iron_plates_in_inventory}"

# Craft 40 Iron Gear Wheels
craft_item(Prototype.IronGearWheel, 40)

# Verify that 40 Iron Gear Wheels have been crafted
iron_gear_wheels_in_inventory = inspect_inventory().get(Prototype.IronGearWheel, 0)
assert iron_gear_wheels_in_inventory >= 40, f"Failed to craft 40 Iron Gear Wheels. Current count: {iron_gear_wheels_in_inventory}"

print(f"Successfully crafted 40 Iron Gear Wheels. Current Inventory: {inspect_inventory()}")

"""
Step 5: Craft underground belts. We need to craft 2 underground belts, which requires 20 iron gear wheels and 20 iron plates.
"""

# Print the recipe for Underground Belt
recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print(f"Underground Belt Recipe: {recipe}")

# Check current inventory for required materials
iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
iron_gear_wheels_in_inventory = inspect_inventory().get(Prototype.IronGearWheel, 0)

print(f"Current Iron Plates in Inventory: {iron_plates_in_inventory}")
print(f"Current Iron Gear Wheels in Inventory: {iron_gear_wheels_in_inventory}")

# Ensure there are enough Iron Plates and Iron Gear Wheels to craft Underground Belts
required_iron_plates = 20
required_iron_gear_wheels = 20

assert iron_plates_in_inventory >= required_iron_plates, f"Not enough Iron Plates to craft Underground Belts. Required: {required_iron_plates}, Available: {iron_plates_in_inventory}"
assert iron_gear_wheels_in_inventory >= required_iron_gear_wheels, f"Not enough Iron Gear Wheels to craft Underground Belts. Required: {required_iron_gear_wheels}, Available: {iron_gear_wheels_in_inventory}"

# Craft 2 Underground Belts
craft_item(Prototype.UndergroundBelt, 2)

# Verify that 2 Underground Belts have been crafted
underground_belts_in_inventory = inspect_inventory().get(Prototype.UndergroundBelt, 0)
assert underground_belts_in_inventory >= 2, f"Failed to craft 2 Underground Belts. Current count: {underground_belts_in_inventory}"

print(f"Successfully crafted 2 Underground Belts. Current Inventory: {inspect_inventory()}")

"""
Step 6: Craft fast-underground-belt. We need to craft 1 fast-underground-belt, which requires 2 underground belts and 40 iron gear wheels.
"""

# Print the recipe for Fast Underground Belt
recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
print(f"Fast Underground Belt Recipe: {recipe}")

# Check current inventory for required materials
underground_belts_in_inventory = inspect_inventory().get(Prototype.UndergroundBelt, 0)
iron_gear_wheels_in_inventory = inspect_inventory().get(Prototype.IronGearWheel, 0)

print(f"Current Underground Belts in Inventory: {underground_belts_in_inventory}")
print(f"Current Iron Gear Wheels in Inventory: {iron_gear_wheels_in_inventory}")

# Ensure there are enough Underground Belts and Iron Gear Wheels to craft Fast Underground Belt
required_underground_belts = 2
required_iron_gear_wheels = 40

assert underground_belts_in_inventory >= required_underground_belts, f"Not enough Underground Belts to craft Fast Underground Belt. Required: {required_underground_belts}, Available: {underground_belts_in_inventory}"
assert iron_gear_wheels_in_inventory >= required_iron_gear_wheels, f"Not enough Iron Gear Wheels to craft Fast Underground Belt. Required: {required_iron_gear_wheels}, Available: {iron_gear_wheels_in_inventory}"

# Craft 1 Fast Underground Belt
craft_item(Prototype.FastUndergroundBelt, 1)

# Verify that 1 Fast Underground Belt has been crafted
fast_underground_belts_in_inventory = inspect_inventory().get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belts_in_inventory >= 1, f"Failed to craft 1 Fast Underground Belt. Current count: {fast_underground_belts_in_inventory}"

print(f"Successfully crafted 1 Fast Underground Belt. Current Inventory: {inspect_inventory()}")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory after crafting Fast Underground Belt: {final_inventory}")

# Assert that we have at least 1 Fast Underground Belt in our inventory
assert final_inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, "Not enough Fast Underground Belts in inventory"

print("Successfully completed crafting process and verified presence of required items in inventory")

