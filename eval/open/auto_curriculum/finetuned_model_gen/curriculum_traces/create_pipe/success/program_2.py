

from instance import *

"""
Step 1: Print recipe for pipe
"""
# Get recipe for pipe
pipe_recipe = get_prototype_recipe(Prototype.Pipe)

# Print the recipe details
print("Pipe Recipe:")
print(f"Ingredients: {pipe_recipe.ingredients}")

"""
Step 2: Smelt iron plates
"""
# Move to the stone furnace
furnace = get_entities({Prototype.StoneFurnace})[0]
move_to(furnace.position)

# Check current inventory for iron plates
inventory = inspect_inventory()
iron_plates_needed = max(1 - inventory.get(Prototype.IronPlate, 0), 0)

if iron_plates_needed > 0:
    # Gather iron ore
    iron_ore_position = nearest(Resource.IronOre)
    move_to(iron_ore_position)
    harvest_resource(iron_ore_position, quantity=iron_plates_needed)

    # Move back to the furnace
    move_to(furnace.position)

    # Insert iron ore into the furnace
    insert_item(Prototype.IronOre, furnace, iron_plates_needed)
    insert_item(Prototype.Coal, furnace, 1)  # Use the coal from inventory for fuel

    # Wait for smelting
    sleep(5)

    # Extract iron plates
    extract_item(Prototype.IronPlate, furnace.position, iron_plates_needed)

    # Verify iron plates
    inventory = inspect_inventory()
    assert inventory.get(Prototype.IronPlate, 0) >= 1, "Failed to obtain enough iron plates"

"""
Step 3: Craft the pipe
"""
# Craft the pipe
craft_item(Prototype.Pipe, quantity=1)

# Verify pipe creation
inventory = inspect_inventory()
assert inventory.get(Prototype.Pipe, 0) >= 1, "Failed to craft pipe"

# Final inventory check
final_inventory = inspect_inventory()
print("Final Inventory:")
print(f"Iron Plates: {final_inventory.get(Prototype.IronPlate, 0)}")
print(f"Pipes: {final_inventory.get(Prototype.Pipe, 0)}")

