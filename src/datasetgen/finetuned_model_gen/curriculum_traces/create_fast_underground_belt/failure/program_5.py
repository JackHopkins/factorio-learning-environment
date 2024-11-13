

from factorio_instance import *


"""
Objective: Craft a fast-underground-belt from scratch

Planning:
We need to create a fast-underground-belt from scratch.
There are no entities on the map, and our inventory is empty.
We need to gather resources, craft intermediate products, and finally craft the fast-underground-belt.

Steps:
1. Print recipes for fast-underground-belt and intermediate products
2. Calculate total resources needed
3. Gather raw resources (iron ore and stone)
4. Craft stone furnaces
5. Set up iron smelting
6. Craft iron plates
7. Craft intermediate products (iron gear wheels and underground belt)
8. Craft fast-underground-belt
9. Verify success
"""

"""
Step 1: Print recipes
"""
print("Recipes:")
print("fast-underground-belt requires 2 iron gear wheels and 1 underground belt")
print("iron gear wheel requires 2 iron plates")
print("underground belt requires 1 iron plate and 1 iron gear wheel")

"""
Step 2: Calculate total resources needed
"""
# For 2 iron gear wheels: 2 * 2 = 4 iron plates
# For 1 underground belt: 1 iron plate + 2 iron plates (for 1 iron gear wheel) = 3 iron plates
# Total iron plates needed: 4 + 3 = 7
total_iron_plates_needed = 7

# Each iron plate requires 1 iron ore
iron_ore_needed = total_iron_plates_needed

# We need 12 stone to craft 2 stone furnaces (each requires 5 stone)
stone_needed = 12

print(f"Total iron ore needed: {iron_ore_needed}")
print(f"Total stone needed: {stone_needed}")

"""
Step 3: Gather raw resources
"""
resources_to_gather = [
    (Resource.IronOre, iron_ore_needed),
    (Resource.Stone, stone_needed)
]

for resource_type, required_quantity in resources_to_gather:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

print("Final inventory after gathering resources:")
print(inspect_inventory())

"""
Step 4: Craft stone furnaces
"""
craft_item(Prototype.StoneFurnace, quantity=2)
print("Crafted 2 stone furnaces")

"""
Step 5: Set up iron smelting
"""
furnace_position = Position(x=0, y=0)  # Choose an arbitrary position
move_to(furnace_position)
furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)

# Insert stone into the furnace
insert_item(Prototype.Stone, furnace, quantity=10)
print("Inserted 10 stone into the furnace")

# Insert coal for fuel
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
if coal_in_inventory > 0:
    insert_item(Prototype.Coal, furnace, quantity=5)
    print("Inserted 5 coal into the furnace for fuel")
else:
    print("No coal available in inventory for fuel")

"""
Step 6: Craft iron plates
"""
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
if iron_ore_in_inventory > 0:
    insert_item(Prototype.IronOre, furnace, quantity=iron_ore_in_inventory)
    sleep(5)  # Wait for smelting
    extracted_iron_plates = extract_item(Prototype.IronPlate, furnace.position, quantity=iron_ore_in_inventory)
    print(f"Extracted {extracted_iron_plates} iron plates")
else:
    print("No iron ore available in inventory to smelt")

"""
Step 7: Craft intermediate products
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=2)
print("Crafted 2 iron gear wheels")

# Craft underground belt
craft_item(Prototype.UndergroundBelt, quantity=1)
print("Crafted 1 underground belt")

"""
Step 8: Craft fast-underground-belt
"""
craft_item(Prototype.FastUndergroundBelt, quantity=1)
print("Crafted 1 fast-underground-belt")

"""
Step 9: Verify success
"""
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, "Failed to craft fast-underground-belt"
print("Successfully crafted fast-underground-belt")
print("Final inventory:")
print(final_inventory)

