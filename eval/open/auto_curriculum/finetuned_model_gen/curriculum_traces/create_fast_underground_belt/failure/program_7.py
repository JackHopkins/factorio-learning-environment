
from instance import *

"""
Step 1: Gather resources
- Mine at least 6 iron ore
- Mine at least 10 stone
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 6),
    (Resource.Stone, 10)
]

# Loop through each resource we need to gather
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
print("Final inventory:", final_inventory)

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 6, f"Not enough iron ore! Have {final_inventory.get(Resource.IronOre, 0)} but need 6"
assert final_inventory.get(Resource.Stone, 0) >= 10, f"Not enough stone! Have {final_inventory.get(Resource.Stone, 0)} but need 10"

print("Successfully gathered all required resources")

"""
Step 2: Craft a stone furnace
- Use 5 stone to craft a stone furnace
"""
# Craft a stone furnace
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted {crafted_furnaces} stone furnace(s)")

# Check if we successfully crafted the stone furnace
furnace_count = inspect_inventory().get(Prototype.StoneFurnace, 0)
assert furnace_count >= 1, f"Failed to craft stone furnace. Current count: {furnace_count}"

# Print current inventory state
current_inventory = inspect_inventory()
print("Current inventory after crafting stone furnace:", current_inventory)

"""
Step 3: Set up smelting operation
- Place the stone furnace
- Add coal (or wood) as fuel to the furnace
"""
# Place the stone furnace at origin
origin = Position(x=0, y=0)  # Origin point
move_to(origin)
placed_furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed stone furnace at {placed_furnace.position}")

# Gather wood for fuel if needed
wood_in_inventory = inspect_inventory().get(Prototype.Wood, 0)
if wood_in_inventory < 5:  # Assuming we need at least 5 units of wood for fuel
    # Find nearest tree
    tree_position = nearest(Resource.Wood)
    move_to(tree_position)
    # Harvest wood
    harvested = harvest_resource(tree_position, 5)
    print(f"Harvested {harvested} units of wood")
    # Verify that we have enough wood
    wood_in_inventory = inspect_inventory().get(Prototype.Wood, 0)
    assert wood_in_inventory >= 5, f"Failed to gather enough wood! Current count: {wood_in_inventory}"

# Insert wood as fuel into the stone furnace
updated_furnace = insert_item(Prototype.Wood, placed_furnace, quantity=5)
print("Inserted wood as fuel into the stone furnace")

# Verify that the furnace has fuel
fuel_count = updated_furnace.fuel.get(Prototype.Wood, 0)
assert fuel_count > 0, "Failed to insert fuel into the stone furnace"

# Print current inventory state
current_inventory = inspect_inventory()
print("Current inventory after setting up smelting operation:", current_inventory)

"""
Step 4: Smelt iron plates
- Smelt 6 iron ore into 6 iron plates
"""
# Insert Iron Ore into Furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} Iron Ore into the Stone Furnace")

# Wait for smelting process to complete
smelt_time_per_unit = 0.7
total_smelt_time = int(smelt_time_per_unit * iron_ore_in_inventory)
sleep(total_smelt_time)

# Extract Iron Plates from Furnace
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= iron_ore_in_inventory:
        break
    sleep(10)

print(f"Extracted {current_iron_plate_count} Iron Plates from Furnace")

# Verify that we have enough Iron Plates
assert current_iron_plate_count >= 6, f"Failed to obtain required number of Iron Plates! Current count: {current_iron_plate_count}"

# Print final inventory state after smelting
final_inventory_after_smelting = inspect_inventory()
print("Final inventory after smelting operation:", final_inventory_after_smelting)

"""
Step 5: Craft iron gear wheels
- Craft 4 iron gear wheels (each requires 2 iron plates)
"""
# Craft Iron Gear Wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=4)
print(f"Crafted {crafted_gear_wheels} Iron Gear Wheel(s)")

# Check if we successfully crafted the Iron Gear Wheels
gear_wheel_count = inspect_inventory().get(Prototype.IronGearWheel, 0)
assert gear_wheel_count >= 4, f"Failed to craft enough Iron Gear Wheels. Current count: {gear_wheel_count}"

# Print current inventory state after crafting Iron Gear Wheels
current_inventory_after_crafting_gears = inspect_inventory()
print("Current inventory after crafting Iron Gear Wheels:", current_inventory_after_crafting_gears)

"""
Step 6: Craft underground belts
- Craft 2 underground belts (each requires 2 iron gear wheels and 1 iron plate)
"""
# Craft Underground Belts
crafted_underground_belts = craft_item(Prototype.UndergroundBelt, quantity=2)
print(f"Crafted {crafted_underground_belts} Underground Belt(s)")

# Check if we successfully crafted the Underground Belts
underground_belt_count = inspect_inventory().get(Prototype.UndergroundBelt, 0)
assert underground_belt_count >= 2, f"Failed to craft enough Underground Belts. Current count: {underground_belt_count}"

# Print current inventory state after crafting Underground Belts
current_inventory_after_crafting_underground_belts = inspect_inventory()
print("Current inventory after crafting Underground Belts:", current_inventory_after_crafting_underground_belts)

"""
Step 7: Craft fast-underground-belt
- Craft 1 fast-underground-belt (requires 2 iron gear wheels and 2 underground belts)
"""
# Craft Fast Underground Belt
crafted_fast_underground_belt = craft_item(Prototype.FastUndergroundBelt, quantity=1)
print(f"Crafted {crafted_fast_underground_belt} Fast Underground Belt(s)")

# Check if we successfully crafted the Fast Underground Belt
fast_underground_belt_count = inspect_inventory().get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belt_count >= 1, f"Failed to craft Fast Underground Belt. Current count: {fast_underground_belt_count}"

# Print final inventory state
final_inventory = inspect_inventory()
print("Final inventory after crafting Fast Underground Belt:", final_inventory)

print("Successfully completed all steps and crafted a Fast Underground Belt!")

