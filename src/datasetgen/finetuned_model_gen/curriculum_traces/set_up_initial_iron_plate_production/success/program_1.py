
from factorio_instance import *

"""
Step 1: Print recipe for Stone Furnace
"""
# Get the recipe for Stone Furnace
recipe = get_prototype_recipe(Prototype.StoneFurnace)

# Print the recipe details
print("Recipe for Stone Furnace:")
print(f"Ingredients:")
for ingredient in recipe.ingredients:
    print(f"- {ingredient.count} {ingredient.name}")


"""
Step 1: Craft and place a stone furnace
"""
# Get stone for furnace
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=5)

# Craft stone furnace
craft_item(Prototype.StoneFurnace, 1)

# Place stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed stone furnace at {furnace.position}")

"""
Step 2: Mine iron ore and fuel
"""
# Get iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=10)
print("Mined iron ore")

# Get coal for fuel
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=5)
print("Mined coal")

"""
Step 3: Smelt iron plates
"""
# Insert fuel
updated_furnace = insert_item(Prototype.Coal, furnace, 5)
print("Inserted coal into furnace")

# Insert iron ore
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, 10)
print("Inserted iron ore into furnace")

# Wait for smelting
sleep(5)

# Extract iron plates
extract_item(Prototype.IronPlate, updated_furnace.position, 10)

# Verify production
iron_plates = inspect_inventory()[Prototype.IronPlate]
assert iron_plates >= 10, f"Failed to produce enough iron plates. Only have {iron_plates}"
print(f"Successfully produced {iron_plates} iron plates")

