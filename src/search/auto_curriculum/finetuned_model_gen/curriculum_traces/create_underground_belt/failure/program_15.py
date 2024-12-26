

from factorio_instance import *

"""
Objective: Craft an underground-belt from raw materials

Planning:
We need to craft an underground-belt, which requires 5 iron plates and 5 transport-belts.
To craft the transport-belts, we need 1 iron gear wheel and 1 iron plate per belt, totaling 10 iron plates.
We'll need a stone furnace to smelt iron ore into iron plates.
We'll also need coal to fuel the furnace.

Steps:
1. Print recipes
2. Gather resources (iron ore, stone, coal)
3. Craft and set up the stone furnace
4. Smelt iron plates
5. Craft transport-belts
6. Craft the underground-belt
7. Verify the result
"""

"""
Step 1: Print recipes
"""
print("Recipes:")
print("Stone Furnace: 5 stone")
print("Iron Plate: 1 iron ore smelted")
print("Transport Belt: 1 iron gear wheel, 1 iron plate")
print("Iron Gear Wheel: 2 iron plates")
print("Underground Belt: 5 iron plates, 5 transport belts")

"""
Step 2: Gather resources
"""
resources_to_gather = [
    (Resource.IronOre, 10),
    (Resource.Stone, 5),
    (Resource.Coal, 5)
]

for resource_type, required_amount in resources_to_gather:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_amount)
    current_inventory = inspect_inventory()
    actual_amount = current_inventory.get(resource_type, 0)
    assert actual_amount >= required_amount, f"Failed to gather enough {resource_type}. Required: {required_amount}, Actual: {actual_amount}"
    print(f"Successfully gathered {actual_amount} {resource_type}")

"""
Step 3: Craft and set up the stone furnace
"""
craft_item(Prototype.StoneFurnace, 1)
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
move_to(furnace.position)

# Insert coal into the furnace as fuel
furnace = insert_item(Prototype.Coal, furnace, quantity=5)

# Insert iron ore into the furnace
furnace = insert_item(Prototype.IronOre, furnace, quantity=10)

"""
Step 4: Smelt iron plates
"""
sleep(7)  # Wait for smelting to complete
extract_item(Prototype.IronPlate, furnace.position, quantity=10)

current_inventory = inspect_inventory()
iron_plates = current_inventory.get(Prototype.IronPlate, 0)
assert iron_plates >= 10, f"Failed to smelt enough iron plates. Required: 10, Actual: {iron_plates}"
print(f"Successfully smelted {iron_plates} iron plates")

"""
Step 5: Craft transport-belts
"""
craft_item(Prototype.TransportBelt, 5)

"""
Step 6: Craft the underground-belt
"""
craft_item(Prototype.UndergroundBelt, 1)

"""
Step 7: Verify the result
"""
final_inventory = inspect_inventory()
underground_belts = final_inventory.get(Prototype.UndergroundBelt, 0)
assert underground_belts >= 1, f"Failed to craft underground-belt. Required: 1, Actual: {underground_belts}"
print(f"Successfully crafted {underground_belts} underground-belt(s)")

print("Crafting process completed successfully!")

