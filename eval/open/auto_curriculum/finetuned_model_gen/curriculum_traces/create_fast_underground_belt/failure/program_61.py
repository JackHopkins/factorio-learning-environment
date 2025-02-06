

from instance import *

"""
Objective: Craft a fast-underground-belt from scratch

Planning:
We need to craft a fast-underground-belt. 
There are no entities on the map or in the inventory, so we need to start from scratch.
"""

"""
Step 1: Print recipes
We need to print the recipes for the items we need to craft:
- stone furnace
- assembling machine 1
- inserter
- iron gear wheel
- underground belt
- fast underground belt
"""
# function to print recipes
def print_recipes():
    recipes_to_print = [
        Prototype.StoneFurnace,
        Prototype.AssemblingMachine1,
        Prototype.Inserter,
        Prototype.IronGearWheel,
        Prototype.UndergroundBelt,
        Prototype.FastUndergroundBelt
    ]
    
    for recipe in recipes_to_print:
        print(f"Recipe for {recipe}:")
        print(get_prototype_recipe(recipe))
        print("\n")

print_recipes()

"""
Step 1: Craft stone furnace
- Mine 5 stone
- Craft 1 stone furnace
"""
# Mine stone
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=5)

# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 stone furnace")

"""
Step 2: Set up smelting area
- Place stone furnace
- Mine iron ore and coal
- Smelt iron plates
"""
# Place stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)

# Mine iron ore and coal
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
harvest_resource(iron_ore_position, quantity=100)

coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, quantity=50)

# Smelt iron plates
move_to(furnace.position)
insert_item(Prototype.Coal, furnace, quantity=25)
insert_item(Prototype.IronOre, furnace, quantity=100)

# Wait for smelting
sleep(15)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=100)
print("Extracted iron plates")

"""
Step 3: Craft assembling machine 1
- Craft 3 iron gear wheels (requires 6 iron plates)
- Craft 1 inserter (requires 1 iron gear wheel, 1 electronic circuit, 1 iron plate)
- Craft 1 assembling machine 1 (requires 3 iron gear wheels, 3 electronic circuits, 9 iron plates)
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=3)
print("Crafted 3 iron gear wheels")

# Craft inserter
craft_item(Prototype.Inserter, quantity=1)
print("Crafted 1 inserter")

# Craft assembling machine 1
craft_item(Prototype.AssemblingMachine1, quantity=1)
print("Crafted 1 assembling machine 1")

"""
Step 4: Craft intermediate products
- Craft 40 iron gear wheels (requires 80 iron plates)
- Craft 2 underground belts (requires 2 iron gear wheels and 1 transport belt each)
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=40)
print("Crafted 40 iron gear wheels")

# Craft underground belts
craft_item(Prototype.UndergroundBelt, quantity=2)
print("Crafted 2 underground belts")

"""
Step 5: Craft fast underground belt
- Craft 1 fast underground belt (requires 2 underground belts, 40 iron gear wheels)
"""
craft_item(Prototype.FastUndergroundBelt, quantity=1)
print("Crafted 1 fast underground belt")

# Verify the crafted item
inventory = inspect_inventory()
assert inventory.get(Prototype.FastUndergroundBelt) >= 1, "Failed to craft fast underground belt"
print("Successfully crafted fast underground belt")

