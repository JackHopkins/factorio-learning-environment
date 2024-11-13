

from factorio_instance import *

"""
Craft an iron chest from scratch

:param game:
:return:
"""

"""
Planning:
We need to create an iron chest. There are no iron chests on the map or in our inventory, so we need to craft one from scratch.
To do this, we need to gather the necessary resources and craft the required items.

Steps:
1. Gather resources:
   - Mine at least 6 stone
   - Mine at least 1 coal for fuel
   - Mine at least 14 iron ore
2. Craft a stone furnace
3. Craft a burner mining drill
4. Set up the burner mining drill to mine iron
5. Smelt iron ore into iron plates
6. Craft the iron chest
"""

"""
Step 1: Gather resources
- Mine at least 6 stone
- Mine at least 1 coal for fuel
- Mine at least 14 iron ore
"""

# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 6),
    (Resource.Coal, 1),
    (Resource.IronOre, 14)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    
    # Move to the resource
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

print("Successfully gathered all required resources!")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:", final_inventory)

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.Stone, 0) >= 6, "Not enough Stone"
assert final_inventory.get(Resource.Coal, 0) >= 1, "Not enough Coal"
assert final_inventory.get(Resource.IronOre, 0) >= 14, "Not enough Iron Ore"

print("All required resources have been successfully gathered!")

"""
Step 2: Craft a stone furnace
"""

# Craft a stone furnace
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted {crafted_furnaces} stone furnaces")

# Verify crafting success
assert crafted_furnaces == 1, "Failed to craft stone furnace"
print("Successfully crafted a stone furnace")

# Check current inventory for stone
current_stone_inventory = inspect_inventory().get(Resource.Stone, 0)
print(f"Remaining stone in inventory: {current_stone_inventory}")

# Check that we still have at least one stone left
assert current_stone_inventory >= 1, "Not enough remaining stone"

"""
Step 3: Craft a burner mining drill
"""

# Get the recipe for burner mining drill
bmd_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
print("Burner Mining Drill Recipe:")
print(f"Ingredients: {bmd_recipe.ingredients}")

# Craft a burner mining drill
crafted_drills = craft_item(Prototype.BurnerMiningDrill, quantity=1)
print(f"Crafted {crafted_drills} burner mining drills")

# Verify crafting success
assert crafted_drills == 1, "Failed to craft burner mining drill"
print("Successfully crafted a burner mining drill")

# Check current inventory for required items
current_iron_plate_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
current_iron_gear_wheel_inventory = inspect_inventory().get(Prototype.IronGearWheel, 0)
current_stone_furnace_inventory = inspect_inventory().get(Prototype.StoneFurnace, 0)

print(f"Remaining iron plates in inventory: {current_iron_plate_inventory}")
print(f"Remaining iron gear wheels in inventory: {current_iron_gear_wheel_inventory}")
print(f"Remaining stone furnaces in inventory: {current_stone_furnace_inventory}")

"""
Step 4: Set up the burner mining drill to mine iron
"""

# Find the nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)

# Move to the iron ore patch
move_to(iron_ore_position)

# Place the burner mining drill
drill = place_entity(Prototype.BurnerMiningDrill, position=iron_ore_position)
print(f"Placed burner mining drill at {drill.position}")

# Insert coal into the burner mining drill as fuel
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
assert coal_in_inventory >= 1, f"Insufficient coal in inventory. Expected at least 1 but found {coal_in_inventory}"

# Insert all available coal (should be at least 1) into the drill
updated_drill = insert_item(Prototype.Coal, drill, quantity=coal_in_inventory)
print(f"Inserted {coal_in_inventory} coal into the burner mining drill")

# Verify that the drill now has fuel
coal_in_drill = updated_drill.fuel.get(Prototype.Coal, 0)
assert coal_in_drill > 0, "Failed to fuel burner mining drill"

print("Burner mining drill successfully set up and fueled")

"""
Step 5: Smelt iron ore into iron plates
"""

# Move to the existing stone furnace
furnace_position = Position(x=0.0, y=0.0)
move_to(furnace_position)

# Get the stone furnace entity
stone_furnace = get_entity(Prototype.StoneFurnace, position=furnace_position)

# Insert coal into the stone furnace as fuel
updated_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=1)
print("Inserted 1 coal into the stone furnace")

# Check if there are any existing contents in the furnace and extract them
existing_contents = updated_furnace.furnace_result.get(Prototype.IronPlate, 0)
if existing_contents > 0:
    extract_item(Prototype.IronPlate, updated_furnace.position, existing_contents)
    print(f"Extracted {existing_contents} existing iron plates from the furnace")

# Insert all available iron ore into the furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
assert iron_ore_in_inventory >= 14, f"Insufficient iron ore in inventory. Expected at least 14 but found {iron_ore_in_inventory}"

updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} iron ore into the stone furnace")

# Wait for smelting to complete
smelting_time = 0.7 * iron_ore_in_inventory  # Assuming a smelting time of 0.7 seconds per iron ore
sleep(smelting_time)

# Extract the smelted iron plates
expected_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0) + iron_ore_in_inventory
extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)

# Verify that we have extracted the expected number of iron plates
actual_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
assert actual_iron_plates >= expected_iron_plates, f"Failed to obtain enough iron plates. Expected: {expected_iron_plates}, Actual: {actual_iron_plates}"

print(f"Successfully obtained {actual_iron_plates} iron plates")


"""
Step 6: Craft the iron chest
"""

# Craft the iron chest
crafted_chests = craft_item(Prototype.IronChest, quantity=1)
print(f"Crafted {crafted_chests} iron chests")

# Verify crafting success
assert crafted_chests == 1, "Failed to craft iron chest"
print("Successfully crafted an iron chest")

# Check current inventory for iron plates
current_iron_plate_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
print(f"Remaining iron plates in inventory: {current_iron_plate_inventory}")

# Assert that we have enough iron plates left
assert current_iron_plate_inventory >= 4, "Not enough remaining iron plates"

print("Iron chest crafting completed successfully!")


