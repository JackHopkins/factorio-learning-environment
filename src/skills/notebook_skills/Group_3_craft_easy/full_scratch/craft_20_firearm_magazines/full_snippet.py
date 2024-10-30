from factorio_instance import *

"""
Main Objective: We need to craft 6 firearm magazines. The final success should be checked by looking if the firearm magazines are in inventory
"""



"""
Step 1: Print recipes and gather resources. We need to craft firearm magazines and a stone furnace for smelting. We'll gather the following resources:
- Print recipe for FirearmMagazine and StoneFurnace
- Mine iron ore (at least 24 for 6 magazines)
- Mine stone (at least 5 for the furnace)
- Mine coal (for fuel)
"""
# Inventory at the start of step {}
#Step Execution

# Print recipes for FirearmMagazine and StoneFurnace
firearm_magazine_recipe = get_prototype_recipe(Prototype.FirearmMagazine)
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)

print(f"FirearmMagazine recipe: {firearm_magazine_recipe}")
print(f"StoneFurnace recipe: {stone_furnace_recipe}")

# Calculate required resources
iron_ore_needed = 24  # At least 24 for 6 magazines
stone_needed = 5  # At least 5 for the furnace
coal_needed = 10  # Arbitrary amount for fuel, adjust as needed

# List of resources to gather
resources_to_gather = [
    (Resource.IronOre, iron_ore_needed),
    (Resource.Stone, stone_needed),
    (Resource.Coal, coal_needed)
]

# Gather resources
for resource, amount_needed in resources_to_gather:
    resource_position = nearest(resource)
    print(f"Moving to nearest {resource} patch at {resource_position}")
    move_to(resource_position)
    
    print(f"Harvesting {amount_needed} {resource}")
    harvested = harvest_resource(resource_position, amount_needed)
    
    # Verify harvested amount
    inventory = inspect_inventory()
    actual_amount = inventory.get(resource, 0)
    print(f"Harvested {actual_amount} {resource}")
    
    assert actual_amount >= amount_needed, f"Failed to harvest enough {resource}. Needed {amount_needed}, but only got {actual_amount}"

# Print final inventory
final_inventory = inspect_inventory()
print(f"Final inventory after gathering resources: {final_inventory}")

# Verify we have all required resources
assert final_inventory.get(Resource.IronOre, 0) >= iron_ore_needed, f"Not enough iron ore. Needed {iron_ore_needed}, but only have {final_inventory.get(Resource.IronOre, 0)}"
assert final_inventory.get(Resource.Stone, 0) >= stone_needed, f"Not enough stone. Needed {stone_needed}, but only have {final_inventory.get(Resource.Stone, 0)}"
assert final_inventory.get(Resource.Coal, 0) >= coal_needed, f"Not enough coal. Needed {coal_needed}, but only have {final_inventory.get(Resource.Coal, 0)}"

print("Successfully gathered all required resources!")


"""
Step 2: Create smelting setup. We need to smelt iron ore into iron plates:
- Craft a stone furnace
- Place the stone furnace
- Fuel the furnace with coal
"""
# Inventory at the start of step {'coal': 10, 'stone': 5, 'iron-ore': 24}
#Step Execution

# Craft a stone furnace
print("Crafting a stone furnace")
craft_item(Prototype.StoneFurnace, 1)
print(f"Inventory after crafting: {inspect_inventory()}")

# Find a suitable location to place the furnace
# We'll place it near the coal patch for easy refueling
coal_position = nearest(Resource.Coal)
furnace_position = Position(x=coal_position.x + 2, y=coal_position.y)

# Move to the chosen position
print(f"Moving to position {furnace_position} to place the furnace")
move_to(furnace_position)

# Place the stone furnace
print("Placing the stone furnace")
furnace = place_entity(Prototype.StoneFurnace, direction=Direction.UP, position=furnace_position)
print(f"Stone furnace placed at {furnace.position}")

# Fuel the furnace with coal
print("Fueling the furnace with coal")
coal_to_insert = min(5, inspect_inventory()[Prototype.Coal])  # Insert up to 5 coal, or all we have if less
furnace = insert_item(Prototype.Coal, furnace, coal_to_insert)
print(f"Inserted {coal_to_insert} coal into the furnace")

# Print the final inventory
print(f"Final inventory after setting up the furnace: {inspect_inventory()}")

# Verify that the furnace is placed and fueled
entities = get_entities({Prototype.StoneFurnace}, furnace_position, radius=1)
assert len(entities) > 0, "Failed to place the stone furnace"
print("Stone furnace successfully placed and fueled!")


"""
Step 3: Smelt iron plates. We need to smelt the iron ore into iron plates:
- Put iron ore into the furnace
- Wait for the smelting process to complete
- Collect the iron plates from the furnace
"""
# Inventory at the start of step {'coal': 5, 'iron-ore': 24}
#Step Execution

# Get the stone furnace entity
furnaces = get_entities({Prototype.StoneFurnace})
assert len(furnaces) > 0, "No stone furnace found on the map"
furnace = furnaces[0]

# Get the amount of iron ore in the inventory
iron_ore_count = inspect_inventory()[Prototype.IronOre]
print(f"Iron ore in inventory: {iron_ore_count}")

# Insert all iron ore into the furnace
print(f"Inserting {iron_ore_count} iron ore into the furnace")
furnace = insert_item(Prototype.IronOre, furnace, iron_ore_count)

# Calculate smelting time (3.2 seconds per iron plate)
smelting_time = iron_ore_count * 3.2
print(f"Waiting for {smelting_time} seconds for smelting to complete")

# Wait for smelting to complete
sleep(smelting_time)

# Extract iron plates from the furnace
print("Extracting iron plates from the furnace")
max_attempts = 5
expected_iron_plates = iron_ore_count  # 1 iron ore = 1 iron plate

for attempt in range(max_attempts):
    extract_item(Prototype.IronPlate, furnace.position, expected_iron_plates)
    iron_plates_in_inventory = inspect_inventory()[Prototype.IronPlate]
    
    if iron_plates_in_inventory >= expected_iron_plates:
        break
    
    print(f"Attempt {attempt + 1}: Extracted {iron_plates_in_inventory} iron plates. Waiting for more...")
    sleep(5)  # Wait a bit more if not all plates are ready

# Verify that we have the correct amount of iron plates
final_iron_plates = inspect_inventory()[Prototype.IronPlate]
print(f"Final iron plates in inventory: {final_iron_plates}")

assert final_iron_plates >= expected_iron_plates, f"Failed to smelt enough iron plates. Expected {expected_iron_plates}, but got {final_iron_plates}"

print("Successfully smelted iron ore into iron plates!")
print(f"Final inventory: {inspect_inventory()}")


"""
Step 4: Craft firearm magazines. We'll craft the 6 firearm magazines:
- Use the crafting menu to craft 6 firearm magazines using the iron plates
"""
# Inventory at the start of step {'coal': 5, 'iron-plate': 24}
#Step Execution

# Calculate the number of firearm magazines we need to craft
magazines_to_craft = 6

# Print the current inventory before crafting
print(f"Inventory before crafting: {inspect_inventory()}")

# Craft the firearm magazines
print(f"Crafting {magazines_to_craft} firearm magazines...")
crafted = craft_item(Prototype.FirearmMagazine, magazines_to_craft)

# Verify that we crafted the correct number of magazines
assert crafted == magazines_to_craft, f"Failed to craft all magazines. Crafted {crafted} out of {magazines_to_craft}"

# Check the inventory after crafting
inventory = inspect_inventory()
print(f"Inventory after crafting: {inventory}")

# Verify that we have the correct number of magazines in our inventory
magazines_in_inventory = inventory.get(Prototype.FirearmMagazine, 0)
assert magazines_in_inventory == magazines_to_craft, f"Incorrect number of magazines in inventory. Expected {magazines_to_craft}, but found {magazines_in_inventory}"

# Verify that we used the correct amount of iron plates
iron_plates_used = 24  # 6 magazines * 4 iron plates each
iron_plates_remaining = inventory.get(Prototype.IronPlate, 0)
assert iron_plates_remaining == 0, f"Incorrect number of iron plates remaining. Expected 0, but found {iron_plates_remaining}"

print(f"Successfully crafted {magazines_to_craft} firearm magazines!")


"""
Step 5: Confirm success. Check the inventory to ensure we have 6 firearm magazines.

##
"""
# Inventory at the start of step {'coal': 5, 'firearm-magazine': 6}
#Step Execution

# Check the inventory to confirm we have 6 firearm magazines
inventory = inspect_inventory()
print(f"Final inventory: {inventory}")

# Get the count of firearm magazines in the inventory
firearm_magazines_count = inventory.get(Prototype.FirearmMagazine, 0)

# Assert that we have exactly 6 firearm magazines
assert firearm_magazines_count == 6, f"Expected 6 firearm magazines, but found {firearm_magazines_count}"

# If the assertion passes, print a success message
print("Success! We have crafted 6 firearm magazines.")
print("Main objective completed: 6 firearm magazines have been crafted and are in the inventory.")

# Additional check to ensure we don't have any iron plates left (all should have been used)
iron_plates_count = inventory.get(Prototype.IronPlate, 0)
assert iron_plates_count == 0, f"Expected 0 iron plates remaining, but found {iron_plates_count}"

print("All iron plates have been used in crafting, as expected.")

# Final summary
print("\nFinal Summary:")
print(f"- Firearm Magazines: {firearm_magazines_count}")
print(f"- Remaining Coal: {inventory.get(Prototype.Coal, 0)}")
print(f"- Remaining Iron Plates: {iron_plates_count}")

print("\nAll objectives have been successfully completed!")
