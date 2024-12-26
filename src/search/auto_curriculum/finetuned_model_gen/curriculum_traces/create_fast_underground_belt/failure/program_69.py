

from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipes for the items we need to craft. 
"""
recipes_to_print = [Prototype.FastUndergroundBelt, Prototype.UndergroundBelt, Prototype.IronGearWheel]
# Print the recipes
for recipe in recipes_to_print:
    print(f"Recipe for {recipe}: {get_prototype_recipe(recipe)}")


"""
Step 1: Gather resources. We need to mine iron ore, coal, and stone. 
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 88),
    (Resource.Coal, 20),
    (Resource.Stone, 20)
]

# Loop over each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest position of this resource
    resource_position = nearest(resource_type)
    print(f"Nearest {resource_type} found at {resource_position}")
    
    # Move to the resource
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    print(f"Harvested {harvested} units of {resource_type}")
    
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} units of {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory after gathering: {final_inventory}")

# Assert that we have gathered at least as much as we need
assert final_inventory.get(Resource.IronOre, 0) >= 88, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 20, "Not enough Coal"
assert final_inventory.get(Resource.Stone, 0) >= 20, "Not enough Stone"

print("Successfully gathered all required resources!")


"""
Step 2: Craft stone furnaces. We need to craft 4 stone furnaces. 
"""
# Craft 4 stone furnaces
furnaces_crafted = craft_item(Prototype.StoneFurnace, 4)
print(f"Crafted {furnaces_crafted} Stone Furnaces")

# Check if we crafted enough furnaces
current_inventory = inspect_inventory()
furnaces_in_inventory = current_inventory.get(Prototype.StoneFurnace, 0)
assert furnaces_in_inventory >= 4, f"Failed to craft enough Stone Furnaces. Required: 4, Actual: {furnaces_in_inventory}"

print(f"Successfully crafted {furnaces_in_inventory} Stone Furnaces")


"""
Step 3: Set up smelting area. We need to place and fuel the furnaces. 
"""
# Move to a suitable position to place the furnaces
move_to(Position(x=0, y=0))

# Place the first furnace
furnace1 = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
print(f"Placed first Stone Furnace at {furnace1.position}")

# Place the second furnace to the right of the first one
furnace2 = place_entity(Prototype.StoneFurnace, position=Position(x=2, y=0))
print(f"Placed second Stone Furnace at {furnace2.position}")

# Fuel the first furnace
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
if coal_in_inventory > 0:
    insert_item(Prototype.Coal, furnace1, quantity=5)
    print("Inserted coal into the first furnace")

# Fuel the second furnace
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
if coal_in_inventory > 0:
    insert_item(Prototype.Coal, furnace2, quantity=5)
    print("Inserted coal into the second furnace")

# Verify that both furnaces have fuel
furnace1_inventory = inspect_inventory(furnace1)
furnace2_inventory = inspect_inventory(furnace2)
assert furnace1_inventory.get(Prototype.Coal, 0) > 0, "First furnace is not fueled"
assert furnace2_inventory.get(Prototype.Coal, 0) > 0, "Second furnace is not fueled"

print("Successfully placed and fueled both Stone Furnaces")


"""
Step 4: Smelt iron plates. We need to smelt 88 iron ore into iron plates. 
"""
# Insert iron ore into the furnaces
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
if iron_ore_in_inventory > 0:
    half_iron_ore = iron_ore_in_inventory // 2
    insert_item(Prototype.IronOre, furnace1, quantity=half_iron_ore)
    insert_item(Prototype.IronOre, furnace2, quantity=half_iron_ore)
    print(f"Inserted {half_iron_ore} iron ore into each furnace")

# Wait for smelting to complete
smelting_time = 0.7 * half_iron_ore  # 0.7 seconds per iron plate
sleep(smelting_time)

# Extract iron plates from the furnaces
max_attempts = 5
for attempt in range(max_attempts):
    extract_item(Prototype.IronPlate, furnace1.position, quantity=half_iron_ore)
    extract_item(Prototype.IronPlate, furnace2.position, quantity=half_iron_ore)
    iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
    
    if iron_plates_in_inventory >= 88:
        break
    
    sleep(10)

print(f"Extracted Iron Plates; Current Inventory Count: {iron_plates_in_inventory}")
print(f"Final Inventory: {inspect_inventory()}")
assert iron_plates_in_inventory >= 88, f"Failed to obtain enough Iron Plates. Required: 88, Actual: {iron_plates_in_inventory}"

print("Successfully obtained required number of Iron Plates!")


"""
Step 5: Craft components. We need to craft 2 underground belts and 40 iron gear wheels. 
"""
# Craft 40 Iron Gear Wheels
iron_gear_wheels_crafted = craft_item(Prototype.IronGearWheel, 40)
print(f"Crafted {iron_gear_wheels_crafted} Iron Gear Wheels")

# Check if we crafted enough Iron Gear Wheels
current_inventory = inspect_inventory()
iron_gear_wheels_in_inventory = current_inventory.get(Prototype.IronGearWheel, 0)
assert iron_gear_wheels_in_inventory >= 40, f"Failed to craft enough Iron Gear Wheels. Required: 40, Actual: {iron_gear_wheels_in_inventory}"

# Craft 2 Underground Belts
underground_belts_crafted = craft_item(Prototype.UndergroundBelt, 2)
print(f"Crafted {underground_belts_crafted} Underground Belts")

# Check if we crafted enough Underground Belts
current_inventory = inspect_inventory()
underground_belts_in_inventory = current_inventory.get(Prototype.UndergroundBelt, 0)
assert underground_belts_in_inventory >= 2, f"Failed to craft enough Underground Belts. Required: 2, Actual: {underground_belts_in_inventory}"

print(f"Successfully crafted {iron_gear_wheels_in_inventory} Iron Gear Wheels and {underground_belts_in_inventory} Underground Belts")


"""
Step 6: Craft fast-underground-belt. We need to craft 1 fast-underground-belt. 
"""
# Craft 1 Fast Underground Belt
fast_underground_belt_crafted = craft_item(Prototype.FastUndergroundBelt, 1)
print(f"Crafted {fast_underground_belt_crafted} Fast Underground Belts")

# Check if we crafted the Fast Underground Belt
current_inventory = inspect_inventory()
fast_underground_belts_in_inventory = current_inventory.get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belts_in_inventory >= 1, f"Failed to craft a Fast Underground Belt. Required: 1, Actual: {fast_underground_belts_in_inventory}"

print(f"Successfully crafted a Fast Underground Belt; Current Inventory Count: {fast_underground_belts_in_inventory}")
print(f"Final Inventory: {inspect_inventory()}")

