

from instance import *

"""
Objective: Craft an underground-belt from scratch

Planning:
We need to craft an underground-belt which requires:
- 2 transport belts (4 iron plates, 4 iron gear wheels)
- 10 iron plates

In total, we need at least 14 iron plates and 4 iron gear wheels.

Since we have no entities on the map or in our inventory, we need to:
1. Gather raw resources (iron ore, coal, stone)
2. Craft and set up smelting infrastructure
3. Craft intermediate products
4. Craft the final product

Let's break this down into detailed steps.
"""

"""
Step 1: Gather raw resources
- We need to mine iron ore, coal, and stone
- We need 21 iron ore (for iron plates and iron gear wheels)
- We need 10 coal (for fueling the furnaces and drills)
- We need 12 stone (for crafting 2 stone furnaces)
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 21),
    (Resource.Coal, 10),
    (Resource.Stone, 12)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    print(f"Nearest {resource_type} found at: {resource_position}")
    
    # Move to the resource
    move_to(resource_position)
    print(f"Moved to {resource_type} at position {resource_position}")
    
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
print("Final inventory after gathering resources:")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")

# Assert that we have gathered at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 21, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 10, "Not enough Coal"
assert final_inventory.get(Resource.Stone, 0) >= 12, "Not enough Stone"

print("Successfully gathered all required resources!")

"""
Step 2: Set up smelting infrastructure
- Craft 2 stone furnaces
- Place the furnaces
- Fuel the furnaces with coal
"""
# Craft stone furnaces
craft_item(Prototype.StoneFurnace, quantity=2)
print("Crafted 2 Stone Furnaces")

# Place the furnaces
origin = Position(x=0, y=0)
move_to(origin)

furnace_1 = place_entity(Prototype.StoneFurnace, position=Position(x=1, y=0))
furnace_2 = place_entity(Prototype.StoneFurnace, position=Position(x=3, y=0))
print("Placed 2 Stone Furnaces")

# Fuel the furnaces
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
assert coal_in_inventory >= 10, f"Insufficient coal in inventory to fuel furnaces. Expected at least 10, found {coal_in_inventory}"

furnace_1 = insert_item(Prototype.Coal, furnace_1, quantity=5)
furnace_2 = insert_item(Prototype.Coal, furnace_2, quantity=5)
print("Inserted coal into both furnaces")

"""
Step 3: Craft intermediate products
- Smelt iron plates (21 iron ore -> 21 iron plates)
- Craft 4 iron gear wheels (8 iron plates)
"""
# Insert iron ore into furnaces
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
assert iron_ore_in_inventory >= 21, f"Insufficient iron ore in inventory. Expected at least 21, found {iron_ore_in_inventory}"

furnace_1 = insert_item(Prototype.IronOre, furnace_1, quantity=11)
furnace_2 = insert_item(Prototype.IronOre, furnace_2, quantity=10)
print("Inserted iron ore into both furnaces")

# Wait for smelting to complete
sleep(15)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace_1.position, quantity=11)
extract_item(Prototype.IronPlate, furnace_2.position, quantity=10)

iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
assert iron_plates_in_inventory >= 21, f"Failed to smelt enough iron plates. Expected at least 21, found {iron_plates_in_inventory}"
print(f"Smelted {iron_plates_in_inventory} Iron Plates")

# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=4)
print("Crafted 4 Iron Gear Wheels")

"""
Step 4: Craft underground-belt
- Craft 2 transport belts (4 iron plates, 4 iron gear wheels)
- Craft 1 underground-belt (2 transport belts, 10 iron plates)
"""
# Craft transport belts
craft_item(Prototype.TransportBelt, quantity=2)
print("Crafted 2 Transport Belts")

# Craft underground-belt
craft_item(Prototype.UndergroundBelt, quantity=1)
print("Crafted 1 Underground Belt")

# Verify that we have the underground-belt in our inventory
underground_belt_in_inventory = inspect_inventory().get(Prototype.UndergroundBelt, 0)
assert underground_belt_in_inventory >= 1, f"Failed to craft Underground Belt. Expected at least 1, found {underground_belt_in_inventory}"
print(f"Successfully crafted {underground_belt_in_inventory} Underground Belt(s)")

print("Objective complete: Crafted an Underground Belt from scratch")

