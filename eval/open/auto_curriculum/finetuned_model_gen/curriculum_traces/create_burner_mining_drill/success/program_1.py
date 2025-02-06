

from instance import *

"""
Objective: Craft a burner mining drill from scratch

Planning:
We need to craft a burner mining drill, which requires:
- 3 iron gear wheels
- 1 stone furnace
- 3 iron plates

In total, we need at least 9 iron plates and 5 stone.
We also need coal for smelting.

Steps:
1. Print recipes for required items
2. Gather raw resources (iron ore, coal, stone)
3. Craft a stone furnace
4. Smelt iron plates
5. Craft iron gear wheels
6. Craft the burner mining drill
"""

"""
Step 1: Print recipes for required items
"""
# Get and print recipe for burner mining drill
drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
print(f"Burner Mining Drill Recipe: {drill_recipe}")

# Get and print recipe for stone furnace
furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace Recipe: {furnace_recipe}")

# Get and print recipe for iron gear wheel
gear_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(f"Iron Gear Wheel Recipe: {gear_recipe}")

# Get and print recipe for iron plate
iron_plate_recipe = get_prototype_recipe(Prototype.IronPlate)
print(f"Iron Plate Recipe: {iron_plate_recipe}")

"""
Step 2: Gather raw resources
"""
resources_to_gather = [
    (Resource.Stone, 13),  # 5 for furnace, 8 extra for safety margin
    (Resource.IronOre, 30),  # 26 for iron plates, 4 extra for safety margin
    (Resource.Coal, 10)  # 10 for smelting fuel
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
print(f"Final inventory after gathering: {final_inventory}")

"""
Step 3: Craft and place stone furnace
"""
craft_item(Prototype.StoneFurnace, quantity=1)
furnace_position = Position(x=0, y=0)
move_to(furnace_position)
furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)
print("Placed stone furnace")

"""
Step 4: Smelt iron plates
"""
# Insert coal into the furnace as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=5)
print("Inserted coal into the furnace")

# Insert iron ore into the furnace
insert_item(Prototype.IronOre, updated_furnace, quantity=26)
print("Inserted iron ore into the furnace")

sleep(20)  # Wait for smelting to complete

# Extract iron plates
for _ in range(5):  # Try up to 5 times
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=26)
    current_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plates >= 26:
        break
    sleep(5)

print(f"Extracted iron plates. Current inventory: {inspect_inventory()}")

"""
Step 5: Craft iron gear wheels
"""
craft_item(Prototype.IronGearWheel, quantity=6)
print("Crafted 6 iron gear wheels")

"""
Step 6: Craft burner mining drill
"""
craft_item(Prototype.BurnerMiningDrill, quantity=1)
print("Crafted 1 burner mining drill")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")
assert final_inventory.get(Prototype.BurnerMiningDrill, 0) >= 1, "Failed to craft burner mining drill"

print("Successfully crafted burner mining drill!")

