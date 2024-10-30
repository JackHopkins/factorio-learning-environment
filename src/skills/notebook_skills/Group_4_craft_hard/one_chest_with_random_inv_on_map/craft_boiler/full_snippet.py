from factorio_instance import *

"""
Main Objective: We require one Boiler. The final success should be checked by looking if a Boiler is in inventory
"""



"""
Step 1: Print recipes. We need to craft a Boiler. We must print the recipes for the Boiler and its components:
- Boiler recipe
- Pipe recipe
- Stone Furnace recipe
"""
# Inventory at the start of step {'iron-chest': 2, 'transport-belt': 50, 'burner-inserter': 32, 'small-electric-pole': 10, 'pipe': 15, 'boiler': 1, 'steam-engine': 1, 'burner-mining-drill': 3, 'electric-mining-drill': 1, 'stone-furnace': 9, 'assembling-machine-1': 1, 'coal': 50, 'iron-plate': 50, 'copper-plate': 50}
#Step Execution

# Print recipe for Boiler
print("Recipe for Boiler:")
boiler_recipe = get_prototype_recipe(Prototype.Boiler)
print(f"Ingredients: {boiler_recipe.ingredients}")
print(f"Energy required: {boiler_recipe.energy}")
print(f"Products: {boiler_recipe.products}")
print()

# Print recipe for Pipe
print("Recipe for Pipe:")
pipe_recipe = get_prototype_recipe(Prototype.Pipe)
print(f"Ingredients: {pipe_recipe.ingredients}")
print(f"Energy required: {pipe_recipe.energy}")
print(f"Products: {pipe_recipe.products}")
print()

# Print recipe for Stone Furnace
print("Recipe for Stone Furnace:")
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Ingredients: {stone_furnace_recipe.ingredients}")
print(f"Energy required: {stone_furnace_recipe.energy}")
print(f"Products: {stone_furnace_recipe.products}")
print()

# Print a summary of all recipes
print("Summary of recipes:")
print(f"Boiler: {boiler_recipe}")
print(f"Pipe: {pipe_recipe}")
print(f"Stone Furnace: {stone_furnace_recipe}")

# Assert to ensure we have all the required recipes
assert boiler_recipe is not None, "Failed to get Boiler recipe"
assert pipe_recipe is not None, "Failed to get Pipe recipe"
assert stone_furnace_recipe is not None, "Failed to get Stone Furnace recipe"

print("Successfully printed all required recipes.")


"""
Step 2: Gather resources. We need to gather the following resources:
- Collect the 7 stone from the wooden chest on the map
- Mine iron ore for crafting pipes
- Mine coal for fueling the furnace
"""
# Inventory at the start of step {'iron-chest': 2, 'transport-belt': 50, 'burner-inserter': 32, 'small-electric-pole': 10, 'pipe': 15, 'boiler': 1, 'steam-engine': 1, 'burner-mining-drill': 3, 'electric-mining-drill': 1, 'stone-furnace': 9, 'assembling-machine-1': 1, 'coal': 50, 'iron-plate': 50, 'copper-plate': 50}
#Step Execution

from factorio_instance import *

# Check current inventory
inventory = inspect_inventory()
print(f"Current inventory: {inventory}")

# Check if we already have enough stone
stone_count = inventory.get(Prototype.Stone, 0)
if stone_count < 7:
    # If we don't have enough stone, we need to mine it
    stone_to_mine = 7 - stone_count
    stone_position = nearest(Resource.Stone)
    move_to(stone_position)
    harvested_stone = harvest_resource(stone_position, stone_to_mine)
    print(f"Mined {harvested_stone} stone")

# Verify stone count
inventory = inspect_inventory()
stone_count = inventory.get(Prototype.Stone, 0)
assert stone_count >= 7, f"Failed to collect enough stone. Expected at least 7, but got {stone_count}"
print(f"Stone count: {stone_count}")

# Check if we need to mine iron ore
iron_plate_count = inventory.get(Prototype.IronPlate, 0)
if iron_plate_count < 4:  # We need 4 iron plates for 4 pipes
    iron_ore_to_mine = (4 - iron_plate_count) * 2  # Assuming 2 ore per plate
    iron_position = nearest(Resource.IronOre)
    move_to(iron_position)
    harvested_iron = harvest_resource(iron_position, iron_ore_to_mine)
    print(f"Mined {harvested_iron} iron ore")

# Check if we need to mine coal
coal_count = inventory.get(Prototype.Coal, 0)
if coal_count < 5:  # Assuming we need at least 5 coal for fueling
    coal_to_mine = 5 - coal_count
    coal_position = nearest(Resource.Coal)
    move_to(coal_position)
    harvested_coal = harvest_resource(coal_position, coal_to_mine)
    print(f"Mined {harvested_coal} coal")

# Print final inventory
inventory = inspect_inventory()
print(f"Final inventory after gathering resources: {inventory}")

# Verify we have all required resources
assert inventory.get(Prototype.Stone, 0) >= 7, "Not enough stone"
assert inventory.get(Prototype.IronOre, 0) >= 4 or inventory.get(Prototype.IronPlate, 0) >= 4, "Not enough iron ore or plates"
assert inventory.get(Prototype.Coal, 0) >= 5, "Not enough coal"

print("Successfully gathered all required resources")


"""
Step 3: Craft Stone Furnace and smelt iron plates. We need to:
- Craft a Stone Furnace using 5 stone
- Place the Stone Furnace and fuel it with coal
- Smelt iron ore into iron plates
"""
# Inventory at the start of step {'coal': 5, 'stone': 7, 'iron-ore': 8}
#Step Execution

# Craft Stone Furnace
craft_item(Prototype.StoneFurnace, 1)
print("Crafted 1 Stone Furnace")

# Find a suitable location to place the Stone Furnace
furnace_position = Position(x=0, y=0)  # You might want to adjust this based on your map
move_to(furnace_position)

# Place the Stone Furnace
furnace = place_entity(Prototype.StoneFurnace, Direction.UP, furnace_position)
print(f"Placed Stone Furnace at {furnace_position}")

# Fuel the Stone Furnace with coal
coal_to_insert = min(inspect_inventory()[Prototype.Coal], 5)  # Insert up to 5 coal
furnace = insert_item(Prototype.Coal, furnace, coal_to_insert)
print(f"Inserted {coal_to_insert} coal into the Stone Furnace")

# Insert iron ore into the Stone Furnace
iron_ore_to_insert = inspect_inventory()[Prototype.IronOre]
furnace = insert_item(Prototype.IronOre, furnace, iron_ore_to_insert)
print(f"Inserted {iron_ore_to_insert} iron ore into the Stone Furnace")

# Wait for smelting to complete (0.7 seconds per iron ore)
sleep(iron_ore_to_insert * 0.7)

# Extract iron plates from the Stone Furnace
expected_iron_plates = iron_ore_to_insert  # Assuming 1:1 ratio for ore to plate
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, furnace.position, expected_iron_plates)
    iron_plates_in_inventory = inspect_inventory()[Prototype.IronPlate]
    if iron_plates_in_inventory >= expected_iron_plates:
        break
    sleep(5)  # Wait a bit more if not all plates are ready

print(f"Extracted {iron_plates_in_inventory} iron plates from the Stone Furnace")

# Check if we have the expected number of iron plates
assert iron_plates_in_inventory >= expected_iron_plates, f"Failed to smelt enough iron plates. Expected {expected_iron_plates}, but got {iron_plates_in_inventory}"

print(f"Successfully crafted Stone Furnace and smelted {iron_plates_in_inventory} iron plates")
print(f"Current inventory: {inspect_inventory()}")


"""
Step 4: Craft components and Boiler. We need to:
- Craft 4 Pipes using the iron plates
- Craft the Stone Furnace for the Boiler recipe using the remaining 2 stone
- Craft the Boiler using 4 Pipes and 1 Stone Furnace
"""
# Inventory at the start of step {'stone': 2, 'iron-plate': 8}
#Step Execution

# Step 1: Craft 4 pipes
craft_item(Prototype.Pipe, 4)
print("Crafted 4 pipes")

# Check if we have the pipes
inventory = inspect_inventory()
assert inventory[Prototype.Pipe] >= 4, f"Failed to craft 4 pipes. Only have {inventory[Prototype.Pipe]}"

# Step 2: Mine additional stone
stone_needed = 5 - inventory[Prototype.Stone]
if stone_needed > 0:
    stone_position = nearest(Resource.Stone)
    move_to(stone_position)
    harvested_stone = harvest_resource(stone_position, stone_needed)
    print(f"Mined {harvested_stone} additional stone")

# Verify we have enough stone
inventory = inspect_inventory()
assert inventory[Prototype.Stone] >= 5, f"Not enough stone. Have {inventory[Prototype.Stone]}, need 5"

# Step 3: Craft 1 stone furnace
craft_item(Prototype.StoneFurnace, 1)
print("Crafted 1 stone furnace")

# Check if we have the stone furnace
inventory = inspect_inventory()
assert inventory[Prototype.StoneFurnace] >= 1, f"Failed to craft stone furnace. Have {inventory[Prototype.StoneFurnace]}"

# Step 4: Craft 1 boiler
craft_item(Prototype.Boiler, 1)
print("Crafted 1 boiler")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

# Verify we have crafted the boiler
assert final_inventory[Prototype.Boiler] >= 1, f"Failed to craft boiler. Have {final_inventory[Prototype.Boiler]}"

print("Successfully crafted all components and the boiler")


"""
Step 5: Verify success. Check if a Boiler is in the inventory.
##
"""
# Inventory at the start of step {'boiler': 1, 'iron-plate': 4}
#Step Execution

# Check the current inventory
inventory = inspect_inventory()
print(f"Current inventory: {inventory}")

# Check if we have at least one Boiler in the inventory
boiler_count = inventory.get(Prototype.Boiler, 0)

# Assert that we have at least one Boiler
assert boiler_count >= 1, f"Failed to craft Boiler. Expected at least 1, but got {boiler_count}"

# If the assertion passes, print a success message
print(f"Success! We have {boiler_count} Boiler(s) in the inventory.")
print("We have successfully completed the objective of crafting a Boiler.")
