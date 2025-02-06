

from instance import *

"""
Step 1: Print recipes
- Stone Furnace: 5 stone
- Firearm Magazine: 4 iron plates
"""
print("Recipes:")
print("Stone Furnace: 5 stone")
print("Firearm Magazine: 4 iron plates")

"""
Step 2: Gather raw resources
- Mine stone for the furnace
- Mine iron ore for the iron plates
- Mine coal for fuel
"""
resources_to_gather = [
    (Resource.Stone, 10),
    (Resource.IronOre, 24),
    (Resource.Coal, 12)
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
Step 3: Craft and place stone furnace
"""
craft_item(Prototype.StoneFurnace, 1)
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
print("Stone furnace crafted and placed")

"""
Step 4: Smelt iron ore into iron plates
"""
iron_plates_needed = 12
move_to(furnace.position)
insert_item(Prototype.Coal, furnace, 6)
insert_item(Prototype.IronOre, furnace, iron_plates_needed)
sleep(10)
extract_item(Prototype.IronPlate, furnace.position, iron_plates_needed)
print(f"Extracted {iron_plates_needed} Iron Plates")

"""
Step 5: Craft firearm magazine
"""
craft_item(Prototype.FirearmMagazine, 1)
print("Crafted 1 Firearm Magazine")

"""
Step 6: Verify crafted items
"""
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.FirearmMagazine, 0) >= 1, "Failed to craft Firearm Magazine"
print("Successfully crafted the required items!")

