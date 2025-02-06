

from instance import *

"""
Objective: Craft an underground-belt from scratch

Planning:
We need to craft an underground-belt. The recipe for underground-belt requires:
- 6 iron plates
- 10 iron gear wheels
- 2 transport belts

We need to craft all components from scratch as we have nothing in our inventory.
We'll need to gather iron ore, coal for fuel, and stone for furnaces.
We'll need to smelt iron plates, craft iron gear wheels, transport belts, and then the underground-belt.
"""

"""
Step 1: Print recipe
"""
print("Recipes:")
print("Transport Belt: 1 iron gear wheel, 1 iron plate")
print("Underground Belt: 10 iron gear wheels, 2 transport belts")

"""
Step 2: Gather raw resources
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 21),
    (Resource.Coal, 2),
    (Resource.Stone, 12)
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

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 21, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Not enough Coal"
assert final_inventory.get(Resource.Stone, 0) >= 12, "Not enough Stone"

print("Successfully gathered all required resources!")

"""
Step 3: Craft stone furnaces
"""
craft_item(Prototype.StoneFurnace, quantity=2)
print("Crafted 2 Stone Furnaces")

"""
Step 4: Set up smelting operation
"""
# Place a stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)

# Add fuel and start smelting
insert_item(Prototype.Coal, furnace, quantity=1)
insert_item(Prototype.IronOre, furnace, quantity=21)
print("Inserted coal and iron ore into the furnace")

# Wait for smelting to complete
smelting_time = 21 * 0.7  # 0.7 seconds per ore
sleep(smelting_time)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=21)
print("Extracted Iron Plates")

# Verify iron plates count
iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
assert iron_plates >= 21, f"Not enough iron plates. Expected 21, got {iron_plates}"
print(f"Current Iron Plates: {iron_plates}")

"""
Step 5: Craft intermediate products
"""
craft_item(Prototype.IronGearWheel, quantity=10)
print("Crafted 10 Iron Gear Wheels")

"""
Step 6: Craft transport-belts
"""
craft_item(Prototype.TransportBelt, quantity=4)
print("Crafted 4 Transport Belts")

"""
Step 7: Craft underground-belt
"""
craft_item(Prototype.UndergroundBelt, quantity=1)
print("Crafted 1 Underground Belt")

"""
Step 8: Verify the final result
"""
final_inventory = inspect_inventory()
underground_belts = final_inventory.get(Prototype.UndergroundBelt, 0)
assert underground_belts >= 1, f"Failed to craft Underground Belts. Expected at least 1, got {underground_belts}"
print(f"Successfully crafted Underground Belts. Current count: {underground_belts}")

print("Objective completed successfully!")

