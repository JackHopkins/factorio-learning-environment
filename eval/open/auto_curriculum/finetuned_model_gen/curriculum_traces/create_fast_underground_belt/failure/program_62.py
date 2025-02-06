

from instance import *

"""
Objective: Craft a fast-underground-belt from raw materials

Planning:
We need to craft a fast-underground-belt. To do this, we need to craft the following intermediate items:
- Iron gear wheels (40)
- Underground belts (2)

There are no entities on the map, so we need to craft everything from scratch.
We'll need to gather raw resources, set up smelting, and craft the required items.
"""

"""
Step 1: Print recipes
"""
# Print recipe for fast-underground-belt
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
print("fast-underground-belt recipe:")
print(fast_underground_belt_recipe)

# Print recipe for underground-belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print("underground-belt recipe:")
print(underground_belt_recipe)

# Print recipe for iron gear wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print("iron gear wheel recipe:")
print(iron_gear_wheel_recipe)

"""
Step 2: Gather raw resources
We need to mine the following resources:
- Iron ore (at least 80 for 160 iron plates)
- Copper ore (at least 4 for 4 copper plates)
- Coal (at least 40 for fueling the furnace)
- Stone (at least 5 for the stone furnace)
"""

# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 80),
    (Resource.CopperOre, 4),
    (Resource.Coal, 40),
    (Resource.Stone, 5)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    # Move to the resource
    move_to(resource_position)
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    # Check how much was actually harvested
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    # Print out what we did
    print(f"Harvested {actual_quantity} of {resource_type}")
    print(f"Current inventory: {current_inventory}")
    # Ensure we've gathered enough
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}"

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory after gathering all resources:")
print(final_inventory)

# Verify that we have at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 80, "Not enough Iron Ore"
assert final_inventory.get(Resource.CopperOre, 0) >= 4, "Not enough Copper Ore"
assert final_inventory.get(Resource.Coal, 0) >= 40, "Not enough Coal"
assert final_inventory.get(Resource.Stone, 0) >= 5, "Not enough Stone"

print("Successfully gathered all required resources!")

"""
Step 3: Craft and set up smelting infrastructure
- Craft 1 stone furnace
- Place the stone furnace
- Add coal to the furnace as fuel
"""

# Craft a stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 stone furnace")

# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed stone furnace at {furnace.position}")

# Add coal to the furnace as fuel
coal_in_inventory = inspect_inventory()[Prototype.Coal]
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=coal_in_inventory)
print("Inserted coal into the stone furnace")

"""
Step 4: Smelt iron plates
- Smelt 160 iron ore into 160 iron plates
"""

# Insert iron ore into the furnace
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print("Inserted Iron Ore into the Stone Furnace")

# Wait for smelting to complete
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_in_inventory)
sleep(total_smelting_time)

# Extract iron plates
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= iron_ore_in_inventory:
        break
    sleep(10)

print(f"Extracted Iron Plates; Current Inventory Count: {current_iron_plate_count}")
print(f"Current Inventory: {inspect_inventory()}")

"""
Step 5: Craft assembling machine
- Craft 1 assembling machine (requires 5 iron gear wheels, 9 iron plates, 3 electronic circuits)
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=5)
print("Crafted 5 iron gear wheels")

# Craft electronic circuits
craft_item(Prototype.ElectronicCircuit, quantity=3)
print("Crafted 3 electronic circuits")

# Craft assembling machine
craft_item(Prototype.AssemblingMachine1, quantity=1)
print("Crafted 1 assembling machine")

# Place the assembling machine
assembling_machine = place_entity(Prototype.AssemblingMachine1, position=origin)
print(f"Placed assembling machine at {assembling_machine.position}")

"""
Step 6: Craft iron gear wheels
- Use the assembling machine to craft 40 iron gear wheels
"""
# Insert iron plates into the assembling machine
iron_plates_in_inventory = inspect_inventory()[Prototype.IronPlate]
updated_assembling_machine = insert_item(Prototype.IronPlate, assembling_machine, quantity=iron_plates_in_inventory)
print("Inserted iron plates into the assembling machine")

# Set the recipe for the assembling machine
set_entity_recipe(updated_assembling_machine, Prototype.IronGearWheel)
print("Set recipe for iron gear wheels")

# Wait for crafting to complete
crafting_time_per_unit = 0.5
total_crafting_time = int(crafting_time_per_unit * 40)
sleep(total_crafting_time)

# Extract iron gear wheels
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronGearWheel, updated_assembling_machine.position, quantity=40)
    current_iron_gear_wheel_count = inspect_inventory().get(Prototype.IronGearWheel, 0)
    if current_iron_gear_wheel_count >= 40:
        break
    sleep(10)

print(f"Extracted Iron Gear Wheels; Current Inventory Count: {current_iron_gear_wheel_count}")
print(f"Current Inventory: {inspect_inventory()}")

"""
Step 7: Craft underground belts
- Use the assembling machine to craft 2 underground belts (requires 10 iron gear wheels, 20 iron plates)
"""
# Insert iron plates into the assembling machine
iron_plates_in_inventory = inspect_inventory()[Prototype.IronPlate]
updated_assembling_machine = insert_item(Prototype.IronPlate, updated_assembling_machine, quantity=iron_plates_in_inventory)
print("Inserted iron plates into the assembling machine")

# Set the recipe for the assembling machine
set_entity_recipe(updated_assembling_machine, Prototype.UndergroundBelt)
print("Set recipe for underground belts")

# Wait for crafting to complete
crafting_time_per_unit = 0.5
total_crafting_time = int(crafting_time_per_unit * 2)
sleep(total_crafting_time)

# Extract underground belts
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.UndergroundBelt, updated_assembling_machine.position, quantity=2)
    current_underground_belt_count = inspect_inventory().get(Prototype.UndergroundBelt, 0)
    if current_underground_belt_count >= 2:
        break
    sleep(10)

print(f"Extracted Underground Belts; Current Inventory Count: {current_underground_belt_count}")
print(f"Current Inventory: {inspect_inventory()}")

"""
Step 8: Craft fast-underground-belt
- Use the assembling machine to craft 1 fast-underground-belt (requires 2 iron gear wheels, 2 underground belts)
"""
# Set the recipe for the assembling machine
set_entity_recipe(updated_assembling_machine, Prototype.FastUndergroundBelt)
print("Set recipe for fast-underground-belt")

# Wait for crafting to complete
crafting_time_per_unit = 0.5
total_crafting_time = int(crafting_time_per_unit * 1)
sleep(total_crafting_time)

# Extract fast-underground-belt
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.FastUndergroundBelt, updated_assembling_machine.position, quantity=1)
    current_fast_underground_belt_count = inspect_inventory().get(Prototype.FastUndergroundBelt, 0)
    if current_fast_underground_belt_count >= 1:
        break
    sleep(10)

print(f"Extracted Fast-Underground-Belt; Current Inventory Count: {current_fast_underground_belt_count}")
print(f"Current Inventory: {inspect_inventory()}")

# Final verification
assert current_fast_underground_belt_count >= 1, "Failed to craft Fast-Underground-Belt"
print("Successfully crafted Fast-Underground-Belt!")

