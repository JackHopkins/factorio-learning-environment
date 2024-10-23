from factorio_instance import *

"""
Main Objective: We require one BurnerInserter. The final success should be checked by looking if a BurnerInserter is in inventory
"""



"""
Step 1: Print recipes. We need to craft a BurnerInserter. The recipe is:
BurnerInserter - Crafting requires 1 iron gear wheel, 1 iron plate. In total all ingredients require at least 3 iron plates.
"""
# Inventory at the start of step {}
#Step Execution

# Get the recipe for BurnerInserter
burner_inserter_recipe = get_prototype_recipe(Prototype.BurnerInserter)

# Print the recipe details
print("BurnerInserter Recipe:")
print(f"Direct ingredients: {burner_inserter_recipe.ingredients}")

# Calculate total iron plates needed
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
iron_plates_for_gear = iron_gear_wheel_recipe.ingredients[0].count
total_iron_plates = iron_plates_for_gear + 1  # 2 for gear wheel + 1 direct

# Print the total iron plates needed
print(f"Total iron plates required: {total_iron_plates}")

# Print summary of resources needed
print("\nSummary of resources needed:")
print(f"- Iron Plates: {total_iron_plates}")
print("- Iron Gear Wheel: 1 (crafted from 2 iron plates)")
print("- Additional Iron Plate: 1")

# Assert to ensure we have the correct information
assert total_iron_plates == 3, f"Expected 3 total iron plates, but calculated {total_iron_plates}"

print("\nRecipe printing completed successfully.")


"""
Step 2: Gather resources. We need to mine the following resources:
- At least 3 iron ore
- At least 5 stone for crafting a stone furnace
- Some coal for fuel
"""
# Inventory at the start of step {}
#Step Execution

# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 5),  # Gather a bit more than 3
    (Resource.Stone, 7),    # Gather a bit more than 5
    (Resource.Coal, 10)     # Gather some extra for fuel
]

# Loop through each resource and gather it
for resource, amount in resources_to_gather:
    # Find the nearest patch of the resource
    resource_position = nearest(resource)
    print(f"Moving to nearest {resource} at {resource_position}")
    
    # Move to the resource
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, amount)
    print(f"Harvested {harvested} {resource}")
    
    # Check if we've gathered enough
    inventory = inspect_inventory()
    actual_amount = inventory.get(resource, 0)
    print(f"Current inventory of {resource}: {actual_amount}")
    
    assert actual_amount >= amount, f"Failed to gather enough {resource}. Expected at least {amount}, but got {actual_amount}"

# Print final inventory
final_inventory = inspect_inventory()
print("Final inventory after gathering resources:")
print(final_inventory)

# Additional checks
assert final_inventory.get(Resource.IronOre, 0) >= 3, "Not enough iron ore gathered"
assert final_inventory.get(Resource.Stone, 0) >= 5, "Not enough stone gathered"
assert final_inventory.get(Resource.Coal, 0) >= 5, "Not enough coal gathered"

print("Resource gathering completed successfully!")


"""
Step 3: Craft and set up smelting. We need to:
- Craft a stone furnace using 5 stone
- Place the stone furnace
- Fuel the furnace with coal
"""
# Inventory at the start of step {'coal': 10, 'stone': 7, 'iron-ore': 5}
#Step Execution

# Craft a stone furnace
print("Attempting to craft a stone furnace...")
crafted = craft_item(Prototype.StoneFurnace, 1)
assert crafted == 1, f"Failed to craft stone furnace. Crafted: {crafted}"
print("Successfully crafted a stone furnace.")

# Find a suitable location to place the furnace (near coal)
coal_position = nearest(Resource.Coal)
furnace_position = Position(x=coal_position.x + 2, y=coal_position.y)
print(f"Planning to place furnace at {furnace_position}")

# Move to the chosen position
move_to(furnace_position)

# Place the stone furnace
print("Attempting to place the stone furnace...")
furnace = place_entity(Prototype.StoneFurnace, Direction.UP, furnace_position)
print(f"Stone furnace placed at {furnace.position}")

# Fuel the furnace with coal
print("Fueling the furnace with coal...")
coal_to_insert = min(5, inspect_inventory()[Prototype.Coal])  # Insert up to 5 coal
furnace = insert_item(Prototype.Coal, furnace, coal_to_insert)
print(f"Inserted {coal_to_insert} coal into the furnace")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory after crafting and setting up furnace:")
print(final_inventory)

# Ensure we have the furnace in our game world
furnaces = get_entities({Prototype.StoneFurnace})
assert len(furnaces) > 0, "Failed to find the placed stone furnace in the game world"

print("Stone furnace crafted, placed, and fueled successfully!")


"""
Step 4: Smelt iron plates. We need to:
- Smelt at least 3 iron ore into iron plates
"""
# Inventory at the start of step {'coal': 5, 'stone': 2, 'iron-ore': 5}
#Step Execution

# Get the stone furnace
furnaces = get_entities({Prototype.StoneFurnace})
furnace = furnaces[0]  # We know there's only one furnace

# Move to the furnace
move_to(furnace.position)

# Get the amount of iron ore in the inventory
iron_ore_count = inspect_inventory()[Prototype.IronOre]
print(f"Iron ore in inventory: {iron_ore_count}")

# Insert all iron ore into the furnace
furnace = insert_item(Prototype.IronOre, furnace, iron_ore_count)
print(f"Inserted {iron_ore_count} iron ore into the furnace")

# Calculate the smelting time (3.2 seconds per iron plate)
smelting_time = iron_ore_count * 3.2
print(f"Waiting for {smelting_time} seconds for smelting to complete")

# Wait for smelting to complete
sleep(smelting_time)

# Extract iron plates from the furnace
max_attempts = 5
for attempt in range(max_attempts):
    extract_item(Prototype.IronPlate, furnace.position, iron_ore_count)
    iron_plates_in_inventory = inspect_inventory()[Prototype.IronPlate]
    print(f"Attempt {attempt + 1}: Extracted iron plates. Current inventory: {iron_plates_in_inventory}")
    
    if iron_plates_in_inventory >= 3:
        break
    
    if attempt < max_attempts - 1:
        print("Not enough iron plates extracted. Waiting for 5 seconds before next attempt.")
        sleep(5)

# Check if we have at least 3 iron plates
final_iron_plates = inspect_inventory()[Prototype.IronPlate]
print(f"Final iron plates in inventory: {final_iron_plates}")

assert final_iron_plates >= 3, f"Failed to smelt enough iron plates. Expected at least 3, but got {final_iron_plates}"

print("Successfully smelted iron plates!")
print(f"Current inventory: {inspect_inventory()}")


"""
Step 5: Craft BurnerInserter. We need to:
- Craft 1 iron gear wheel using 2 iron plates
- Craft 1 BurnerInserter using 1 iron gear wheel and 1 iron plate
- Check inventory to confirm BurnerInserter is crafted successfully
##
"""
# Inventory at the start of step {'coal': 5, 'stone': 2, 'iron-plate': 4}
#Step Execution

# Step 1: Craft iron gear wheel
print("Crafting iron gear wheel...")
craft_item(Prototype.IronGearWheel, 1)
inventory = inspect_inventory()
assert inventory[Prototype.IronGearWheel] >= 1, f"Failed to craft iron gear wheel. Current inventory: {inventory}"
print(f"Successfully crafted iron gear wheel. Current inventory: {inventory}")

# Step 2: Craft BurnerInserter
print("Crafting BurnerInserter...")
craft_item(Prototype.BurnerInserter, 1)
inventory = inspect_inventory()
assert inventory[Prototype.BurnerInserter] >= 1, f"Failed to craft BurnerInserter. Current inventory: {inventory}"
print(f"Successfully crafted BurnerInserter. Current inventory: {inventory}")

# Step 3: Verify inventory
final_inventory = inspect_inventory()
print(f"Final inventory after crafting: {final_inventory}")

# Assert to ensure we have at least one BurnerInserter
assert final_inventory[Prototype.BurnerInserter] >= 1, f"Expected at least 1 BurnerInserter, but found {final_inventory[Prototype.BurnerInserter]}"

print("Successfully crafted BurnerInserter and verified inventory!")
