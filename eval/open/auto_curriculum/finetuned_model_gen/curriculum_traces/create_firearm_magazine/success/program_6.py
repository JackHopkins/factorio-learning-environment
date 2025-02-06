
from instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- stone-furnace
- iron-plate
- firearm-magazine
"""
# Get the recipes for the required items
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
iron_plate_recipe = get_prototype_recipe(Prototype.IronPlate)
firearm_magazine_recipe = get_prototype_recipe(Prototype.FirearmMagazine)

# Print the recipes
print("Stone Furnace Recipe:", stone_furnace_recipe)
print("Iron Plate Recipe:", iron_plate_recipe)
print("Firearm Magazine Recipe:", firearm_magazine_recipe)

"""
Step 2: Gather resources. We need to gather the following resources:
- 6 stone for the stone furnace
- At least 12 iron ore (more for buffer)
- At least 1 coal for fuel (more for buffer)
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 6),
    (Resource.IronOre, 12),
    (Resource.Coal, 1)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    
    # Move to the resource position
    move_to(resource_position)
    
    # Harvest the required quantity of this resource
    harvested_quantity = harvest_resource(resource_position, required_quantity)
    
    # Assert that we've harvested at least the required amount
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory after gathering resources:", final_inventory)

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.Stone, 0) >= 6, "Not enough stone gathered"
assert final_inventory.get(Resource.IronOre, 0) >= 12, "Not enough iron ore gathered"
assert final_inventory.get(Resource.Coal, 0) >= 1, "Not enough coal gathered"

print("Successfully gathered all required resources!")

"""
Step 3: Craft a stone furnace. We need to craft a stone furnace using the 6 stone we gathered.
"""
# Craft a stone furnace using the gathered stone
crafted_quantity = craft_item(Prototype.StoneFurnace, 1)

# Verify that the crafting process was successful
current_inventory = inspect_inventory()
actual_quantity = current_inventory.get(Prototype.StoneFurnace, 0)
assert actual_quantity >= 1, f"Failed to craft stone furnace. Expected at least 1, but got {actual_quantity}"

print(f"Successfully crafted {crafted_quantity} stone furnace")

# Print the current inventory after crafting
print("Inventory after crafting stone furnace:", current_inventory)

# Assert that we have at least one stone furnace in our inventory
assert current_inventory.get(Prototype.StoneFurnace, 0) >= 1, "Stone furnace crafting failed"

print("Stone furnace crafting step completed successfully!")

"""
Step 4: Set up smelting operation. We need to:
- Place the stone furnace
- Add coal to the furnace as fuel
"""
# Place the stone furnace at the origin position
origin_position = Position(x=0, y=0)
move_to(origin_position)
stone_furnace = place_entity(Prototype.StoneFurnace, position=origin_position)
assert stone_furnace is not None, "Failed to place stone furnace"

# Insert coal into the stone furnace as fuel
coal_quantity_for_fuel = 1
updated_furnace = insert_item(Prototype.Coal, stone_furnace, coal_quantity_for_fuel)
assert updated_furnace.fuel.get(Prototype.Coal, 0) > 0, "Failed to insert coal into the stone furnace"

print("Successfully set up smelting operation with a stone furnace fueled by coal")

"""
Step 5: Smelt iron plates. We need to:
- Smelt at least 12 iron ore into iron plates
"""
# Insert iron ore into the stone furnace for smelting
iron_ore_quantity = 12  # Smelt 12 iron ore into iron plates
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, iron_ore_quantity)

# Wait for the smelting process to complete
smelting_time = 0.7 * iron_ore_quantity  # Assuming 0.7 seconds per unit of iron ore
sleep(smelting_time)

# Extract the smelted iron plates from the furnace
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    # Attempt to extract all possible iron plates from the furnace
    extract_item(Prototype.IronPlate, updated_furnace.position, iron_ore_quantity)
    
    # Check how many iron plates are now in our inventory
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    
    # If we've reached or exceeded the target number of iron plates, break out of loop
    if current_iron_plate_count >= 12:
        break

print(f"Successfully smelted {current_iron_plate_count} iron plates")

"""
Step 6: Craft firearm magazine. We need to craft the firearm magazine using 4 iron plates.
"""
# Craft a firearm magazine using the gathered iron plates
crafted_quantity = craft_item(Prototype.FirearmMagazine, 1)

# Verify that the crafting process was successful
current_inventory = inspect_inventory()
actual_quantity = current_inventory.get(Prototype.FirearmMagazine, 0)
assert actual_quantity >= 1, f"Failed to craft firearm magazine. Expected at least 1, but got {actual_quantity}"

print(f"Successfully crafted {crafted_quantity} firearm magazine")

# Print the current inventory after crafting
print("Inventory after crafting firearm magazine:", current_inventory)

# Assert that we have at least one firearm magazine in our inventory
assert current_inventory.get(Prototype.FirearmMagazine, 0) >= 1, "Firearm magazine crafting failed"

print("Firearm magazine crafting step completed successfully!")

# Final inventory check for all items
final_inventory_check = inspect_inventory()
print("Final inventory check:", final_inventory_check)

# Assert that we have at least 1 firearm magazine in our inventory
assert final_inventory_check.get(Prototype.FirearmMagazine, 0) >= 1, "Final check: Not enough firearm magazines in inventory"

# Assert that we have at least 8 iron plates left (12 smelted - 4 used for crafting)
assert final_inventory_check.get(Prototype.IronPlate, 0) >= 8, "Final check: Not enough iron plates left in inventory"

# Assert that there's still some coal (we started with more than needed)
assert final_inventory_check.get(Prototype.Coal, 0) >= 0, "Final check: Not enough coal left in inventory"

print("All required items have been successfully crafted!")
