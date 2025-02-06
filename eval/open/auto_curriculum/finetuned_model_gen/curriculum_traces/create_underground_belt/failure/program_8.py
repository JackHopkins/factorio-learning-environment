

from instance import *

"""
Objective: Craft an underground belt from scratch

Planning:
We need to craft 1 underground belt, which requires:
- 4 transport-belts
- 1 fast-transport-belt
- 7 iron plates
- 4 iron-gear-wheels

There are no entities on the map and our inventory is empty, so we need to gather all resources from scratch.
We'll need to mine iron ore, stone, and coal, then craft stone furnaces for smelting.
"""

"""
Step 1: Print recipes
"""
print("Recipes:")
print("Stone Furnace: 5 stone")
print("Transport Belt: 1 iron gear wheel, 1 iron plate")
print("Fast Transport Belt: 1 iron gear wheel, 3 iron plates")
print("Iron Gear Wheel: 2 iron plates")
print("Underground Belt: 7 iron plates, 4 iron gear wheels")

"""
Step 2: Gather raw resources
- Mine 12 stone (5 for furnace, 7 extra for safety)
- Mine 21 iron ore (14 for plates, 7 extra for safety)
- Mine 2 coal (for fuel)
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
    print(f"Harvested {harvested} {resource_type}")
    print(f"Current inventory: {current_inventory}")
    assert current_inventory[resource_type] >= required_quantity, f"Failed to gather enough {resource_type}"

"""
Step 3: Craft and set up stone furnaces
- Craft 2 stone furnaces
- Place and fuel them
"""
craft_item(Prototype.StoneFurnace, quantity=2)
print("Crafted 2 stone furnaces")

origin = Position(x=0, y=0)
move_to(origin)
furnace1 = place_entity(Prototype.StoneFurnace, position=origin)
furnace2 = place_entity(Prototype.StoneFurnace, position=Position(x=1, y=0))
print("Placed 2 stone furnaces")

for furnace in [furnace1, furnace2]:
    insert_item(Prototype.Coal, furnace, 1)
    print(f"Inserted 1 coal into furnace at {furnace.position}")

"""
Step 4: Smelt iron plates
- Smelt 21 iron ore into iron plates
"""
move_to(furnace1.position)
insert_item(Prototype.IronOre, furnace1, 11)
insert_item(Prototype.IronOre, furnace2, 10)
print("Inserted iron ore into furnaces")

sleep(11)

for furnace in [furnace1, furnace2]:
    extracted = extract_item(Prototype.IronPlate, furnace.position, 11)
    print(f"Extracted {extracted} iron plates from furnace at {furnace.position}")

current_inventory = inspect_inventory()
print(f"Current inventory after smelting: {current_inventory}")
assert current_inventory[Prototype.IronPlate] >= 21, "Failed to smelt enough iron plates"

"""
Step 5: Craft iron-gear-wheels
- Craft 8 iron-gear-wheels
"""
craft_item(Prototype.IronGearWheel, quantity=8)
print("Crafted 8 iron-gear-wheels")

"""
Step 6: Craft transport-belts
- Craft 4 transport-belts
"""
craft_item(Prototype.TransportBelt, quantity=4)
print("Crafted 4 transport-belts")

"""
Step 7: Craft fast-transport-belt
- Craft 1 fast-transport-belt
"""
craft_item(Prototype.FastTransportBelt, quantity=1)
print("Crafted 1 fast-transport-belt")

"""
Step 8: Craft underground-belt
- Craft 1 underground-belt
"""
craft_item(Prototype.UndergroundBelt, quantity=1)
print("Crafted 1 underground-belt")

"""
Step 9: Verify crafting
"""
final_inventory = inspect_inventory()
assert final_inventory[Prototype.UndergroundBelt] >= 1, "Failed to craft underground-belt"
print("Successfully crafted underground-belt")

