
from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipe for iron chest and firearm magazine

"""
# Get the recipe for iron chest
iron_chest_recipe = get_prototype_recipe(Prototype.IronChest)

# Get the recipe for firearm magazine
firearm_magazine_recipe = get_prototype_recipe(Prototype.FirearmMagazine)

# Print the recipes
print("Iron Chest Recipe:")
print(iron_chest_recipe)

print("\nFirearm Magazine Recipe:")
print(firearm_magazine_recipe)

"""
Step 2: Gather resources. We need to gather the following resources:
- Mine 14 iron ore
- Mine 6 stone
- Mine 1-2 coal for fuel
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 14),
    (Resource.Stone, 6),
    (Resource.Coal, 2)
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

# Final check to ensure all resources are gathered
final_inventory = inspect_inventory()
for resource_type, required_quantity in resources_to_gather:
    actual_quantity = final_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Final check failed for {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"

print("Successfully gathered all required resources")

"""
Step 3: Craft and set up stone furnace. We need to craft a stone furnace and set it up for smelting.
"""
# Craft a stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Stone Furnace crafted successfully")

# Place the stone furnace
origin_position = Position(x=0, y=0)
move_to(origin_position)
furnace = place_entity(Prototype.StoneFurnace, position=origin_position)
print(f"Stone Furnace placed at {furnace.position}")

"""
Step 4: Smelt iron plates. We need to smelt 14 iron ore into 14 iron plates.
"""
# Insert coal into the furnace as fuel
insert_item(Prototype.Coal, furnace, quantity=2)
print("Coal inserted into the Stone Furnace")

# Insert iron ore into the furnace
insert_item(Prototype.IronOre, furnace, quantity=14)
print("Iron Ore inserted into the Stone Furnace")

# Wait for the smelting process to complete
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * 14)
sleep(total_smelting_time)

# Extract iron plates from the furnace
max_attempts = 5
for attempt in range(max_attempts):
    extract_item(Prototype.IronPlate, furnace.position, quantity=14)
    
    # Check if we have enough iron plates
    current_inventory = inspect_inventory()
    if current_inventory.get(Prototype.IronPlate, 0) >= 14:
        break
    
    sleep(10)  # Wait a bit more if not all plates are ready

final_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
assert final_iron_plate_count >= 14, f"Failed to obtain required number of Iron Plates. Expected: 14, Actual: {final_iron_plate_count}"
print(f"Successfully obtained {final_iron_plate_count} Iron Plates")


"""
Step 5: Craft iron chest and firearm magazine. We need to craft an iron chest and a firearm magazine.
"""
# Craft an Iron Chest
craft_item(Prototype.IronChest, quantity=1)
print("Iron Chest crafted successfully")

# Craft a Firearm Magazine
craft_item(Prototype.FirearmMagazine, quantity=1)
print("Firearm Magazine crafted successfully")

# Verify crafting success by checking inventory
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.IronChest, 0) >= 1, "Failed to craft Iron Chest"
assert final_inventory.get(Prototype.FirearmMagazine, 0) >= 1, "Failed to craft Firearm Magazine"
print("Successfully crafted all required items")


