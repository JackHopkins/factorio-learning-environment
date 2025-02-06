
from instance import *


"""
Step 1: Print recipes. We need to print the recipe for firearm-magazine, as we need to craft it from scratch
"""
# Get the recipe for firearm-magazine
recipe = get_prototype_recipe(Prototype.FirearmMagazine)

# Print the recipe
print("FirearmMagazine Recipe:")
print(f"Ingredients: {recipe.ingredients}")

"""
Step 1: Craft the firearm-magazine
- Craft firearm-magazine using 4 iron plates
"""
# Craft the firearm-magazine using 4 iron plates
craft_item(Prototype.FirearmMagazine, quantity=1)

# Check if we have the firearm-magazine in our inventory
inventory = inspect_inventory()
firearm_magazine_count = inventory.get(Prototype.FirearmMagazine, 0)
assert firearm_magazine_count >= 1, f"Failed to craft firearm-magazine. Expected at least 1, but got {firearm_magazine_count}"
print(f"Successfully crafted {firearm_magazine_count} firearm-magazine(s)")

"""
Step 2: Craft the stone furnace
- Mine 5 stone
- Craft 1 stone furnace
"""
# Define the amount of stone needed for one stone furnace
STONE_FOR_FURNACE = 5

# Find the nearest stone resource and move to it
stone_position = nearest(Resource.Stone)
move_to(stone_position)

# Mine the stone
harvested_stone = harvest_resource(stone_position, quantity=STONE_FOR_FURNACE)
print(f"Harvested {harvested_stone} stone")

# Check if we have enough stone
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.Stone, 0) >= STONE_FOR_FURNACE, "Not enough stone to craft a furnace"

# Craft the stone furnace
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted {crafted_furnaces} stone furnace(s)")

# Verify that we have at least one stone furnace in our inventory
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.StoneFurnace, 0) >= 1, "Failed to craft a stone furnace"
print(f"Successfully crafted a stone furnace; Current inventory: {final_inventory}")

"""
Step 3: Gather and process resources
- Mine 4 iron ore
- Mine 1 coal
- Place stone furnace
- Add coal to furnace
- Smelt iron ore into 4 iron plates
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 4),
    (Resource.Coal, 1)
]

# Gather each resource
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest resource patch
    resource_position = nearest(resource_type)
    # Move to the resource
    move_to(resource_position)
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    assert current_inventory.get(resource_type, 0) >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {current_inventory.get(resource_type, 0)}"
    print(f"Successfully gathered {required_quantity} {resource_type}")

# Log the inventory after gathering resources
print(f"Inventory after gathering resources: {inspect_inventory()}")

# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print("Placed stone furnace")

# Insert coal into the furnace as fuel
coal_quantity = inspect_inventory().get(Prototype.Coal, 0)
assert coal_quantity > 0, "No coal available in inventory"
updated_furnace = insert_item(Prototype.Coal, furnace, coal_quantity)
print("Inserted coal into the stone furnace")

# Insert iron ore into the furnace
iron_ore_quantity = inspect_inventory().get(Prototype.IronOre, 0)
assert iron_ore_quantity >= 4, f"Not enough Iron Ore; Expected: 4, Found: {iron_ore_quantity}"
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, iron_ore_quantity)
print("Inserted Iron Ore into the Stone Furnace")

# Wait for smelting to complete
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_quantity)
sleep(total_smelting_time)

# Extract iron plates from the furnace
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, iron_ore_quantity)
    if inspect_inventory().get(Prototype.IronPlate, 0) >= 4:
        break
    sleep(10)
print("Extracted Iron Plates from the Stone Furnace")

# Final verification that we have enough Iron Plates
final_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
assert final_iron_plate_count >= 4, f"Failed to obtain required number of Iron Plates; Expected: 4, Found: {final_iron_plate_count}"
print(f"Successfully obtained {final_iron_plate_count} Iron Plates")

# Log final inventory state
final_inventory_state = inspect_inventory()
print(f"Final Inventory State: {final_inventory_state}")

print("Successfully completed gathering and processing resources step")

"""
Step 4: Craft the firearm-magazine
- Craft firearm-magazine using 4 iron plates
"""
# Craft the firearm-magazine using 4 iron plates
craft_item(Prototype.FirearmMagazine, quantity=1)

# Check if we have the firearm-magazine in our inventory
inventory = inspect_inventory()
firearm_magazine_count = inventory.get(Prototype.FirearmMagazine, 0)
assert firearm_magazine_count >= 1, f"Failed to craft firearm-magazine. Expected at least 1, but got {firearm_magazine_count}"
print(f"Successfully crafted {firearm_magazine_count} firearm-magazine(s)")

# Print the final inventory
final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

# Assert that we have at least one firearm-magazine in the final inventory
assert final_inventory.get(Prototype.FirearmMagazine, 0) >= 1, "Final inventory check failed: No firearm-magazine found"
print("Objective completed successfully: Crafted firearm-magazine")

