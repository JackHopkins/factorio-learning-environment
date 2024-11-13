

from factorio_instance import *

"""
Objective: Create a burner-inserter
Planning:
We need to create a burner-inserter from scratch. 
There are no entities on the map and the inventory is empty.
We'll need to gather resources, craft intermediate items, and finally craft the burner-inserter.
"""

"""
Step 1: Print recipes
"""
print("Recipes:")
print("burner-inserter: 1 iron gear wheel, 1 iron plate")
print("firearm-magazine: 4 iron plates")
print("stone-furnace: 5 stone")

"""
Step 2: Gather resources
- Mine stone for stone furnace
- Mine iron ore for iron plates
- Mine coal for fuel
"""
resources_to_gather = [
    (Resource.Stone, 6),  # 5 for furnace, 1 extra
    (Resource.IronOre, 19),  # 19 total (8 for plates, 2 for gear wheel, 4 for magazine, 1 for inserter, 4 extra)
    (Resource.Coal, 2)  # 2 for fuel
]

for resource_type, required_quantity in resources_to_gather:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

"""
Step 3: Craft stone furnace
"""
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 stone furnace")

"""
Step 4: Set up smelting operation
- Place stone furnace
- Add coal as fuel
- Smelt iron ore into iron plates
"""
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)

# Fuel the furnace
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=2)
print("Inserted coal into the stone furnace")

# Smelt iron ore into iron plates
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print("Inserted iron ore into the stone furnace")

# Wait for smelting to complete
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_in_inventory)
sleep(total_smelting_time)

# Extract iron plates
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= 8:
        break
    sleep(10)

print(f"Extracted {current_iron_plate_count} iron plates")
assert current_iron_plate_count >= 8, f"Failed to obtain required number of iron plates. Expected: 8, Actual: {current_iron_plate_count}"

"""
Step 5: Craft intermediate items
- Craft 1 iron gear wheel (requires 2 iron plates)
- Craft 1 firearm magazine (requires 4 iron plates)
"""
craft_item(Prototype.IronGearWheel, quantity=1)
print("Crafted 1 iron gear wheel")

craft_item(Prototype.FirearmMagazine, quantity=1)
print("Crafted 1 firearm magazine")

"""
Step 6: Craft burner inserter
"""
craft_item(Prototype.BurnerInserter, quantity=1)
print("Crafted 1 burner inserter")

# Verify that we have crafted the burner inserter
burner_inserter_count = inspect_inventory().get(Prototype.BurnerInserter, 0)
assert burner_inserter_count >= 1, f"Failed to craft burner inserter. Expected: 1, Actual: {burner_inserter_count}"
print(f"Successfully crafted {burner_inserter_count} burner inserter(s)")

