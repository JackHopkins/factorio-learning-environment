from factorio_instance import *

"""
Main Objective: We need to craft 4 small electric poles. The final success should be checked by looking if the small electric poles are in inventory
"""



"""
Step 1: Print recipes and gather resources. We need to print the recipe for small electric poles and gather the necessary resources.
- Print recipe for small electric poles
- Gather copper ore, coal, stone, and wood
- Craft a stone furnace using the gathered stone
"""
# Inventory at the start of step {}
#Step Execution

# Print the recipe for small electric poles
small_electric_pole_recipe = get_prototype_recipe(Prototype.SmallElectricPole)
print(f"Recipe for Small Electric Pole: {small_electric_pole_recipe}")

# Define the resources we need to gather
resources_needed = [
    (Resource.CopperOre, 10),  # A bit extra for inefficiencies
    (Resource.Coal, 10),
    (Resource.Stone, 10),
    (Resource.Wood, 10)
]

# Gather the necessary resources
for resource, amount in resources_needed:
    resource_position = nearest(resource)
    print(f"Moving to {resource} at position {resource_position}")
    move_to(resource_position)
    
    harvested = harvest_resource(resource_position, amount)
    print(f"Harvested {harvested} {resource}")

    # Check if we harvested enough
    inventory = inspect_inventory()
    assert inventory[resource] >= amount, f"Failed to harvest enough {resource}. Got {inventory[resource]}, needed {amount}"

print("Current inventory after gathering resources:")
print(inspect_inventory())

# Craft a stone furnace
furnace_crafted = craft_item(Prototype.StoneFurnace, 1)
print(f"Crafted {furnace_crafted} Stone Furnace")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory after crafting Stone Furnace:")
print(final_inventory)

# Assert that we have the Stone Furnace in our inventory
assert final_inventory[Prototype.StoneFurnace] >= 1, "Failed to craft Stone Furnace"

print("Successfully completed step 1: Printed recipes, gathered resources, and crafted Stone Furnace")


"""
Step 2: Smelt copper plates. We need to smelt copper ore into copper plates.
- Place the stone furnace
- Fuel the furnace with coal
- Smelt copper ore into copper plates
"""
# Inventory at the start of step {'stone-furnace': 1, 'wood': 10, 'coal': 10, 'stone': 5, 'copper-ore': 10}
#Step Execution

# Place the stone furnace
furnace_position = Position(x=0, y=0)  # Choose a position near the player
move_to(furnace_position)
furnace = place_entity(Prototype.StoneFurnace, Direction.UP, furnace_position)
print(f"Placed stone furnace at {furnace_position}")

# Get the amount of coal and copper ore in the inventory
coal_amount = inspect_inventory()[Prototype.Coal]
copper_ore_amount = inspect_inventory()[Prototype.CopperOre]
print(f"Coal in inventory: {coal_amount}")
print(f"Copper ore in inventory: {copper_ore_amount}")

# Insert coal into the furnace (use half of the coal for fuel)
coal_to_insert = coal_amount // 2
furnace = insert_item(Prototype.Coal, furnace, coal_to_insert)
print(f"Inserted {coal_to_insert} coal into the furnace")

# Insert copper ore into the furnace
furnace = insert_item(Prototype.CopperOre, furnace, copper_ore_amount)
print(f"Inserted {copper_ore_amount} copper ore into the furnace")

# Calculate expected copper plates and smelting time
expected_copper_plates = copper_ore_amount
smelting_time = copper_ore_amount * 3.2  # 3.2 seconds per copper plate

# Wait for smelting to complete
print(f"Waiting {smelting_time} seconds for smelting to complete")
sleep(smelting_time)

# Extract copper plates from the furnace
max_attempts = 5
for attempt in range(max_attempts):
    extract_item(Prototype.CopperPlate, furnace.position, expected_copper_plates)
    copper_plates_in_inventory = inspect_inventory()[Prototype.CopperPlate]
    
    if copper_plates_in_inventory >= expected_copper_plates:
        print(f"Successfully extracted {copper_plates_in_inventory} copper plates")
        break
    
    if attempt < max_attempts - 1:
        print(f"Extracted only {copper_plates_in_inventory} copper plates. Waiting and trying again...")
        sleep(5)

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory after smelting copper plates:")
print(final_inventory)

# Assert that we have the expected number of copper plates
assert final_inventory[Prototype.CopperPlate] >= expected_copper_plates, f"Failed to smelt enough copper plates. Expected at least {expected_copper_plates}, but got {final_inventory[Prototype.CopperPlate]}"

print("Successfully completed step 2: Smelted copper plates")


"""
Step 3: Craft copper cables. We need to craft copper cables as an intermediate product.
- Craft copper cables using the smelted copper plates
"""
# Inventory at the start of step {'wood': 10, 'coal': 5, 'stone': 5, 'copper-plate': 10}
#Step Execution

# Get the recipe for copper cable
copper_cable_recipe = get_prototype_recipe(Prototype.CopperCable)
print(f"Recipe for Copper Cable: {copper_cable_recipe}")

# Get the recipe for small electric pole to determine the required copper cables
small_electric_pole_recipe = get_prototype_recipe(Prototype.SmallElectricPole)
copper_cables_per_pole = next((ingredient.count for ingredient in small_electric_pole_recipe.ingredients if ingredient.name == 'copper-cable'), 2)  # Default to 2 if not found

# Calculate the number of copper cables needed (4 poles * cables per pole)
copper_cables_needed = 4 * copper_cables_per_pole

# Assume 1 copper plate produces 2 copper cables (standard Factorio recipe)
copper_plates_required = copper_cables_needed // 2

print(f"We need to craft {copper_cables_needed} copper cables, requiring {copper_plates_required} copper plates")

# Check if we have enough copper plates
inventory = inspect_inventory()
copper_plates_available = inventory[Prototype.CopperPlate]

if copper_plates_available < copper_plates_required:
    print(f"Warning: Not enough copper plates. Have {copper_plates_available}, need {copper_plates_required}")
    copper_cables_to_craft = copper_plates_available * 2
else:
    copper_cables_to_craft = copper_cables_needed

# Craft copper cables
copper_cables_crafted = craft_item(Prototype.CopperCable, copper_cables_to_craft)
print(f"Crafted {copper_cables_crafted} copper cables")

# Verify the crafting result
final_inventory = inspect_inventory()
print("Final inventory after crafting copper cables:")
print(final_inventory)

# Assert that we have crafted the correct amount of copper cables
assert final_inventory[Prototype.CopperCable] >= copper_cables_needed, f"Failed to craft enough copper cables. Needed {copper_cables_needed}, but got {final_inventory[Prototype.CopperCable]}"

print("Successfully completed step 3: Crafted copper cables")


"""
Step 4: Craft small electric poles. We will now craft the required small electric poles.
- Craft 4 small electric poles using the copper cables and wood
"""
# Inventory at the start of step {'wood': 10, 'coal': 5, 'stone': 5, 'copper-plate': 6, 'copper-cable': 8}
#Step Execution

# Get the recipe for small electric poles
small_electric_pole_recipe = get_prototype_recipe(Prototype.SmallElectricPole)
print(f"Recipe for Small Electric Pole: {small_electric_pole_recipe}")

# Check our current inventory
current_inventory = inspect_inventory()
print(f"Current inventory: {current_inventory}")

# Extract the required ingredients from the recipe
wood_required = next(ingredient.count for ingredient in small_electric_pole_recipe.ingredients if ingredient.name == 'wood')
copper_cable_required = next(ingredient.count for ingredient in small_electric_pole_recipe.ingredients if ingredient.name == 'copper-cable')

# Calculate total requirements for 4 poles
total_wood_required = wood_required * 4
total_copper_cable_required = copper_cable_required * 4

print(f"To craft 4 small electric poles, we need: {total_wood_required} wood and {total_copper_cable_required} copper cables")

# Check if we have enough materials
if current_inventory['wood'] < total_wood_required or current_inventory['copper-cable'] < total_copper_cable_required:
    print("Error: Not enough materials to craft 4 small electric poles")
else:
    # Craft 4 small electric poles
    poles_crafted = craft_item(Prototype.SmallElectricPole, 4)
    print(f"Crafted {poles_crafted} small electric poles")

    # Verify the crafting result
    final_inventory = inspect_inventory()
    print("Final inventory after crafting small electric poles:")
    print(final_inventory)

    # Assert that we have crafted the correct number of poles
    assert final_inventory[Prototype.SmallElectricPole] >= 4, f"Failed to craft 4 small electric poles. Only crafted {final_inventory[Prototype.SmallElectricPole]}"

    print("Successfully crafted 4 small electric poles")


"""
Step 5: Confirm success. We need to check if the crafting was successful.
- Check inventory to confirm the presence of 4 small electric poles
##
"""
# Inventory at the start of step {'small-electric-pole': 4, 'wood': 8, 'coal': 5, 'stone': 5, 'copper-plate': 6, 'copper-cable': 4}
#Step Execution

# Check the inventory to confirm the presence of 4 small electric poles
inventory = inspect_inventory()
print("Current inventory:")
print(inventory)

# Check if we have at least 4 small electric poles
small_electric_poles_count = inventory[Prototype.SmallElectricPole]
print(f"Number of small electric poles in inventory: {small_electric_poles_count}")

# Assert that we have at least 4 small electric poles
assert small_electric_poles_count >= 4, f"Failed to craft 4 small electric poles. Only {small_electric_poles_count} found in inventory."

# If the assertion passes, print a success message
print("Success: Crafted 4 small electric poles successfully!")

# Additional check: Print out the remaining resources
print("\nRemaining resources:")
print(f"Wood: {inventory['wood']}")
print(f"Copper Cable: {inventory['copper-cable']}")
print(f"Copper Plate: {inventory['copper-plate']}")
print(f"Coal: {inventory['coal']}")
print(f"Stone: {inventory['stone']}")

print("\nObjective completed: Crafted 4 small electric poles.")
