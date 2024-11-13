

from factorio_instance import *


"""
Step 1: Craft intermediate products
- Craft two transport belts
- Craft two iron gear wheels
"""
"""
Step 3: Craft the underground belt
- Craft the underground belt using the two transport belts and two iron gear wheels
:param game:
:return:
"""
"""
Step 1: Craft intermediate products
- Craft two transport belts
- Craft two iron gear wheels
:param game:
:return:
"""
# Get the recipe for transport belts
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)

# Check if the recipe is available
if transport_belt_recipe:
    print("Transport belt recipe:")
    print(f"Ingredients: {transport_belt_recipe.ingredients}")

# Craft two transport belts
num_transport_belts_to_craft = 2
crafted_transport_belts = craft_item(Prototype.TransportBelt, num_transport_belts_to_craft)
print(f"Crafted {crafted_transport_belts} transport belts")

# Check if we crafted the correct number of transport belts
assert crafted_transport_belts == num_transport_belts_to_craft, f"Failed to craft required number of transport belts. Expected {num_transport_belts_to_craft}, but got {crafted_transport_belts}"

# Get the recipe for iron gear wheels
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)

# Check if the recipe is available
if iron_gear_wheel_recipe:
    print("Iron gear wheel recipe:")
    print(f"Ingredients: {iron_gear_wheel_recipe.ingredients}")

# Craft two iron gear wheels
num_iron_gear_wheels_to_craft = 2
crafted_iron_gear_wheels = craft_item(Prototype.IronGearWheel, num_iron_gear_wheels_to_craft)
print(f"Crafted {crafted_iron_gear_wheels} iron gear wheels")

# Check if we crafted the correct number of iron gear wheels
assert crafted_iron_gear_wheels == num_iron_gear_wheels_to_craft, f"Failed to craft required number of iron gear wheels. Expected {num_iron_gear_wheels_to_craft}, but got {crafted_iron_gear_wheels}"

# Inspect the inventory to verify that we have the required items
inventory = inspect_inventory()
num_transport_belts_in_inventory = inventory.get(Prototype.TransportBelt, 0)
num_iron_gear_wheels_in_inventory = inventory.get(Prototype.IronGearWheel, 0)
print(f"Inventory: {num_transport_belts_in_inventory} transport belts, {num_iron_gear_wheels_in_inventory} iron gear wheels")

# Check if we have the required number of transport belts and iron gear wheels in the inventory
assert num_transport_belts_in_inventory >= num_transport_belts_to_craft, f"Not enough transport belts in inventory. Expected at least {num_transport_belts_to_craft}, but got {num_transport_belts_in_inventory}"
assert num_iron_gear_wheels_in_inventory >= num_iron_gear_wheels_to_craft, f"Not enough iron gear wheels in inventory. Expected at least {num_iron_gear_wheels_to_craft}, but got {num_iron_gear_wheels_in_inventory}"

print("Successfully crafted intermediate products: transport belts and iron gear wheels")

"""
Step 3: Craft the underground belt
- Craft the underground belt using the two transport belts and two iron gear wheels
:param game:
:return:
"""

# Get the recipe for underground belts
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)

# Check if the recipe is available
if underground_belt_recipe:
    print("Underground belt recipe:")
    print(f"Ingredients: {underground_belt_recipe.ingredients}")

# Craft one underground belt
num_underground_belts_to_craft = 1
crafted_underground_belts = craft_item(Prototype.UndergroundBelt, num_underground_belts_to_craft)
print(f"Crafted {crafted_underground_belts} underground belts")

# Check if we crafted the correct number of underground belts
assert crafted_underground_belts == num_underground_belts_to_craft, f"Failed to craft required number of underground belts. Expected {num_underground_belts_to_craft}, but got {crafted_underground_belts}"

# Inspect the inventory to verify that we have the required items
inventory = inspect_inventory()
num_underground_belts_in_inventory = inventory.get(Prototype.UndergroundBelt, 0)
print(f"Inventory: {num_underground_belts_in_inventory} underground belts")

# Check if we have the required number of underground belts in the inventory
assert num_underground_belts_in_inventory >= num_underground_belts_to_craft, f"Not enough underground belts in inventory. Expected at least {num_underground_belts_to_craft}, but got {num_underground_belts_in_inventory}"

print("Successfully crafted the underground belt")

