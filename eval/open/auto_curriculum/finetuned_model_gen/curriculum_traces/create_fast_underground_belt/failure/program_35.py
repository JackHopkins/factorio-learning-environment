

from instance import *

"""
Objective: Create a fast-underground-belt from scratch

Planning:
We need to create a fast-underground-belt from scratch. There are no entities on the map, so we need to gather all the resources and craft the necessary components.
We need to print out the recipes for the items we need to craft.
We need to gather coal, stone, and iron ore. We need to craft stone furnaces for smelting. 
We need to smelt iron plates, craft iron gear wheels, underground belts, and finally the fast-underground-belt.
"""

"""
Step 1: Print out recipes
"""
print("Recipes:")
print("Fast Underground Belt:")
print("1 Fast Underground Belt requires 2 Underground Belts and 40 Iron Gear Wheels")
print("1 Underground Belt requires 10 Iron Gear Wheels and 10 Iron Plates")
print("1 Iron Gear Wheel requires 2 Iron Plates")
print("1 Stone Furnace requires 5 Stone")
print("1 Iron Plate requires smelting 1 Iron Ore")
print("Smelting requires coal as fuel")

"""
Step 2: Gather raw resources
We need to gather the following resources:
- Coal (at least 7 for fuel)
- Stone (at least 10 for 2 stone furnaces)
- Iron Ore (at least 98 for 98 iron plates)
"""
resources_to_gather = [
    (Resource.Coal, 7),
    (Resource.Stone, 10),
    (Resource.IronOre, 98)
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
print(f"Final inventory after gathering resources: {final_inventory}")

"""
Step 3: Craft and set up stone furnaces
- Craft 2 stone furnaces
- Place one furnace at a suitable location
- Fuel the furnace with coal
"""
craft_item(Prototype.StoneFurnace, 2)
print("Crafted 2 Stone Furnaces")

furnace_position = Position(x=0, y=0)
move_to(furnace_position)
furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)
print("Placed Stone Furnace")

coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
assert coal_in_inventory >= 1, f"Not enough coal in inventory to fuel the furnace. Coal available: {coal_in_inventory}"
fueled_furnace = insert_item(Prototype.Coal, furnace, quantity=coal_in_inventory)
print("Inserted coal into the Stone Furnace")

"""
Step 4: Smelt iron plates
- Insert iron ore into the furnace
- Wait for the smelting process to complete
- Extract iron plates (at least 98)
"""
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
assert iron_ore_in_inventory >= 98, f"Not enough Iron Ore in inventory. Required: 98, Available: {iron_ore_in_inventory}"
iron_inserted_furnace = insert_item(Prototype.IronOre, fueled_furnace, quantity=iron_ore_in_inventory)
print("Inserted Iron Ore into the Stone Furnace")

smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_in_inventory)
sleep(total_smelting_time)

max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, furnace_position, quantity=iron_ore_in_inventory)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= 98:
        break
    sleep(10)

print(f"Extracted Iron Plates; Current Inventory Count: {current_iron_plate_count}")

"""
Step 5: Craft iron gear wheels
- Use iron plates to craft 40 iron gear wheels
"""
craft_item(Prototype.IronGearWheel, 40)
print("Crafted 40 Iron Gear Wheels")

"""
Step 6: Craft underground belts
- Use iron gear wheels and iron plates to craft 2 underground belts
"""
craft_item(Prototype.UndergroundBelt, 2)
print("Crafted 2 Underground Belts")

"""
Step 7: Craft fast-underground-belt
- Use the 2 underground belts and 40 iron gear wheels to craft 1 fast-underground-belt
"""
craft_item(Prototype.FastUndergroundBelt, 1)
print("Crafted 1 Fast Underground Belt")

"""
Step 8: Verify the final inventory
- Check that we have at least 1 fast-underground-belt in our inventory
"""
final_inventory = inspect_inventory()
fast_underground_belt_count = final_inventory.get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belt_count >= 1, f"Failed to craft Fast Underground Belt. Expected at least 1, but found {fast_underground_belt_count}"
print(f"Successfully crafted Fast Underground Belt; Current Inventory Count: {fast_underground_belt_count}")

print("Objective completed successfully!")

