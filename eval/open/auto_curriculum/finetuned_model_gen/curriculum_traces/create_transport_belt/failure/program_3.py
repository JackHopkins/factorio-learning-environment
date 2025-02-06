
from instance import *

"""
Crafting plan to create a transport-belt from an empty inventory:

We need to craft one transport-belt. To do this, we need to:
1. Print recipes for stone furnace and transport belt
2. Mine stone and craft a stone furnace
3. Place the stone furnace
4. Mine iron ore
5. Smelt iron ore into iron plates
6. Craft iron gear wheel
7. Craft transport belt

The policy will follow these steps to craft the required item from scratch.
"""

"""
Step 1: Print recipes
"""
# Print recipe for stone furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print("Stone Furnace Recipe:")
print(f"Ingredients: {stone_furnace_recipe.ingredients}")

# Print recipe for transport belt
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
print("Transport Belt Recipe:")
print(f"Ingredients: {transport_belt_recipe.ingredients}")

"""
Step 2: Craft stone furnace
"""
# Mine stone for the furnace
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=5)

# Craft the stone furnace
craft_item(Prototype.StoneFurnace, 1)
print("Crafted 1 Stone Furnace")

"""
Step 3: Place the stone furnace
"""
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed Stone Furnace at {furnace.position}")

"""
Step 4: Mine iron ore
"""
iron_position = nearest(Resource.IronOre)
move_to(iron_position)
harvest_resource(iron_position, quantity=10)
print("Mined 10 Iron Ore")

"""
Step 5: Smelt iron ore into iron plates
"""
move_to(furnace.position)
insert_item(Prototype.IronOre, furnace, 10)
insert_item(Prototype.Coal, furnace, 5)  # Assuming we mined some coal
sleep(5)
extract_item(Prototype.IronPlate, furnace.position, 10)
print("Extracted Iron Plates")

"""
Step 6: Craft iron gear wheel
"""
craft_item(Prototype.IronGearWheel, 1)
print("Crafted 1 Iron Gear Wheel")

"""
Step 7: Craft transport belt
"""
craft_item(Prototype.TransportBelt, 1)
print("Crafted 1 Transport Belt")

# Verify final inventory
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.TransportBelt, 0) >= 1, "Failed to craft transport belt"
print("Successfully crafted transport belt")
