
from instance import *

"""
Step 1: Print recipes. We need to print the recipe for fast-transport-belt
"""
# Get the recipe for fast-transport-belt
recipe = get_prototype_recipe(Prototype.FastTransportBelt)

# Print the recipe details
print("fast-transport-belt Recipe:")
print(f"Ingredients: {recipe.ingredients}")
print(f"Products: {recipe.products}")
print(f"Energy: {recipe.energy}")
print(f"Category: {recipe.category}")
print(f"Enabled: {recipe.enabled}")

"""
Step 2: Gather resources. We need to mine the following resources:
- stone (at least 12)
- coal (at least 2)
- iron ore (at least 31)
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 12),
    (Resource.Coal, 2),
    (Resource.IronOre, 31)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    
    # Move to the resource location
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} of {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")

# Assert that we have gathered at least the required quantities
assert final_inventory.get(Resource.Stone, 0) >= 12, "Not enough Stone"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Not enough Coal"
assert final_inventory.get(Resource.IronOre, 0) >= 31, "Not enough Iron Ore"

print("Successfully gathered all required resources.")

"""
Step 3: Craft stone furnaces. We need to craft 2 stone furnaces.
"""
# Check current inventory for stone
stone_in_inventory = inspect_inventory().get(Resource.Stone, 0)
assert stone_in_inventory >= 10, f"Insufficient stone in inventory. Expected at least 10, found {stone_in_inventory}"

# Craft two stone furnaces
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=2)
assert crafted_furnaces == 2, f"Failed to craft 2 Stone Furnaces. Only crafted {crafted_furnaces}"

# Verify that the stone furnaces are in our inventory
stone_furnaces_in_inventory = inspect_inventory().get(Prototype.StoneFurnace, 0)
assert stone_furnaces_in_inventory >= 2, f"Inventory verification failed for Stone Furnaces. Expected at least 2, found {stone_furnaces_in_inventory}"

print("Successfully crafted 2 Stone Furnaces.")

"""
Step 4: Place and use stone furnace.
- Place a stone furnace
- Add coal to the furnace as fuel
- Smelt 31 iron ore into iron plates
"""
# Move to an appropriate location to place the stone furnace
furnace_position = Position(x=0, y=0)
move_to(furnace_position)

# Place the stone furnace
furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)
assert furnace is not None, "Failed to place Stone Furnace"

# Insert coal into the furnace as fuel
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
assert coal_in_inventory >= 2, f"Insufficient coal in inventory. Expected at least 2, found {coal_in_inventory}"
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=2)
assert updated_furnace.fuel.get(Prototype.Coal, 0) >= 2, f"Failed to insert coal into furnace. Furnace contains: {updated_furnace.fuel}"

# Insert iron ore into the furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
assert iron_ore_in_inventory >= 31, f"Insufficient iron ore in inventory. Expected at least 31, found {iron_ore_in_inventory}"
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=31)
assert updated_furnace.furnace_source.get(Prototype.IronOre, 0) >= 31, f"Failed to insert iron ore into furnace. Furnace contains: {updated_furnace.furnace_source}"

# Wait for smelting to complete
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * 31)
sleep(total_smelting_time)

# Extract iron plates from the furnace
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=31)
    iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
    if iron_plates_in_inventory >= 31:
        break
    sleep(10)

assert iron_plates_in_inventory >= 31, f"Failed to obtain required number of Iron Plates. Expected: 31, Found: {iron_plates_in_inventory}"
print(f"Successfully smelted {iron_plates_in_inventory} Iron Plates")

"""
Step 5: Craft iron gear wheels. We need to craft 8 iron gear wheels.
"""
# Check current inventory for iron plates
iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
assert iron_plates_in_inventory >= 16, f"Insufficient Iron Plates in inventory. Expected at least 16, found {iron_plates_in_inventory}"

# Craft 8 Iron Gear Wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=8)
assert crafted_gear_wheels == 8, f"Failed to craft 8 Iron Gear Wheels. Only crafted {crafted_gear_wheels}"

# Verify that the Iron Gear Wheels are in our inventory
gear_wheels_in_inventory = inspect_inventory().get(Prototype.IronGearWheel, 0)
assert gear_wheels_in_inventory >= 8, f"Inventory verification failed for Iron Gear Wheels. Expected at least 8, found {gear_wheels_in_inventory}"

print("Successfully crafted 8 Iron Gear Wheels.")

"""
Step 6: Craft burner mining drill. We need to craft 1 burner mining drill.
- Craft 1 stone furnace
- Craft 3 iron gear wheels
- Craft 1 burner mining drill
"""
# Check current inventory for required materials
stone_furnaces_in_inventory = inspect_inventory().get(Prototype.StoneFurnace, 0)
iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
gear_wheels_in_inventory = inspect_inventory().get(Prototype.IronGearWheel, 0)

# Ensure we have at least one Stone Furnace
if stone_furnaces_in_inventory < 1:
    # Craft a Stone Furnace
    crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
    assert crafted_furnaces == 1, f"Failed to craft Stone Furnace. Only crafted {crafted_furnaces}"

# Ensure we have at least three Iron Gear Wheels
if gear_wheels_in_inventory < 3:
    # Craft Iron Gear Wheels
    crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=3)
    assert crafted_gear_wheels == 3, f"Failed to craft Iron Gear Wheels. Only crafted {crafted_gear_wheels}"

# Now attempt to craft the Burner Mining Drill
crafted_drills = craft_item(Prototype.BurnerMiningDrill, quantity=1)
assert crafted_drills == 1, f"Failed to craft Burner Mining Drill. Only crafted {crafted_drills}"

# Verify that the Burner Mining Drill is in our inventory
drills_in_inventory = inspect_inventory().get(Prototype.BurnerMiningDrill, 0)
assert drills_in_inventory >= 1, f"Inventory verification failed for Burner Mining Drill. Expected at least 1, found {drills_in_inventory}"

print("Successfully crafted 1 Burner Mining Drill.")

"""
Step 7: Craft transport belt. We need to craft 1 transport belt.
- Craft 1 iron gear wheel
- Craft 1 transport belt (this will give us 2)
"""
# Check current inventory for Iron Plates
iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
assert iron_plates_in_inventory >= 2, f"Insufficient Iron Plates in inventory. Expected at least 2, found {iron_plates_in_inventory}"

# Craft 1 Iron Gear Wheel
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=1)
assert crafted_gear_wheels == 1, f"Failed to craft 1 Iron Gear Wheel. Only crafted {crafted_gear_wheels}"

# Verify that the Iron Gear Wheel is in our inventory
gear_wheels_in_inventory = inspect_inventory().get(Prototype.IronGearWheel, 0)
assert gear_wheels_in_inventory >= 1, f"Inventory verification failed for Iron Gear Wheel. Expected at least 1, found {gear_wheels_in_inventory}"

# Craft 1 Transport Belt (which gives us 2)
crafted_transport_belts = craft_item(Prototype.TransportBelt, quantity=1)
assert crafted_transport_belts == 1, f"Failed to craft 1 Transport Belt (2 units). Only crafted {crafted_transport_belts}"

# Verify that there are now 2 Transport Belts in our inventory
transport_belts_in_inventory = inspect_inventory().get(Prototype.TransportBelt, 0)
assert transport_belts_in_inventory >= 2, f"Inventory verification failed for Transport Belts. Expected at least 2, found {transport_belts_in_inventory}"

print("Successfully crafted 1 Transport Belt (2 units).")

"""
Step 8: Craft fast-transport-belt. We need to craft 1 fast-transport-belt.
"""
# Check current inventory for required materials
gear_wheels_in_inventory = inspect_inventory().get(Prototype.IronGearWheel, 0)
transport_belts_in_inventory = inspect_inventory().get(Prototype.TransportBelt, 0)

# Ensure we have at least one Iron Gear Wheel
if gear_wheels_in_inventory < 1:
    # Check if there are enough Iron Plates to craft another Gear Wheel
    iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
    if iron_plates_in_inventory >= 2:
        # Craft an additional Iron Gear Wheel
        crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=1)
        assert crafted_gear_wheels == 1, f"Failed to craft additional Iron Gear Wheel. Only crafted {crafted_gear_wheels}"
    else:
        raise Exception("Insufficient resources to craft required Iron Gear Wheel")

# Ensure we have at least one Transport Belt
if transport_belts_in_inventory < 1:
    # Check if there are enough resources to craft another Transport Belt
    if gear_wheels_in_inventory >= 1 and iron_plates_in_inventory >= 1:
        # Craft an additional Transport Belt
        crafted_transport_belts = craft_item(Prototype.TransportBelt, quantity=1)
        assert crafted_transport_belts == 1, f"Failed to craft additional Transport Belt. Only crafted {crafted_transport_belts}"
    else:
        raise Exception("Insufficient resources to craft required Transport Belt")

# Now attempt to craft the Fast Transport Belt
crafted_fast_transport_belts = craft_item(Prototype.FastTransportBelt, quantity=1)
assert crafted_fast_transport_belts == 1, f"Failed to craft Fast Transport Belt. Only crafted {crafted_fast_transport_belts}"

# Verify that the Fast Transport Belt is in our inventory
fast_transport_belts_in_inventory = inspect_inventory().get(Prototype.FastTransportBelt, 0)
assert fast_transport_belts_in_inventory >= 1, f"Inventory verification failed for Fast Transport Belt. Expected at least 1, found {fast_transport_belts_in_inventory}"

print("Successfully crafted 1 Fast Transport Belt.")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Fast Transport Belt: {final_inventory.get(Prototype.FastTransportBelt, 0)}")
print(f"Burner Mining Drill: {final_inventory.get(Prototype.BurnerMiningDrill, 0)}")
print(f"Stone Furnace: {final_inventory.get(Prototype.StoneFurnace, 0)}")
