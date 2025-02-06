
from instance import *

"""
Step 1: Print recipes. We need to print the recipe for fast-underground-belt, iron-gear-wheel and underground-belt
"""
# Get the recipe for fast-underground-belt
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)

# Get the recipe for iron-gear-wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)

# Get the recipe for underground-belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)

print("To craft a fast-underground-belt, we need the following resources:")
print("- 20 iron gear wheels")
print("- 2 underground-belts")

print("\nRecipes:")
print("\nfast-underground-belt recipe:")
print(fast_underground_belt_recipe)

print("\niron-gear-wheel recipe:")
print(iron_gear_wheel_recipe)

print("\nunderground-belt recipe:")
print(underground_belt_recipe)

print("\nPlan for crafting fast-underground-belt:")
print("1. Craft 40 iron gear wheels (20 for fast-underground-belt, 20 for underground-belt)")
print("2. Craft 2 underground-belts (each requires 10 iron gear wheels)")
print("3. Craft 1 fast-underground-belt (requires 20 iron gear wheels and 2 underground-belts)")

print("\nWe need to gather enough iron plates to craft all the required components.")


"""
Step 2: Print recipes. We need to print the recipe for fast-underground-belt, iron-gear-wheel and underground-belt
"""
# Print the recipe for fast-underground-belt
print("Fast Underground Belt recipe:")
print("Ingredients:")
print("- 20 iron gear wheels")
print("- 2 underground-belts")

# Print the recipe for iron-gear-wheel
print("\nIron Gear Wheel recipe:")
print("Ingredients:")
print("- 2 iron plates")

# Print the recipe for underground-belt
print("\nUnderground Belt recipe:")
print("Ingredients:")
print("- 10 iron gear wheels")
print("- 1 iron plate")

print("\nTo craft a fast-underground-belt, we need a total of 40 iron gear wheels and 2 iron plates.")
print("This means we need at least 82 iron plates in total (40 for gear wheels, 2 for underground belts).")
print("We also need to craft 2 underground-belts using 20 of the gear wheels and 2 iron plates.")

print("\nSteps to craft fast-underground-belt:")
print("1. Gather at least 82 iron plates")
print("2. Craft 40 iron gear wheels")
print("3. Craft 2 underground-belts using 20 gear wheels and 2 iron plates")
print("4. Craft 1 fast-underground-belt using 20 gear wheels and 2 underground-belts")


"""
Step 3: Gather resources. We need to gather at least 82 iron plates
"""
from instance import *

# Define the minimum required iron plates
min_iron_plates = 82

# Find the nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
print(f"Nearest iron ore found at: {iron_ore_position}")

# Move to the iron ore patch
move_to(iron_ore_position)
print(f"Moved to iron ore patch at: {iron_ore_position}")

# Harvest iron ore (assuming a 1:1 ratio for ore to plates)
harvested_iron = harvest_resource(iron_ore_position, min_iron_plates)
print(f"Harvested {harvested_iron} iron ore")

# Verify that enough iron ore was harvested
current_inventory = inspect_inventory()
actual_iron_ore = current_inventory.get(Prototype.IronOre, 0)
assert actual_iron_ore >= min_iron_plates, f"Failed to harvest enough iron ore! Expected at least {min_iron_plates}, but got {actual_iron_ore}"
print(f"Successfully gathered {actual_iron_ore} iron ore")

# Find the nearest coal patch
coal_position = nearest(Resource.Coal)
print(f"Nearest coal found at: {coal_position}")

# Move to the coal patch
move_to(coal_position)
print(f"Moved to coal patch at: {coal_position}")

# Harvest coal (assuming a 1:1 ratio for coal to smelting operations)
harvested_coal = harvest_resource(coal_position, min_iron_plates)
print(f"Harvested {harvested_coal} coal")

# Verify that enough coal was harvested
current_inventory = inspect_inventory()
actual_coal = current_inventory.get(Prototype.Coal, 0)
assert actual_coal >= min_iron_plates, f"Failed to harvest enough coal! Expected at least {min_iron_plates}, but got {actual_coal}"
print(f"Successfully gathered {actual_coal} coal")

# Craft a stone furnace if needed
stone_furnace = Prototype.StoneFurnace
inventory = inspect_inventory()
if inventory.get(stone_furnace, 0) == 0:
    # Find the nearest stone patch
    stone_position = nearest(Resource.Stone)
    print(f"Nearest stone found at: {stone_position}")
    
    # Move to the stone patch
    move_to(stone_position)
    print(f"Moved to stone patch at: {stone_position}")
    
    # Harvest stone (5 stone per furnace)
    harvested_stone = harvest_resource(stone_position, 5)
    print(f"Harvested {harvested_stone} stone")
    
    # Craft the stone furnace
    crafted = craft_item(stone_furnace, 1)
    print(f"Crafted {crafted} stone furnace")
    
    # Verify that the stone furnace was crafted
    inventory = inspect_inventory()
    assert inventory.get(stone_furnace, 0) >= 1, f"Failed to craft stone furnace! Expected 1, but got {inventory.get(stone_furnace, 0)}"
    print("Successfully crafted a stone furnace")

# Place the stone furnace near the player's current position
player_position = inspect_entities().player_position
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=player_position[0]+2, y=player_position[1]))
print(f"Placed stone furnace at: {furnace.position}")

# Insert coal into the stone furnace as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=min_iron_plates)
print(f"Inserted {min_iron_plates} coal into the stone furnace")

# Insert iron ore into the stone furnace
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=min_iron_plates)
print(f"Inserted {min_iron_plates} iron ore into the stone furnace")

# Wait for smelting to complete (assuming 0.7 seconds per plate)
smelting_time = int(0.7 * min_iron_plates)
sleep(smelting_time)

# Extract iron plates from the stone furnace
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=min_iron_plates)
    current_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plates >= min_iron_plates:
        break
    sleep(10)  # Allow additional time if needed

print(f"Extracted iron plates; current inventory count: {current_iron_plates}")

# Verify that enough iron plates were gathered
assert current_iron_plates >= min_iron_plates, f"Failed to gather enough iron plates! Expected at least {min_iron_plates}, but got {current_iron_plates}"
print(f"Successfully gathered {current_iron_plates} iron plates in total")

# Clean up by picking up the stone furnace
pickup_entity(stone_furnace, updated_furnace.position)
print("Picked up stone furnace")

final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

assert final_inventory.get(Prototype.IronPlate) >= 82, f"Not enough iron plates! Expected at least 82, but got {final_inventory.get(Prototype.IronPlate)}"
