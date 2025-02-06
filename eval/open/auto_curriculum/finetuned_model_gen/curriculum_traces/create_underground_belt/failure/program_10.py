

from instance import *

"""
Step 1: Print recipes. We need to craft an underground-belt, which requires 10 iron plates, 10 iron gear wheels, and 1 transport belt. 
To craft these, we need to smelt iron ore into iron plates, and then craft the iron gear wheels and transport belt.
We also need stone furnaces for smelting.
"""

# Print recipe for underground-belt
print("Underground-belt requires 10 iron plates, 10 iron gear wheels, and 1 transport belt")

# Print recipe for iron gear wheels
print("Iron gear wheels require 2 iron plates each")

# Print recipe for transport belt
print("Transport belt requires 1 iron gear wheel (2 iron plates) and 1 iron plate")

# Print recipe for stone furnace
print("Stone furnace requires 5 stone")

"""
Step 2: Gather raw resources. We need to mine:
- At least 21 iron ore (for 26 iron plates)
- At least 12 stone (for 2 stone furnaces)
- At least 2 coal (for fuel)
"""

# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 21),
    (Resource.Stone, 12),
    (Resource.Coal, 2)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    print(f"Starting to gather {required_quantity} of {resource_type}")
    
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    print(f"Nearest {resource_type} found at position {resource_position}")
    
    # Move to the resource
    move_to(resource_position)
    print(f"Moved to {resource_type} patch")
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    print(f"Harvested {harvested} of {resource_type}")
    
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    if actual_quantity >= required_quantity:
        print(f"Successfully gathered {actual_quantity} of {resource_type}")
    else:
        print(f"Warning: Only gathered {actual_quantity} of {resource_type}, expected at least {required_quantity}")
    
    # Print the current inventory state
    print(f"Current inventory: {current_inventory}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory after gathering all resources:")
print(final_inventory)

# Assert statements to ensure we have gathered enough resources
assert final_inventory.get(Resource.IronOre, 0) >= 21, "Not enough Iron Ore"
assert final_inventory.get(Resource.Stone, 0) >= 12, "Not enough Stone"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Not enough Coal"

print("Successfully gathered all required resources")

"""
Step 3: Craft stone furnaces. We need to craft 2 stone furnaces, which requires 10 stone in total.
"""

# Craft 2 stone furnaces
crafted_furnaces = craft_item(Prototype.StoneFurnace, 2)
print(f"Crafted {crafted_furnaces} stone furnaces")

# Check the inventory to confirm we have the stone furnaces
current_inventory = inspect_inventory()
stone_furnaces = current_inventory.get(Prototype.StoneFurnace, 0)
print(f"Current inventory: {current_inventory}")
assert stone_furnaces >= 2, f"Failed to craft required number of stone furnaces. Expected 2, but got {stone_furnaces}"

print("Successfully crafted 2 stone furnaces")

"""
Step 4: Set up smelting area. We need to:
- Place the stone furnaces
- Add coal to the furnaces as fuel
"""

# Place the first furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace1 = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed first stone furnace at {furnace1.position}")

# Place the second furnace to the right of the first one
furnace2 = place_entity_next_to(Prototype.StoneFurnace, direction=Direction.RIGHT, reference_position=furnace1.position)
print(f"Placed second stone furnace at {furnace2.position}")

# Add coal to the furnaces as fuel
for furnace in [furnace1, furnace2]:
    updated_furnace = insert_item(Prototype.Coal, furnace, quantity=1)
    coal_in_fuel_slot = updated_furnace.fuel.get(Prototype.Coal, 0)
    assert coal_in_fuel_slot > 0, f"Failed to add coal to furnace at {furnace.position}"
    print(f"Added coal to furnace at {furnace.position}")

print("Successfully set up smelting area")

"""
Step 5: Smelt iron plates. We need to:
- Smelt 21 iron ore into 21 iron plates
"""

# Insert iron ore into the furnaces
iron_ore_to_insert = 21 // 2  # Divide equally between two furnaces

for furnace in [furnace1, furnace2]:
    updated_furnace = insert_item(Prototype.IronOre, furnace, quantity=iron_ore_to_insert)
    print(f"Inserted iron ore into furnace at {furnace.position}")

# Wait for smelting to complete
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_to_insert)
sleep(total_smelting_time)

# Extract iron plates from the furnaces
for furnace in [furnace1, furnace2]:
    while True:
        extract_item(Prototype.IronPlate, furnace.position, quantity=iron_ore_to_insert)
        current_inventory = inspect_inventory()
        if current_inventory.get(Prototype.IronPlate, 0) >= 21:
            break
        sleep(10)

# Verify that we have enough iron plates
final_inventory = inspect_inventory()
iron_plates = final_inventory.get(Prototype.IronPlate, 0)
assert iron_plates >= 21, f"Failed to obtain required number of iron plates. Expected 21, but got {iron_plates}"

print(f"Successfully obtained {iron_plates} iron plates")

"""
Step 6: Craft iron gear wheels. We need to:
- Craft 10 iron gear wheels (each requires 2 iron plates, so 20 iron plates in total)
"""

# Craft 10 iron gear wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, 10)
print(f"Crafted {crafted_gear_wheels} iron gear wheels")

# Check the inventory to confirm we have the iron gear wheels
current_inventory = inspect_inventory()
iron_gear_wheels = current_inventory.get(Prototype.IronGearWheel, 0)
print(f"Current inventory: {current_inventory}")
assert iron_gear_wheels >= 10, f"Failed to craft required number of iron gear wheels. Expected 10, but got {iron_gear_wheels}"

print("Successfully crafted 10 iron gear wheels")

"""
Step 7: Craft transport belt. We need to:
- Craft 1 transport belt (each requires 1 iron gear wheel and 1 iron plate)
"""

# Craft transport belt
crafted_transport_belts = craft_item(Prototype.TransportBelt, 1)
print(f"Crafted {crafted_transport_belts} transport belts")

# Check the inventory to confirm we have the transport belts
current_inventory = inspect_inventory()
transport_belts = current_inventory.get(Prototype.TransportBelt, 0)
print(f"Current inventory: {current_inventory}")
assert transport_belts >= 1, f"Failed to craft required number of transport belts. Expected 1, but got {transport_belts}"

print("Successfully crafted 1 transport belt")

"""
Step 8: Craft underground-belt. We need to:
- Craft 1 underground-belt (requires 10 iron plates, 10 iron gear wheels, and 1 transport belt)
"""

# Ensure we have all required materials
current_inventory = inspect_inventory()
print(f"Current inventory before crafting underground-belt: {current_inventory}")

# Verify that we have enough materials
assert current_inventory.get(Prototype.IronPlate, 0) >= 10, f"Not enough iron plates. Expected at least 10, but got {current_inventory.get(Prototype.IronPlate, 0)}"
assert current_inventory.get(Prototype.IronGearWheel, 0) >= 10, f"Not enough iron gear wheels. Expected at least 10, but got {current_inventory.get(Prototype.IronGearWheel, 0)}"
assert current_inventory.get(Prototype.TransportBelt, 0) >= 1, f"Not enough transport belts. Expected at least 1, but got {current_inventory.get(Prototype.TransportBelt, 0)}"

# Craft underground-belt
crafted_underground_belts = craft_item(Prototype.UndergroundBelt, 1)
print(f"Crafted {crafted_underground_belts} underground-belts")

# Check the inventory to confirm we have the underground-belts
current_inventory = inspect_inventory()
underground_belts = current_inventory.get(Prototype.UndergroundBelt, 0)
print(f"Current inventory after crafting: {current_inventory}")
assert underground_belts >= 1, f"Failed to craft required number of underground-belts. Expected 1, but got {underground_belts}"

print("Successfully crafted 1 underground-belt")

