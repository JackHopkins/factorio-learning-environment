

from factorio_instance import *

"""
Step 1: Print recipes. We need to print out the recipes for the following items:
- stone-furnace
- fast-underground-belt
"""
# Print recipes
print("Recipes:")
print("stone-furnace: 5 stone")
print("fast-underground-belt: 2 iron gear wheels, 2 underground belts (each requires 5 iron gear wheels, 10 iron plates)")


"""
Step 2: Gather resources. We need to mine the following resources:
- stone: at least 12 (5 for the stone furnace, 7 extra for safety)
- iron ore: at least 44 (40 for iron gear wheels and underground belts, 4 extra for safety)
- coal: at least 10 (for fueling the furnace and burner mining drill)
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 12),
    (Resource.IronOre, 44),
    (Resource.Coal, 10)
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
    
    # Assert that we've harvested at least as much as we needed
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.Stone, 0) >= 12, "Not enough Stone"
assert final_inventory.get(Resource.IronOre, 0) >= 44, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 10, "Not enough Coal"

print("Successfully gathered all required resources!")


"""
Step 3: Craft stone furnaces. We need to craft 2 stone furnaces.
"""
# Craft 2 stone furnaces
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=2)
print(f"Crafted {crafted_furnaces} stone furnaces")

# Verify that we have 2 stone furnaces in our inventory
inventory_after_crafting = inspect_inventory()
stone_furnaces_in_inventory = inventory_after_crafting.get(Prototype.StoneFurnace, 0)
assert stone_furnaces_in_inventory >= 2, f"Failed to craft enough stone furnaces. Expected: 2, Actual: {stone_furnaces_in_inventory}"
print(f"Successfully crafted {stone_furnaces_in_inventory} stone furnaces")




"""
Step 4: Place and fuel furnace. We need to:
- Place a stone furnace
- Fuel it with coal (use 5 coal for safety)
"""
# Place the stone furnace at the origin
furnace_position = Position(x=0, y=0)
move_to(furnace_position)
furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)
print(f"Placed stone furnace at {furnace_position}")

# Insert coal into the furnace
coal_to_insert = 5
updated_furnace = insert_item(Prototype.Coal, target=furnace, quantity=coal_to_insert)
print(f"Inserted {coal_to_insert} coal into the stone furnace")

# Verify that the furnace has coal in its fuel inventory
coal_in_furnace = updated_furnace.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace > 0, "Failed to fuel the furnace"
print("Stone furnace is successfully fueled and ready for smelting")


"""
Step 5: Smelt iron plates. We need to:
- Smelt 44 iron ore into iron plates (use 44 iron ore)
"""
# Insert all available Iron Ore into the Furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
updated_furnace = insert_item(Prototype.IronOre, target=updated_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} Iron Ore into the Stone Furnace")

# Calculate expected number of Iron Plates after smelting
initial_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
expected_iron_plates = initial_iron_plates + iron_ore_in_inventory

# Wait for smelting to complete
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_in_inventory)
sleep(total_smelting_time)

# Extract Iron Plates from Furnace
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, iron_ore_in_inventory)
    current_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plates >= expected_iron_plates:
        break
    sleep(10)  # Allow additional time if needed

print(f"Extracted Iron Plates; Current Inventory Count: {current_iron_plates}")

# Final assertion check
assert current_iron_plates >= expected_iron_plates, f"Failed to obtain required number of Iron Plates. Expected: {expected_iron_plates}, Actual: {current_iron_plates}"
print("Successfully obtained required number of Iron Plates!")


"""
Step 6: Craft iron gear wheels. We need to craft 40 iron gear wheels.
"""
# Craft 40 iron gear wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=40)
print(f"Crafted {crafted_gear_wheels} iron gear wheels")

# Verify that we have 40 iron gear wheels in our inventory
inventory_after_crafting = inspect_inventory()
gear_wheels_in_inventory = inventory_after_crafting.get(Prototype.IronGearWheel, 0)
assert gear_wheels_in_inventory >= 40, f"Failed to craft enough iron gear wheels. Expected: 40, Actual: {gear_wheels_in_inventory}"
print(f"Successfully crafted {gear_wheels_in_inventory} iron gear wheels")


"""
Step 7: Craft underground belts. We need to craft 2 underground belts.
"""
# Craft 2 underground belts
crafted_underground_belts = craft_item(Prototype.UndergroundBelt, quantity=2)
print(f"Crafted {crafted_underground_belts} underground belts")

# Verify that we have 2 underground belts in our inventory
inventory_after_crafting = inspect_inventory()
underground_belts_in_inventory = inventory_after_crafting.get(Prototype.UndergroundBelt, 0)
assert underground_belts_in_inventory >= 2, f"Failed to craft enough underground belts. Expected: 2, Actual: {underground_belts_in_inventory}"
print(f"Successfully crafted {underground_belts_in_inventory} underground belts")


"""
Step 8: Craft fast-underground-belt. We need to craft 1 fast-underground-belt.
"""
# Craft 1 fast-underground-belt
crafted_fast_underground_belts = craft_item(Prototype.FastUndergroundBelt, quantity=1)
print(f"Crafted {crafted_fast_underground_belts} fast-underground-belt")

# Verify that we have 1 fast-underground-belt in our inventory
inventory_after_crafting = inspect_inventory()
fast_underground_belts_in_inventory = inventory_after_crafting.get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belts_in_inventory >= 1, f"Failed to craft enough fast-underground-belt. Expected: 1, Actual: {fast_underground_belts_in_inventory}"
print(f"Successfully crafted {fast_underground_belts_in_inventory} fast-underground-belt")


"""
Step 9: Verify objective completion. We need to check if we have successfully crafted a fast-underground-belt.
"""
# Check if we have 1 fast-underground-belt in our inventory
final_inventory = inspect_inventory()
fast_underground_belts_in_final_inventory = final_inventory.get(Prototype.FastUndergroundBelt, 0)

assert fast_underground_belts_in_final_inventory >= 1, f"Objective not completed. Expected at least 1 fast-underground-belt, but found {fast_underground_belts_in_final_inventory}"
print("Objective completed: Successfully crafted at least 1 fast-underground-belt")

