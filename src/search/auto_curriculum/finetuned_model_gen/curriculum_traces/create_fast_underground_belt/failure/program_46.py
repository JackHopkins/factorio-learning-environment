

from factorio_instance import *

"""
Objective: Create a fast-underground-belt from scratch

Planning:
We need to create a fast-underground-belt. This requires:
- 2 underground-belts
- 40 iron gear wheels
- 20 iron plates

To create these, we need:
- 98 iron plates (for iron gear wheels and the belts)
- A stone furnace to smelt the iron ore into plates

Steps:
1. Print recipes for required items
2. Gather resources: stone, iron ore, coal
3. Craft a stone furnace
4. Place and fuel the furnace
5. Smelt iron ore into iron plates
6. Craft iron gear wheels
7. Craft underground-belts
8. Craft fast-underground-belt
9. Verify the crafted item
"""

"""
Step 1: Print recipes for required items
"""
# Fetch and print recipe for fast-underground-belt
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
print("FastUndergroundBelt Recipe:")
print(fast_underground_belt_recipe)

# Fetch and print recipe for underground-belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print("UndergroundBelt Recipe:")
print(underground_belt_recipe)

# Fetch and print recipe for iron gear wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print("IronGearWheel Recipe:")
print(iron_gear_wheel_recipe)

# Fetch and print recipe for stone furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print("StoneFurnace Recipe:")
print(stone_furnace_recipe)

"""
Step 2: Gather resources
"""
# Define required resources
resources_needed = [
    (Resource.Stone, 6),
    (Resource.IronOre, 98),
    (Resource.Coal, 7)
]

# Gather resources
for resource_type, quantity in resources_needed:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, quantity=quantity)
    current_inventory = inspect_inventory()
    assert current_inventory.get(resource_type, 0) >= quantity, f"Failed to gather enough {resource_type}. Required: {quantity}, Actual: {current_inventory.get(resource_type, 0)}"
    print(f"Successfully gathered {harvested} {resource_type}")

final_inventory = inspect_inventory()
print("Final inventory after gathering resources:", final_inventory)

"""
Step 3: Craft a stone furnace
"""
craft_item(Prototype.StoneFurnace, quantity=1)
assert inspect_inventory().get(Prototype.StoneFurnace, 0) >= 1, "Failed to craft Stone Furnace"
print("Successfully crafted 1 Stone Furnace")

"""
Step 4: Place and fuel the furnace
"""
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
insert_item(Prototype.Coal, furnace, quantity=5)
print("Placed and fueled Stone Furnace")

"""
Step 5: Smelt iron ore into iron plates
"""
# Insert iron ore into the furnace
insert_item(Prototype.IronOre, furnace, quantity=98)

# Wait for smelting and extract iron plates
smelting_time_per_ore = 0.7  # Slightly more than 0.5 to account for delays
total_smelting_time = int(smelting_time_per_ore * 98)
sleep(total_smelting_time)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=98)
iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
assert iron_plates_in_inventory >= 98, f"Failed to smelt enough Iron Plates. Expected: 98, Actual: {iron_plates_in_inventory}"
print(f"Successfully smelted {iron_plates_in_inventory} Iron Plates")

"""
Step 6: Craft iron gear wheels
"""
craft_item(Prototype.IronGearWheel, quantity=40)
assert inspect_inventory().get(Prototype.IronGearWheel, 0) >= 40, "Failed to craft 40 Iron Gear Wheels"
print("Successfully crafted 40 Iron Gear Wheels")

"""
Step 7: Craft underground-belts
"""
craft_item(Prototype.UndergroundBelt, quantity=2)
assert inspect_inventory().get(Prototype.UndergroundBelt, 0) >= 2, "Failed to craft 2 Underground Belts"
print("Successfully crafted 2 Underground Belts")

"""
Step 8: Craft fast-underground-belt
"""
craft_item(Prototype.FastUndergroundBelt, quantity=1)
print("Crafting FastUndergroundBelt...")

"""
Step 9: Verify the crafted item
"""
final_inventory = inspect_inventory()
fast_underground_belt_count = final_inventory.get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belt_count >= 1, f"Failed to craft FastUndergroundBelt. Count: {fast_underground_belt_count}"
print(f"Successfully crafted {fast_underground_belt_count} FastUndergroundBelt(s)")

print("Objective completed successfully!")

