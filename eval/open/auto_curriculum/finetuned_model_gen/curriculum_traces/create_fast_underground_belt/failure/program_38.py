
from instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- burner mining drill
- stone furnace
- iron gear wheels
- transport belt
- fast-underground-belt
"""

"""
Step 2: Gather raw resources. We need to gather the following resources:
- At least 98 iron ore
- At least 7 coal
- At least 6 stone
"""

"""
Step 3: Craft stone furnace. We need to craft 1 stone furnace using 5 stone.
"""

"""
Step 4: Place and fuel stone furnace. We need to:
- Place the stone furnace
- Add coal to the furnace as fuel
"""

"""
Step 5: Smelt iron plates. We need to:
- Smelt 98 iron ore into 98 iron plates
- Ensure there is enough coal to keep the furnace running
- Extract the iron plates from the furnace
"""

"""
Step 6: Craft intermediate items. We need to craft the following intermediate items:
- 20 iron gear wheels (requires 40 iron plates)
- 2 underground-belt (requires 4 iron gear wheels and 2 transport belts, which in turn requires 2 iron gear wheels and 4 iron plates)
"""

"""
Step 7: Craft fast-underground-belt. We need to craft 1 fast-underground-belt using 3 iron gear wheels and 1 underground-belt.
"""

"""
Step 8: Verify crafting. We need to check if the fast-underground-belt is in our inventory.
"""

# Step 1: Print recipes
def print_recipes():
    recipes_to_print = [
        Prototype.BurnerMiningDrill,
        Prototype.StoneFurnace,
        Prototype.IronGearWheel,
        Prototype.TransportBelt,
        Prototype.FastUndergroundBelt
    ]
    
    for recipe in recipes_to_print:
        print(f"Recipe for {recipe}: {get_prototype_recipe(recipe)}")

print_recipes()

# Step 2: Gather raw resources
resources_to_gather = [
    (Resource.IronOre, 98),
    (Resource.Coal, 7),
    (Resource.Stone, 6)
]

for resource, amount in resources_to_gather:
    resource_pos = nearest(resource)
    move_to(resource_pos)
    harvested = harvest_resource(resource_pos, amount)
    current_inventory = inspect_inventory()
    assert current_inventory.get(resource, 0) >= amount, f"Failed to gather enough {resource}. Required: {amount}, Actual: {current_inventory.get(resource, 0)}"

# Step 3: Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
stone_furnace_in_inventory = inspect_inventory()[Prototype.StoneFurnace]
assert stone_furnace_in_inventory >= 1, "Failed to craft stone furnace"

# Step 4: Place and fuel stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
insert_item(Prototype.Coal, furnace, quantity=5)

# Step 5: Smelt iron plates
insert_item(Prototype.IronOre, furnace, quantity=98)
sleep(50)
extract_item(Prototype.IronPlate, furnace.position, quantity=98)
iron_plates_in_inventory = inspect_inventory()[Prototype.IronPlate]
assert iron_plates_in_inventory >= 98, f"Failed to smelt enough iron plates. Expected: 98, Actual: {iron_plates_in_inventory}"

# Step 6: Craft intermediate items
craft_item(Prototype.IronGearWheel, quantity=40)
craft_item(Prototype.TransportBelt, quantity=2)
craft_item(Prototype.UndergroundBelt, quantity=2)

# Step 7: Craft fast-underground-belt
craft_item(Prototype.FastUndergroundBelt, quantity=1)

# Step 8: Verify crafting
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, "Failed to craft fast-underground-belt"
print("Successfully crafted fast-underground-belt!")

