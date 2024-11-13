

from factorio_instance import *


"""
Step 1: Print recipes. We need to print the recipes for the items we need to craft.
"""
# Print the recipe for stone-brick
print("Stone-brick recipe:")
print("Crafting requires smelting 2 stone to make one stone brick")

# Print the recipe for steel-plate
print("Steel-plate recipe:")
print("Crafting requires smelting 5 iron plates, smelts for 4 seconds per ore")

# Print the recipe for iron-plate
print("Iron-plate recipe:")
print("Crafting requires smelting 1 iron ore, smelts for 0.5 seconds per ore")


"""
Step 2: Gather raw resources. We need to gather the following resources:
- Mine 2 stone
- Mine 1 coal
- Use the 6 iron ore from the inventory
"""
# Define the resources we need to gather
resources_to_gather = [(Resource.Stone, 2), (Resource.Coal, 1)]

# Loop over each resource we need to gather
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    print(f"Nearest {resource_type} found at: {resource_position}")
    
    # Move to the resource
    move_to(resource_position)
    print(f"Moved to {resource_type} position: {resource_position}")
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    print(f"Harvested {harvested} {resource_type}")
    
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

print("Successfully gathered all required resources")
print("Final inventory quantities:")
print(f"Stone: {inspect_inventory().get(Resource.Stone, 0)}")
print(f"Coal: {inspect_inventory().get(Resource.Coal, 0)}")
print(f"Iron Ore (from initial inventory): {inspect_inventory().get(Resource.IronOre, 6)}")


"""
Step 3: Prepare the furnace. We need to prepare the furnace by adding coal as fuel.
"""
# Find the existing stone furnace
furnace = get_entities({Prototype.StoneFurnace})[0]
print(f"Found stone furnace at: {furnace.position}")

# Move to the furnace
move_to(furnace.position)
print(f"Moved to furnace position: {furnace.position}")

# Insert the coal into the furnace
# Note: We're using the coal from the stone_furnace object, not from the inventory directly.
#       The stone_furnace object has a 'fuel' attribute that contains the coal.
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=1)
print("Inserted 1 coal into the furnace")

# Inspect the furnace's fuel to verify that coal was added
coal_in_furnace = updated_furnace.fuel.get('coal', 0)
print(f"Coal in furnace after insertion: {coal_in_furnace}")
assert coal_in_furnace >= 1, "Failed to insert coal into the furnace"

# Verify that the furnace is now ready to smelt
furnace_status = updated_furnace.status
assert furnace_status != EntityStatus.NO_FUEL, "Furnace still has no fuel"
print("Furnace is now fueled and ready to smelt")


"""
Step 4: Smelt iron plates. We need to smelt the 6 iron ore into iron plates.
"""
# Insert iron ore into the furnace
# Note: We're using the iron ore from the inventory directly.
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
print(f"Iron ore in inventory before insertion: {iron_ore_in_inventory}")
assert iron_ore_in_inventory >= 6, f"Not enough iron ore in inventory. Expected at least 6, but found {iron_ore_in_inventory}"

# Insert all available iron ore into the furnace
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} iron ore into the furnace")

# Wait for the smelting process to complete
smelting_time_per_unit = 0.7  # seconds
total_smelting_time = int(smelting_time_per_unit * iron_ore_in_inventory)
sleep(total_smelting_time)

# Try extracting multiple times as the smelting might take a bit longer
max_attempts_to_extract = 5
for attempt in range(max_attempts_to_extract):
    # Attempt to extract iron plates
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    
    # Check how many iron plates are now in inventory
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    
    # Check if we have the desired number of iron plates
    if current_iron_plate_count >= 6:
        break
    
    sleep(5)  # Allowing additional time for any remaining smelting

print(f"Extracted Iron Plates; Current Inventory: {inspect_inventory()}")
assert current_iron_plate_count >= 6, f"Failed to obtain required number of Iron Plates; Expected: At least 6, Found: {current_iron_plate_count}"
print("Successfully obtained required number of Iron Plates!")


"""
Step 5: Craft steel plate. We need to craft 1 steel plate using the 5 iron plates.
"""
# Insert iron plates into the furnace for smelting
iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
print(f"Iron plates in inventory before insertion: {iron_plates_in_inventory}")
assert iron_plates_in_inventory >= 5, f"Not enough iron plates in inventory. Expected at least 5, but found {iron_plates_in_inventory}"

# Insert all available iron plates into the furnace
updated_furnace = insert_item(Prototype.IronPlate, updated_furnace, quantity=5)
print("Inserted 5 iron plates into the furnace")

# Wait for the smelting process to complete
smelting_time_per_unit = 4  # seconds for steel plate
total_smelting_time = int(smelting_time_per_unit * 1)  # Only crafting one steel plate
sleep(total_smelting_time)

# Try extracting multiple times as the smelting might take a bit longer
max_attempts_to_extract = 5
for attempt in range(max_attempts_to_extract):
    # Attempt to extract steel plate
    extract_item(Prototype.SteelPlate, updated_furnace.position, quantity=1)
    
    # Check how many steel plates are now in inventory
    current_steel_plate_count = inspect_inventory().get(Prototype.SteelPlate, 0)
    
    # Check if we have the desired number of steel plates
    if current_steel_plate_count >= 1:
        break
    
    sleep(5)  # Allowing additional time for any remaining smelting

print(f"Extracted Steel Plate; Current Inventory: {inspect_inventory()}")
assert current_steel_plate_count >= 1, f"Failed to obtain required number of Steel Plates; Expected: At least 1, Found: {current_steel_plate_count}"
print("Successfully obtained required number of Steel Plates!")


"""
Step 6: Smelt stone bricks. We need to smelt 2 stone to create 1 stone brick.
"""
# Insert stone into the furnace for smelting
stone_in_inventory = inspect_inventory().get(Prototype.Stone, 0)
print(f"Stone in inventory before insertion: {stone_in_inventory}")
assert stone_in_inventory >= 2, f"Not enough stone in inventory. Expected at least 2, but found {stone_in_inventory}"

# Insert all available stones into the furnace
updated_furnace = insert_item(Prototype.Stone, updated_furnace, quantity=2)
print("Inserted 2 stones into the furnace")

# Wait for the smelting process to complete
smelting_time_per_unit = 0.7  # seconds
total_smelting_time = int(smelting_time_per_unit * 2)
sleep(total_smelting_time)

# Try extracting multiple times as the smelting might take a bit longer
max_attempts_to_extract = 5
for attempt in range(max_attempts_to_extract):
    # Attempt to extract stone bricks
    extract_item(Prototype.StoneBrick, updated_furnace.position, quantity=1)
    
    # Check how many stone bricks are now in inventory
    current_stone_brick_count = inspect_inventory().get(Prototype.StoneBrick, 0)
    
    # Check if we have the desired number of stone bricks
    if current_stone_brick_count >= 1:
        break
    
    sleep(5)  # Allowing additional time for any remaining smelting

print(f"Extracted Stone Bricks; Current Inventory: {inspect_inventory()}")
assert current_stone_brick_count >= 1, f"Failed to obtain required number of Stone Bricks; Expected: At least 1, Found: {current_stone_brick_count}"
print("Successfully obtained required number of Stone Bricks!")


"""
Step 7: Verify the results. We need to verify that we have the correct items in our inventory:
- Check if we have 1 stone brick
- Check if we have 1 steel plate
"""
# Check if we have 1 stone brick
stone_brick_count = inspect_inventory().get(Prototype.StoneBrick, 0)
assert stone_brick_count >= 1, f"Expected at least 1 stone brick in inventory, but found {stone_brick_count}"
print(f"Stone Brick Count: {stone_brick_count}")

# Check if we have 1 steel plate
steel_plate_count = inspect_inventory().get(Prototype.SteelPlate, 0)
assert steel_plate_count >= 1, f"Expected at least 1 steel plate in inventory, but found {steel_plate_count}"
print(f"Steel Plate Count: {steel_plate_count}")

print("Successfully verified the presence of required items in the inventory!")

