

from factorio_instance import *

"""
Objective: Craft a fast-underground-belt from scratch

Planning:
We need to create a fast-underground-belt. To make a fast-underground-belt, we need to craft:
- 2 iron gear wheels
- 1 underground belt

We need to craft two iron gear wheels and one underground belt. 
To craft these, we need iron plates and steel plates. 
We'll need to mine iron ore and coal, smelt the iron ore into plates, and then craft the gear wheels and belts.

We have nothing in our inventory and no entities on the map, so we need to gather all raw resources and craft the necessary items from scratch.

For the execution, we need to:
1) Print recipes for items we need to craft
2) Gather raw resources
3) Set up a smelting operation
4) Craft intermediate products
5) Craft the fast-underground-belt

Let's start with the policy implementation:
"""

"""
Step 1: Print recipes for items we need to craft
"""
# Get and print recipe for iron gear wheel
print("Iron Gear Wheel Recipe:")
iron_gear_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(iron_gear_recipe)

# Get and print recipe for underground belt
print("Underground Belt Recipe:")
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print(underground_belt_recipe)

# Get and print recipe for fast-underground-belt
print("Fast Underground Belt Recipe:")
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
print(fast_underground_belt_recipe)

"""
Step 2: Gather raw resources
"""
resources_to_gather = [
    (Resource.IronOre, 15),  # Need extra for steel plates
    (Resource.Coal, 5),
    (Resource.Stone, 5)
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
Step 3: Set up smelting operation
"""
# Craft and place stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
print("Placed stone furnace")

# Add coal to the furnace as fuel
insert_item(Prototype.Coal, furnace, quantity=5)
print("Inserted coal into the furnace")

"""
Step 4: Smelt iron plates
"""
# Smelt iron ore into iron plates
insert_item(Prototype.IronOre, furnace, quantity=10)
print("Inserted iron ore into the furnace")

# Wait for smelting to complete
sleep(10)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=10)
print("Extracted iron plates")

# Verify we have enough iron plates
iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
assert iron_plates >= 10, f"Failed to obtain enough iron plates. Have: {iron_plates}, Need: 10"

"""
Step 5: Smelt steel plates
"""
# Insert iron plates into the furnace (5 iron plates for 1 steel plate)
insert_item(Prototype.IronPlate, furnace, quantity=10)
print("Inserted iron plates into the furnace for steel production")

# Wait for smelting to complete
sleep(20)

# Extract steel plates
extract_item(Prototype.SteelPlate, furnace.position, quantity=5)
print("Extracted steel plates")

# Verify we have enough steel plates
steel_plates = inspect_inventory().get(Prototype.SteelPlate, 0)
assert steel_plates >= 5, f"Failed to obtain enough steel plates. Have: {steel_plates}, Need: 5"

"""
Step 6: Craft intermediate products
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=2)
print("Crafted iron gear wheels")

# Craft underground belt
craft_item(Prototype.UndergroundBelt, quantity=1)
print("Crafted underground belt")

"""
Step 7: Craft fast-underground-belt
"""
craft_item(Prototype.FastUndergroundBelt, quantity=1)
print("Crafted fast-underground-belt")

"""
Step 8: Verify the crafting
"""
final_inventory = inspect_inventory()
fast_underground_belts = final_inventory.get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belts >= 1, f"Failed to craft fast-underground-belt. Have: {fast_underground_belts}, Need: 1"

print(f"Successfully crafted {fast_underground_belts} fast-underground-belt(s)")

