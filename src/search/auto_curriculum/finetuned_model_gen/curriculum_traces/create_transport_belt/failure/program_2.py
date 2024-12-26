
from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- stone-furnace
- transport-belt
- iron-gear-wheel
- iron-plate
"""
# Get the recipes for each item
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
iron_plate_recipe = get_prototype_recipe(Prototype.IronPlate)  # This will be None as it's a base item

# Print the recipes
print("Recipes:")
print(f"Stone Furnace: {stone_furnace_recipe}")
print(f"Transport Belt: {transport_belt_recipe}")
print(f"Iron Gear Wheel: {iron_gear_wheel_recipe}")
print(f"Iron Plate: {iron_plate_recipe}")

"""
Step 2: Gather resources. We need to gather the following resources:
- stone: 6 (5 for the furnace, 1 extra just in case)
- coal: 1 (for fuel)
- iron-ore: 3 (2 for plates, 1 extra)
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 6),
    (Resource.Coal, 1),
    (Resource.IronOre, 3)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    
    # Move to the resource position
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    
    assert actual_quantity >= required_quantity, f"Failed to harvest enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

print("All necessary resources have been gathered.")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final Inventory: {final_inventory}")

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.Stone, 0) >= 6, "Not enough stone in final inventory"
assert final_inventory.get(Resource.Coal, 0) >= 1, "Not enough coal in final inventory"
assert final_inventory.get(Resource.IronOre, 0) >= 3, "Not enough iron ore in final inventory"

"""
Step 3: Craft stone furnace. We need to craft 1 stone furnace using 5 stone.
"""
# Move to a safe position for crafting
move_to(Position(x=0, y=0))

# Craft a stone furnace
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)

# Check how many stone furnaces are in the inventory after crafting
inventory_after_crafting = inspect_inventory()
stone_furnaces_in_inventory = inventory_after_crafting.get(Prototype.StoneFurnace, 0)

assert stone_furnaces_in_inventory >= 1, f"Failed to craft stone furnace. Expected at least 1 but got {stone_furnaces_in_inventory}"

print(f"Successfully crafted {stone_furnaces_in_inventory} Stone Furnace(s)")

"""
Step 4: Place and fuel furnace. We need to:
- Place the stone furnace on the ground
- Add 1 coal to the furnace as fuel
"""
# Place the stone furnace at the origin
furnace_position = Position(x=0, y=0)
stone_furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)
print(f"Placed Stone Furnace at {stone_furnace.position}")

# Insert coal into the stone furnace as fuel
coal_quantity = 1
updated_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=coal_quantity)
print("Inserted coal into Stone Furnace.")

# Verify that the furnace has been fueled
coal_in_furnace = updated_furnace.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace > 0, "Failed to fuel Stone Furnace"

print("Successfully placed and fueled the Stone Furnace.")

"""
Step 5: Smelt iron plates. We need to:
- Insert 2 iron ore into the furnace
- Wait for the smelting process to complete
- Extract 2 iron plates from the furnace
"""
# Insert iron ore into the stone furnace
iron_ore_quantity = 2
updated_furnace = insert_item(Prototype.IronOre, stone_furnace, quantity=iron_ore_quantity)
print("Inserted iron ore into Stone Furnace.")

# Calculate expected number of iron plates
initial_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
expected_final_iron_plates = initial_iron_plates + iron_ore_quantity

# Wait for smelting process to complete (assuming each unit takes about 1 second)
smelting_time_per_unit = 1
total_smelting_time = smelting_time_per_unit * iron_ore_quantity
sleep(total_smelting_time)

# Try extracting multiple times if needed
max_attempts_to_extract = 5
for attempt in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_quantity)
    current_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
    
    if current_iron_plates >= expected_final_iron_plates:
        break
    
    sleep(10)  # Wait a bit more if not all plates are ready

print(f"Extracted {iron_ore_quantity} Iron Plates from Stone Furnace.")

# Verify that we have extracted enough iron plates
final_inventory_count = inspect_inventory().get(Prototype.IronPlate, 0)
assert final_inventory_count >= expected_final_iron_plates, f"Failed to extract enough Iron Plates. Expected: {expected_final_iron_plates}, Actual: {final_inventory_count}"

print(f"Successfully extracted {iron_ore_quantity} Iron Plates.")

"""
Step 6: Craft iron gear wheel. We need to craft 1 iron gear wheel using 2 iron plates.
"""
# Craft an iron gear wheel
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=1)

# Check how many iron gear wheels are in the inventory after crafting
inventory_after_crafting = inspect_inventory()
gear_wheels_in_inventory = inventory_after_crafting.get(Prototype.IronGearWheel, 0)

assert gear_wheels_in_inventory >= 1, f"Failed to craft Iron Gear Wheel. Expected at least 1 but got {gear_wheels_in_inventory}"

print(f"Successfully crafted {gear_wheels_in_inventory} Iron Gear Wheel(s)")

"""
Step 7: Craft transport belt. We need to craft 1 transport belt using 1 iron gear wheel and 1 iron plate.
"""
# Craft a transport belt
crafted_transport_belts = craft_item(Prototype.TransportBelt, quantity=1)

# Check how many transport belts are in the inventory after crafting
inventory_after_crafting = inspect_inventory()
transport_belts_in_inventory = inventory_after_crafting.get(Prototype.TransportBelt, 0)

assert transport_belts_in_inventory >= 1, f"Failed to craft Transport Belt. Expected at least 1 but got {transport_belts_in_inventory}"

print(f"Successfully crafted {transport_belts_in_inventory} Transport Belt(s)")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final Inventory: {final_inventory}")

# Assert that we have at least the required quantities
assert final_inventory.get(Prototype.TransportBelt, 0) >= 1, "Not enough Transport Belts in final inventory"

print("All steps completed successfully!")

