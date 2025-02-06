

from instance import *

"""
Objective: Create a transport belt from scratch

Planning:
We need to craft a transport belt, which requires 1 iron gear wheel and 1 iron plate.
Since we have no entities on the map and an empty inventory, we need to start from scratch.
We'll need to gather resources, craft a furnace, smelt iron plates, and then craft the transport belt.
"""

"""
Step 1: Print recipes
We need to print the recipes for transport belt, iron plate, and iron gear wheel
"""
# Get and print recipes
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
iron_plate_recipe = get_prototype_recipe(Prototype.IronPlate)
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)

print("Transport Belt Recipe:")
print(transport_belt_recipe)
print("\nIron Plate Recipe:")
print(iron_plate_recipe)
print("\nIron Gear Wheel Recipe:")
print(iron_gear_wheel_recipe)

"""
Step 2: Gather resources
- Mine at least 2 iron ore
- Mine at least 5 stone (for furnace)
- Mine at least 2 coal (for fuel)
"""
# Define resources to gather
resources_to_gather = [
    (Resource.IronOre, 2),
    (Resource.Stone, 5),
    (Resource.Coal, 2)
]

# Gather resources
for resource_type, required_quantity in resources_to_gather:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    
    # Verify we harvested the correct amount
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory after gathering resources:")
print(final_inventory)

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 2, "Not enough Iron Ore"
assert final_inventory.get(Resource.Stone, 0) >= 5, "Not enough Stone"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Not enough Coal"

print("Successfully gathered all required resources!")

"""
Step 3: Craft stone furnace
- Craft 1 stone furnace using 5 stone
"""
# Craft stone furnace
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
assert crafted_furnaces == 1, f"Failed to craft Stone Furnace. Expected to craft 1, but crafted {crafted_furnaces}"
print("Successfully crafted 1 Stone Furnace")

# Check inventory to confirm
inventory_after_crafting = inspect_inventory()
furnaces_in_inventory = inventory_after_crafting.get(Prototype.StoneFurnace, 0)
assert furnaces_in_inventory >= 1, f"Stone Furnace not found in inventory after crafting. Expected at least 1, but found {furnaces_in_inventory}"
print(f"Stone Furnace is now in inventory. Current count: {furnaces_in_inventory}")

"""
Step 4: Set up smelting
- Place the stone furnace
- Add coal to the furnace as fuel
- Smelt 2 iron ore into iron plates
"""
# Place the stone furnace at the origin point
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print("Placed Stone Furnace at the origin")

# Add coal to the furnace as fuel
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
if coal_in_inventory > 0:
    updated_furnace = insert_item(Prototype.Coal, furnace, quantity=coal_in_inventory)
    print(f"Inserted {coal_in_inventory} Coal into the Stone Furnace")
else:
    raise Exception("No coal available in inventory to fuel the furnace")

# Insert iron ore into the furnace for smelting
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
if iron_ore_in_inventory > 0:
    updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
    print(f"Inserted {iron_ore_in_inventory} Iron Ore into the Stone Furnace")
else:
    raise Exception("No Iron Ore available in inventory to insert into the furnace")

# Wait for smelting to complete
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_in_inventory)
sleep(total_smelting_time)

# Extract iron plates from the furnace
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= iron_ore_in_inventory:
        break
    sleep(5)

print(f"Extracted {current_iron_plate_count} Iron Plates from the Stone Furnace")
print(f"Current Inventory: {inspect_inventory()}")

# Verify that we have at least 2 iron plates
assert current_iron_plate_count >= 2, f"Failed to obtain required number of Iron Plates. Expected at least 2, but got {current_iron_plate_count}"
print("Successfully obtained required number of Iron Plates!")

"""
Step 5: Craft iron gear wheel
- Craft 1 iron gear wheel using 1 iron plate
"""
# Check current inventory for available Iron Plates
iron_plates_available = inspect_inventory().get(Prototype.IronPlate, 0)
print(f"Iron Plates available before crafting: {iron_plates_available}")

# Craft Iron Gear Wheel
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=1)
assert crafted_gear_wheels == 1, f"Failed to craft Iron Gear Wheel. Expected to craft 1, but crafted {crafted_gear_wheels}"

# Verify that we have crafted an Iron Gear Wheel
iron_gear_wheel_count = inspect_inventory().get(Prototype.IronGearWheel, 0)
assert iron_gear_wheel_count >= 1, f"Failed to obtain required number of Iron Gear Wheels. Expected at least 1, but got {iron_gear_wheel_count}"
print(f"Successfully crafted {iron_gear_wheel_count} Iron Gear Wheel(s)")

# Check remaining inventory for available Iron Plates
remaining_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
print(f"Remaining Iron Plates after crafting: {remaining_iron_plate_count}")

"""
Step 6: Craft transport belt
- Craft 1 transport belt using 1 iron gear wheel and 1 iron plate
"""
# Check current inventory for available Iron Gear Wheels and Iron Plates
iron_gear_wheels_available = inspect_inventory().get(Prototype.IronGearWheel, 0)
iron_plates_available = inspect_inventory().get(Prototype.IronPlate, 0)
print(f"Iron Gear Wheels available before crafting: {iron_gear_wheels_available}")
print(f"Iron Plates available before crafting: {iron_plates_available}")

# Craft Transport Belt
crafted_transport_belts = craft_item(Prototype.TransportBelt, quantity=1)
assert crafted_transport_belts == 1, f"Failed to craft Transport Belt. Expected to craft 1, but crafted {crafted_transport_belts}"

# Verify that we have crafted a Transport Belt
transport_belt_count = inspect_inventory().get(Prototype.TransportBelt, 0)
assert transport_belt_count >= 1, f"Failed to obtain required number of Transport Belts. Expected at least 1, but got {transport_belt_count}"
print(f"Successfully crafted {transport_belt_count} Transport Belt(s)")

print("Objective completed: Created transport-belt")

