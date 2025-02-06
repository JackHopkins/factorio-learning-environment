

from instance import *

"""
Objective: Set up initial iron plate production

Planning:
We need to set up a basic iron smelting operation. This requires a stone furnace and coal for fuel.
There are no entities on the map or in our inventory, so we need to start from scratch.
We'll need to gather stone for the furnace, coal for fuel, and iron ore to smelt.
"""

"""
Step 1: Print recipes
"""
# Get recipes for stone furnace and iron plate
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
iron_plate_recipe = get_prototype_recipe(Prototype.IronPlate)

# Print the recipes
print("Stone Furnace Recipe:")
print(f"Ingredients: {stone_furnace_recipe.ingredients}")

print("\nIron Plate Recipe:")
print(f"Ingredients: {iron_plate_recipe.ingredients}")
print("Note: Iron Plate requires smelting 1 iron ore for 3.2 seconds")

"""
Step 2: Craft Stone Furnace
- We need to mine 5 stone
- Craft 1 stone furnace
"""
# Mine 5 stone
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=5)

# Verify we have enough stone
inventory = inspect_inventory()
assert inventory.get(Prototype.Stone) >= 5, "Failed to gather enough stone"

# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)

# Verify we have the stone furnace
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace) >= 1, "Failed to craft stone furnace"

"""
Step 3: Place Furnace and Gather Resources
- Place the stone furnace
- Mine 5 coal for fuel
- Mine 10 iron ore
"""
# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)

# Mine coal
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, quantity=5)

# Verify coal
inventory = inspect_inventory()
assert inventory.get(Prototype.Coal) >= 5, "Failed to gather enough coal"

# Mine iron ore
iron_position = nearest(Resource.IronOre)
move_to(iron_position)
harvest_resource(iron_position, quantity=10)

# Verify iron ore
inventory = inspect_inventory()
assert inventory.get(Prototype.IronOre) >= 10, "Failed to gather enough iron ore"

"""
Step 4: Start Smelting
- Insert coal into the furnace
- Insert iron ore into the furnace
- Wait for smelting to complete
"""
# Move back to furnace
move_to(furnace.position)

# Insert coal into the furnace
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=5)
assert updated_furnace.fuel.get(Prototype.Coal) > 0, "Failed to fuel furnace"

# Insert iron ore into the furnace
insert_item(Prototype.IronOre, updated_furnace, quantity=10)

# Wait for smelting to complete (3.2 seconds per iron ore)
smelting_time = 3.2 * 10
sleep(smelting_time)

"""
Step 5: Verify Production
- Check the inventory for iron plates
"""
# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=10)
    inventory = inspect_inventory()
    if inventory.get(Prototype.IronPlate) >= 10:
        break
    sleep(5)  # Wait for more smelting if needed

# Final verification
inventory = inspect_inventory()
iron_plates = inventory.get(Prototype.IronPlate, 0)
assert iron_plates >= 10, f"Failed to produce enough iron plates. Expected 10, got {iron_plates}"
print(f"Successfully produced {iron_plates} iron plates")

