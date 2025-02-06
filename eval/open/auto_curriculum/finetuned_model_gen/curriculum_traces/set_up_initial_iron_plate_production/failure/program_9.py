

from instance import *

"""
Step 1: Craft and place a stone furnace
"""
# Check if stone furnace is needed
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
stone_furnace_ingredients = stone_furnace_recipe.ingredients

# We need 5 stone for a stone furnace
stone_needed = stone_furnace_ingredients[0].count

# Get stone for stone furnace
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvested_stone = harvest_resource(stone_position, quantity=stone_needed)
assert harvested_stone >= stone_needed, f"Failed to get enough stone, got {harvested_stone}, needed {stone_needed}"

# Craft stone furnace
craft_item(Prototype.StoneFurnace, 1)
assert inspect_inventory()[Prototype.StoneFurnace] >= 1, "Failed to craft stone furnace"

# Place stone furnace
furnace_position = Position(x=0, y=0)  # Assuming origin is suitable, adjust if needed
move_to(furnace_position)
furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)
assert furnace is not None, "Failed to place stone furnace"

"""
Step 2: Mine resources
"""
# Get coal for fuel
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvested_coal = harvest_resource(coal_position, quantity=5)
assert harvested_coal >= 5, f"Failed to get enough coal, got {harvested_coal}, needed 5"

# Get iron ore
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
harvested_iron_ore = harvest_resource(iron_ore_position, quantity=10)
assert harvested_iron_ore >= 10, f"Failed to get enough iron ore, got {harvested_iron_ore}, needed 10"

"""
Step 3: Smelt iron plates
"""
# Insert coal into furnace
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=5)
assert updated_furnace.fuel.get(Prototype.Coal, 0) >= 1, "Failed to insert coal into furnace"

# Insert iron ore into furnace
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=10)
assert updated_furnace.furnace_source.get(Prototype.IronOre, 0) >= 1, "Failed to insert iron ore into furnace"

# Wait for smelting
sleep(30)

# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=10)
    if inspect_inventory().get(Prototype.IronPlate, 0) >= 10:
        break
    sleep(10)

assert inspect_inventory().get(Prototype.IronPlate, 0) >= 10, "Failed to produce enough iron plates"

