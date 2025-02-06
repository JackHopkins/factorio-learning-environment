

from instance import *

"""
Objective: Craft an underground-belt from scratch

Planning:
We need to craft an underground-belt. There are no entities on the map or in our inventory, so we need to start from scratch.
We'll need to gather resources, craft intermediate products, and finally craft the underground-belt.
"""

"""
Step 1: Print recipes
We need to print the recipes for the items we need to craft.
"""

# Get the recipe for iron gear wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(f"Iron Gear Wheel Recipe: {iron_gear_wheel_recipe}")

# Get the recipe for transport belt
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
print(f"Transport Belt Recipe: {transport_belt_recipe}")

# Get the recipe for underground belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print(f"Underground Belt Recipe: {underground_belt_recipe}")


"""
Step 2: Gather resources
- Mine 12 stone for 2 stone furnaces
- Mine at least 21 iron ore (we need 26 iron plates)
- Mine at least 2 coal for fueling the furnaces
"""
resources_to_gather = [
    (Resource.Stone, 12),
    (Resource.IronOre, 21),
    (Resource.Coal, 2)
]

for resource_type, required_quantity in resources_to_gather:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")

assert final_inventory.get(Resource.Stone, 0) >= 12, "Not enough Stone"
assert final_inventory.get(Resource.IronOre, 0) >= 21, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Not enough Coal"

print("Successfully gathered all required resources")

"""
Step 3: Craft stone furnaces
- Craft 2 stone furnaces
"""
craft_item(Prototype.StoneFurnace, 2)
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.StoneFurnace, 0) >= 2, f"Failed to craft 2 Stone Furnaces. Current inventory: {current_inventory}"

"""
Step 4: Set up and fuel furnaces
- Place 2 stone furnaces
- Add coal to each furnace as fuel
"""
furnace1 = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
furnace2 = place_entity(Prototype.StoneFurnace, position=Position(x=2, y=0))

# Insert coal into each furnace
updated_furnace1 = insert_item(Prototype.Coal, furnace1, quantity=1)
updated_furnace2 = insert_item(Prototype.Coal, furnace2, quantity=1)

"""
Step 5: Smelt iron plates
- Smelt 21 iron ore into iron plates
"""
iron_ore_to_smelt = 21
iron_ore_per_furnace = iron_ore_to_smelt // 2

# Insert iron ore into each furnace
updated_furnace1 = insert_item(Prototype.IronOre, updated_furnace1, quantity=iron_ore_per_furnace)
updated_furnace2 = insert_item(Prototype.IronOre, updated_furnace2, quantity=iron_ore_per_furnace)

# Wait for smelting
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_to_smelt)
sleep(total_smelting_time)

# Extract iron plates
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace1.position, quantity=iron_ore_per_furnace)
    extract_item(Prototype.IronPlate, updated_furnace2.position, quantity=iron_ore_per_furnace)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= 21:
        break
    sleep(10)

assert inspect_inventory().get(Prototype.IronPlate, 0) >= 21, "Failed to obtain enough Iron Plates"

"""
Step 6: Craft intermediate products
- Craft 8 iron gear wheels
- Craft 6 transport-belts
"""
craft_item(Prototype.IronGearWheel, 8)
craft_item(Prototype.TransportBelt, 6)

"""
Step 7: Craft underground-belt
- Craft 1 underground-belt
"""
craft_item(Prototype.UndergroundBelt, 1)

"""
Step 8: Verify crafting
- Check that we have crafted 1 underground-belt
"""
final_inventory = inspect_inventory()
underground_belts_count = final_inventory.get(Prototype.UndergroundBelt, 0)
assert underground_belts_count >= 1, f"Failed to craft the required number of Underground Belts. Expected at least 1, but got {underground_belts_count}"

print(f"Successfully crafted {underground_belts_count} Underground Belt(s)")

