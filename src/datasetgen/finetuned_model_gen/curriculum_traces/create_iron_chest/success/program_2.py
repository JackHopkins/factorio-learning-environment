

from factorio_instance import *

"""
Planning:
We need to create an iron-chest. To do this, we need to smelt iron-ore into iron-plates and then craft the iron-chest.
We have a stone furnace on the map, which we can use for smelting.
We need to mine some coal for fuel and then smelt the iron-ore into iron-plates.
Finally, we need to craft the iron-chest.
"""

"""
Step 1: Print recipe for iron-chest
"""
# Get the recipe for iron-chest
recipe = get_prototype_recipe(Prototype.IronChest)

# Print the recipe details
print("Recipe for iron-chest:")
print(f"Ingredients: {recipe.ingredients}")

"""
Step 2: Smelt iron ore into iron plates
- Move to the stone furnace
- Add coal as fuel to the furnace
- Add iron ore to the furnace
- Wait for smelting to complete
- Extract iron plates
"""
# Inventory before smelting: {'stone-furnace': 1, 'coal': 1, 'stone': 1, 'iron-ore': 14, 'iron-plate': 2, 'iron-gear-wheel': 3, 'firearm-magazine': 1}
# We need to smelt 14 iron ore into 14 iron plates

# Step 1: Print recipe for iron-plate
recipe = get_prototype_recipe(Prototype.IronPlate)
print("Recipe for iron-plate:")
print(f"Ingredients: {recipe.ingredients}")

# Step 2: Move to the stone furnace
furnace_position = Position(x=0, y=0)
move_to(furnace_position)
print(f"Moved to stone furnace at position: {furnace_position}")

# Step 3: Add coal as fuel to the furnace
coal_in_inventory = inspect_inventory()[Prototype.Coal]
print(f"Coal in inventory before adding to furnace: {coal_in_inventory}")

# We need to mine 1 more coal for fuel
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, quantity=1)

# Move back to the furnace
move_to(furnace_position)

updated_coal_in_inventory = inspect_inventory()[Prototype.Coal]
print(f"Updated coal in inventory after mining: {updated_coal_in_inventory}")

furnace = get_entity(Prototype.StoneFurnace, furnace_position)
insert_item(Prototype.Coal, furnace, quantity=1)
print("Inserted 1 coal into the furnace as fuel")

# Step 4: Add iron ore to the furnace
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
print(f"Iron ore in inventory before adding to furnace: {iron_ore_in_inventory}")

# Insert all available iron ore into the furnace
insert_item(Prototype.IronOre, furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} iron ore into the furnace")

# Step 5: Wait for smelting to complete
smelting_time = 0.7 * iron_ore_in_inventory
sleep(int(smelting_time))
print(f"Waited for {smelting_time} seconds for smelting to complete")

# Step 6: Extract iron plates
iron_plates_before_extraction = inspect_inventory()[Prototype.IronPlate]
print(f"Iron plates in inventory before extraction: {iron_plates_before_extraction}")

# Attempt to extract all potential iron plates
max_possible_plates_to_extract = 14
extract_item(Prototype.IronPlate, furnace.position, max_possible_plates_to_extract)

iron_plates_after_extraction = inspect_inventory()[Prototype.IronPlate]
print(f"Iron plates in inventory after extraction: {iron_plates_after_extraction}")

assert iron_plates_after_extraction >= 8, f"Expected at least 8 iron plates, but got {iron_plates_after_extraction}"
print("Successfully smelted iron ore into iron plates.")

"""
Step 3: Craft iron-chest
"""
# Craft the iron-chest
craft_item(Prototype.IronChest, quantity=1)

# Verify that we have crafted the iron-chest
inventory = inspect_inventory()
assert inventory[Prototype.IronChest] >= 1, "Failed to craft iron-chest"
print("Successfully crafted an iron-chest")

