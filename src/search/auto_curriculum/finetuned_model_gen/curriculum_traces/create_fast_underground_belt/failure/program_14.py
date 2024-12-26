

from factorio_instance import *

"""
Objective: Craft 1 fast-underground-belt from scratch

Planning:
We need to craft 1 fast-underground-belt, which requires 2 underground belts and 40 iron gear wheels.
We need to smelt iron plates to make these components.
We don't have any entities or resources on the map or in our inventory, so we need to start from scratch.

Steps:
1. Print recipes for all items we need to craft
2. Gather raw resources (stone, iron ore, coal)
3. Craft and set up the smelting area
4. Smelt iron plates
5. Craft intermediate components (iron gear wheels, underground belts)
6. Craft the final product (fast-underground-belt)
"""

"""
Step 1: Print recipes
"""
# Get and print the recipe for fast-underground-belt
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
print("FastUndergroundBelt recipe:")
print(fast_underground_belt_recipe)

# Get and print the recipe for iron gear wheels
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print("IronGearWheel recipe:")
print(iron_gear_wheel_recipe)

# Get and print the recipe for underground belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print("UndergroundBelt recipe:")
print(underground_belt_recipe)

# Get and print the recipe for stone furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print("StoneFurnace recipe:")
print(stone_furnace_recipe)

"""
Step 2: Gather raw resources
"""
resources_to_gather = [
    (Resource.Stone, 5),
    (Resource.IronOre, 40),
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

"""
Step 3: Craft and set up the smelting area
"""
# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 Stone Furnace")

# Place stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed Stone Furnace at {furnace.position}")

# Add coal to furnace
coal_in_inventory = inspect_inventory()[Prototype.Coal]
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=coal_in_inventory)
print(f"Inserted {coal_in_inventory} coal into the furnace")

"""
Step 4: Smelt iron plates
"""
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} Iron Ore into the furnace")

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

"""
Step 5: Craft intermediate components
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=40)
print("Crafted 40 Iron Gear Wheels")

# Craft underground belts
craft_item(Prototype.UndergroundBelt, quantity=2)
print("Crafted 2 Underground Belts")

"""
Step 6: Craft the final product
"""
# Craft fast-underground-belt
craft_item(Prototype.FastUndergroundBelt, quantity=1)
print("Crafted 1 FastUndergroundBelt")

# Verify the crafting process
final_inventory = inspect_inventory()
fast_underground_belt_count = final_inventory.get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belt_count >= 1, f"Failed to craft FastUndergroundBelt. Required: 1, Actual: {fast_underground_belt_count}"
print(f"Successfully crafted {fast_underground_belt_count} FastUndergroundBelt")

