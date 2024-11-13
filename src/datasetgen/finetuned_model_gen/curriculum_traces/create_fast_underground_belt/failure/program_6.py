
from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- stone-furnace
- iron-gear-wheel
- fast-underground-belt
- underground-belt

Step 2: Gather raw resources. We need to gather the following resources:
- 12 stone
- 80 iron ore
- 60 coal

Step 3: Craft and set up furnaces. We need to:
- Craft 2 stone furnaces
- Place the furnaces
- Fuel the furnaces with coal

Step 4: Smelt iron plates and stone bricks. We need to:
- Smelt 80 iron ore into 80 iron plates
- Smelt 12 stone into 6 stone bricks

Step 5: Craft iron gear wheels. We need to craft 40 iron gear wheels using 80 iron plates.

Step 6: Craft underground-belts. We need to craft 2 underground-belts using 20 iron gear wheels and 6 iron plates.

Step 7: Craft fast-underground-belt. We need to craft 1 fast-underground-belt using 20 iron gear wheels and 2 underground-belts.
"""

"""
Step 1: Print recipes
"""
# Print recipe for stone-furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print("Stone Furnace Recipe:")
print(stone_furnace_recipe)

# Print recipe for iron-gear-wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print("Iron Gear Wheel Recipe:")
print(iron_gear_wheel_recipe)

# Print recipe for fast-underground-belt
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
print("Fast Underground Belt Recipe:")
print(fast_underground_belt_recipe)

# Print recipe for underground-belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print("Underground Belt Recipe:")
print(underground_belt_recipe)

"""
Step 2: Gather raw resources
"""
resources_to_gather = [
    (Resource.Stone, 12),
    (Resource.IronOre, 80),
    (Resource.Coal, 60)
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
print("Final inventory after gathering resources:")
print(final_inventory)

"""
Step 3: Craft and set up furnaces
"""
craft_item(Prototype.StoneFurnace, quantity=2)
print("Crafted 2 stone furnaces")

origin = Position(x=0, y=0)

# Place and fuel first furnace
move_to(origin)
furnace1 = place_entity(Prototype.StoneFurnace, position=origin)
fueled_furnace1 = insert_item(Prototype.Coal, furnace1, quantity=30)
print("Placed and fueled first furnace")

# Place and fuel second furnace
second_furnace_position = Position(x=2, y=0)
move_to(second_furnace_position)
furnace2 = place_entity(Prototype.StoneFurnace, position=second_furnace_position)
fueled_furnace2 = insert_item(Prototype.Coal, furnace2, quantity=30)
print("Placed and fueled second furnace")

"""
Step 4: Smelt iron plates and stone bricks
"""
# Smelt iron ore into iron plates
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
if iron_ore_in_inventory > 0:
    updated_furnace1 = insert_item(Prototype.IronOre, fueled_furnace1, quantity=iron_ore_in_inventory)
    sleep(iron_ore_in_inventory * 0.7)
    extract_item(Prototype.IronPlate, updated_furnace1.position, quantity=iron_ore_in_inventory)
    print(f"Smelted {iron_ore_in_inventory} Iron Ore into Iron Plates")

# Smelt stone into stone bricks
stone_in_inventory = inspect_inventory().get(Prototype.Stone, 0)
if stone_in_inventory > 0:
    updated_furnace2 = insert_item(Prototype.Stone, fueled_furnace2, quantity=stone_in_inventory)
    sleep(stone_in_inventory * 0.7)
    extract_item(Prototype.StoneBrick, updated_furnace2.position, quantity=stone_in_inventory)
    print(f"Smelted {stone_in_inventory} Stone into Stone Bricks")

"""
Step 5: Craft iron gear wheels
"""
iron_plates_for_gears = inspect_inventory().get(Prototype.IronPlate, 0)
if iron_plates_for_gears >= 80:
    craft_item(Prototype.IronGearWheel, quantity=40)
    print("Crafted 40 Iron Gear Wheels")
else:
    print(f"Insufficient Iron Plates to craft Iron Gear Wheels. Available: {iron_plates_for_gears}")

"""
Step 6: Craft underground-belts
"""
iron_plates_for_underground_belts = inspect_inventory().get(Prototype.IronPlate, 0)
if iron_plates_for_underground_belts >= 6:
    craft_item(Prototype.UndergroundBelt, quantity=2)
    print("Crafted 2 Underground Belts")
else:
    print(f"Insufficient Iron Plates to craft Underground Belts. Available: {iron_plates_for_underground_belts}")

"""
Step 7: Craft fast-underground-belt
"""
iron_gear_wheels_for_fast_underground_belt = inspect_inventory().get(Prototype.IronGearWheel, 0)
underground_belts_in_inventory = inspect_inventory().get(Prototype.UndergroundBelt, 0)

if iron_gear_wheels_for_fast_underground_belt >= 20 and underground_belts_in_inventory >= 1:
    craft_item(Prototype.FastUndergroundBelt, quantity=1)
    print("Crafted 1 Fast Underground Belt")
else:
    print(f"Insufficient materials to craft Fast Underground Belt. Available Iron Gear Wheels: {iron_gear_wheels_for_fast_underground_belt}, Available Underground Belts: {underground_belts_in_inventory}")

"""
Final verification
"""
final_inventory = inspect_inventory()
fast_underground_belts = final_inventory.get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belts >= 1, f"Failed to craft Fast Underground Belt. Expected: 1, Actual: {fast_underground_belts}"
print("Successfully crafted Fast Underground Belt")

