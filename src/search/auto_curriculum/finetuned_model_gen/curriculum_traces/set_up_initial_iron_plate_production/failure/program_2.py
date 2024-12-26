

from factorio_instance import *

"""
Objective: Set up initial iron plate production

Planning:
We need to craft a stone furnace and produce iron plates. 
We'll need to mine stone for the furnace and iron ore for the plates.
We'll also need coal to fuel the furnace.
"""

"""
Step 1: Print recipes
"""
print("Recipes:")
print("Stone Furnace: Requires 5 stone")
print("Iron Plate: Requires smelting 1 iron ore")
print("Coal: Used as fuel")

"""
Step 2: Gather resources
- Mine stone for the furnace
- Mine iron ore for smelting
- Mine coal for fuel
"""
resources_to_gather = [
    (Resource.Stone, 5),
    (Resource.IronOre, 10),
    (Resource.Coal, 10)
]

for resource_type, required_quantity in resources_to_gather:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

final_inventory = inspect_inventory()
print(f"Final inventory after gathering resources: {final_inventory}")

"""
Step 3: Craft and place stone furnace
"""
craft_item(Prototype.StoneFurnace, quantity=1)
furnace_position = Position(x=0, y=0)
move_to(furnace_position)
furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)
print("Placed stone furnace")

"""
Step 4: Fuel the furnace
"""
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
assert coal_in_inventory >= 5, f"Not enough coal in inventory to fuel furnace. Required: 5, Actual: {coal_in_inventory}"
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=5)
print("Inserted coal into the furnace")

"""
Step 5: Smelt iron plates
"""
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
assert iron_ore_in_inventory >= 10, f"Not enough iron ore in inventory. Required: 10, Actual: {iron_ore_in_inventory}"
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=10)
print("Inserted iron ore into the furnace")

# Wait for smelting to complete
smelting_time_per_unit = 3.2
total_smelting_time = int(smelting_time_per_unit * 10)
sleep(total_smelting_time)

# Extract iron plates
for _ in range(5):  # Try up to 5 times to ensure all plates are extracted
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=10)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= 10:
        break
    sleep(5)

print(f"Produced {current_iron_plate_count} iron plates")
assert current_iron_plate_count >= 10, f"Failed to produce enough iron plates. Expected: 10, Actual: {current_iron_plate_count}"

final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

