

from factorio_instance import *

"""
Step 1: Gather raw resources
- Mine at least 5 stone
- Mine at least 10 iron ore
- Mine some coal (at least 5) for fuel
"""
resources_to_gather = [
    (Resource.Stone, 5),
    (Resource.IronOre, 10),
    (Resource.Coal, 5)
]

for resource_type, required_amount in resources_to_gather:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_amount)
    current_inventory = inspect_inventory()
    actual_amount = current_inventory.get(resource_type, 0)
    assert actual_amount >= required_amount, f"Failed to gather enough {resource_type}. Required: {required_amount}, Actual: {actual_amount}"
    print(f"Successfully gathered {actual_amount} {resource_type}")

print("Final inventory after gathering resources:")
print(inspect_inventory())

"""
Step 2: Craft the Stone Furnace
- Use 5 stone to craft 1 Stone Furnace
"""
craft_item(Prototype.StoneFurnace, 1)
print("Crafted 1 Stone Furnace")
print("Inventory after crafting Stone Furnace:")
print(inspect_inventory())

"""
Step 3: Set up the smelting area
- Move to a suitable location (e.g., origin at 0,0)
- Place the Stone Furnace
"""
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed Stone Furnace at {furnace.position}")

"""
Step 4: Prepare the furnace for smelting
- Insert 5 coal into the furnace as fuel
"""
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
assert coal_in_inventory >= 5, f"Insufficient coal in inventory. Expected at least 5 but found {coal_in_inventory}"

updated_furnace = insert_item(Prototype.Coal, furnace, quantity=5)
print("Inserted 5 coal into the Stone Furnace")

"""
Step 5: Smelt iron ore into iron plates
- Insert all 10 iron ore into the furnace
- Wait for smelting to complete
- Extract the 10 iron plates
"""
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
assert iron_ore_in_inventory >= 10, f"Insufficient iron ore in inventory. Expected at least 10 but found {iron_ore_in_inventory}"

updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=10)
print("Inserted 10 iron ore into the Stone Furnace")

smelting_time_per_unit = 3.2
total_smelting_time = smelting_time_per_unit * 10
sleep(total_smelting_time)

max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=10)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= 10:
        break
    sleep(5)

print(f"Extracted iron plates; Current inventory count: {current_iron_plate_count}")
assert current_iron_plate_count >= 10, f"Failed to obtain required number of Iron Plates! Expected: 10, Found: {current_iron_plate_count}"

print("Successfully completed the iron plate production setup!")

