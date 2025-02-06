

"""
Objective: Craft a fast-underground-belt from scratch

Planning:
We need to craft iron gear wheels and underground belts to produce a fast-underground-belt. 
There are no entities on the map or items in the inventory, so we need to gather all resources and craft all intermediate products.
We need to gather iron ore, smelt it into iron plates, and then craft the required items.
We'll need at least one stone furnace for smelting.
"""

from instance import *

"""
Step 1: Print recipes
"""
# Print recipe for fast-underground-belt
print("fast-underground-belt recipe:")
print("1 fast-underground-belt requires 2 underground-belts, 40 iron gear wheels")

# Print recipe for underground-belt
print("\nunderground-belt recipe:")
print("1 underground-belt requires 10 iron gear wheels, 2 transport belts")

# Print recipe for transport-belt
print("\ntransport-belt recipe:")
print("1 transport-belt requires 1 iron gear wheel, 1 iron plate")

# Print recipe for iron gear wheel
print("\niron gear wheel recipe:")
print("1 iron gear wheel requires 2 iron plates")

# Print recipe for stone furnace
print("\nstone furnace recipe:")
print("1 stone furnace requires 5 stone")


"""
Step 1: Gather resources
- Mine iron ore (at least 88 for 40 iron gear wheels and 2 underground belts)
- Mine stone for a furnace (5 stone)
- Mine coal for fuel
"""
# Define required quantities
iron_ore_needed = 88
stone_needed = 5
coal_needed = 30

# Define resources to gather
resources_to_gather = [
    (Resource.IronOre, iron_ore_needed),
    (Resource.Stone, stone_needed),
    (Resource.Coal, coal_needed)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest position of this resource type
    resource_position = nearest(resource_type)
    
    # Move to the resource
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    
    # Check that we harvested at least as much as we needed
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Needed {required_quantity}, but only have {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check and assertion
final_inventory = inspect_inventory()
print("Final inventory:", final_inventory)
assert final_inventory.get(Resource.IronOre, 0) >= iron_ore_needed, "Not enough Iron Ore"
assert final_inventory.get(Resource.Stone, 0) >= stone_needed, "Not enough Stone"
assert final_inventory.get(Resource.Coal, 0) >= coal_needed, "Not enough Coal"

print("Successfully gathered all required resources")

"""
Step 2: Craft stone furnace
- Craft 1 stone furnace
"""
# Craft a stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 Stone Furnace")

# Verify that the stone furnace is in the inventory
stone_furnaces_in_inventory = inspect_inventory().get(Prototype.StoneFurnace, 0)
assert stone_furnaces_in_inventory >= 1, f"Failed to craft Stone Furnace. Expected at least 1 but got {stone_furnaces_in_inventory}"
print(f"Successfully crafted {stone_furnaces_in_inventory} Stone Furnace(s)")

"""
Step 3: Set up smelting
- Place the stone furnace
- Add coal as fuel
- Smelt iron ore into iron plates (at least 88 plates)
"""
# Place the stone furnace at origin
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
print(f"Placed Stone Furnace at {furnace.position}")

# Insert coal into the furnace as fuel
updated_furnace = insert_item(Prototype.Coal, target=furnace, quantity=30)
print("Inserted coal into the Stone Furnace")

# Insert iron ore into the furnace
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
updated_furnace = insert_item(Prototype.IronOre, target=updated_furnace, quantity=iron_ore_in_inventory)
print("Inserted iron ore into the Stone Furnace")

# Smelt iron ore into iron plates
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_in_inventory)
sleep(total_smelting_time)

# Extract iron plates
extract_item(Prototype.IronPlate, updated_furnace.position, iron_ore_in_inventory)
print(f"Extracted Iron Plates from the Stone Furnace")

# Verify that we have enough iron plates
current_inventory = inspect_inventory()
iron_plates_in_inventory = current_inventory.get(Prototype.IronPlate, 0)
assert iron_plates_in_inventory >= 88, f"Failed to smelt enough Iron Plates. Needed at least 88 but got {iron_plates_in_inventory}"
print(f"Successfully smelted {iron_plates_in_inventory} Iron Plates")

"""
Step 4: Craft iron gear wheels
- Craft 40 iron gear wheels (requires 80 iron plates)
"""
# Craft 40 iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=40)
print("Crafted 40 Iron Gear Wheels")

# Verify that the iron gear wheels are in the inventory
iron_gear_wheels_in_inventory = inspect_inventory().get(Prototype.IronGearWheel, 0)
assert iron_gear_wheels_in_inventory >= 40, f"Failed to craft Iron Gear Wheels. Expected at least 40 but got {iron_gear_wheels_in_inventory}"
print(f"Successfully crafted {iron_gear_wheels_in_inventory} Iron Gear Wheel(s)")

"""
Step 5: Craft transport belts
- Craft 4 transport belts (requires 4 iron gear wheels and 4 iron plates)
"""
# Calculate required resources
iron_gear_wheels_needed = 4
iron_plates_needed = 4

# Verify that we have enough resources in the inventory
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronGearWheel, 0) >= iron_gear_wheels_needed, f"Not enough Iron Gear Wheels. Needed {iron_gear_wheels_needed} but got {current_inventory.get(Prototype.IronGearWheel, 0)}"
assert current_inventory.get(Prototype.IronPlate, 0) >= iron_plates_needed, f"Not enough Iron Plates. Needed {iron_plates_needed} but got {current_inventory.get(Prototype.IronPlate, 0)}"

# Craft 4 transport belts
craft_item(Prototype.TransportBelt, quantity=4)
print("Crafted 4 Transport Belts")

# Verify that the transport belts are in the inventory
transport_belts_in_inventory = inspect_inventory().get(Prototype.TransportBelt, 0)
assert transport_belts_in_inventory >= 4, f"Failed to craft Transport Belts. Expected at least 4 but got {transport_belts_in_inventory}"
print(f"Successfully crafted {transport_belts_in_inventory} Transport Belt(s)")

"""
Step 6: Craft underground belts
- Craft 2 underground belts (requires 20 iron gear wheels and 4 transport belts)
"""
# Calculate required resources
iron_gear_wheels_needed = 20
transport_belts_needed = 4

# Verify that we have enough resources in the inventory
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronGearWheel, 0) >= iron_gear_wheels_needed, f"Not enough Iron Gear Wheels. Needed {iron_gear_wheels_needed} but got {current_inventory.get(Prototype.IronGearWheel, 0)}"
assert current_inventory.get(Prototype.TransportBelt, 0) >= transport_belts_needed, f"Not enough Transport Belts. Needed {transport_belts_needed} but got {current_inventory.get(Prototype.TransportBelt, 0)}"

# Craft 2 underground belts
craft_item(Prototype.UndergroundBelt, quantity=2)
print("Crafted 2 Underground Belts")

# Verify that the underground belts are in the inventory
underground_belts_in_inventory = inspect_inventory().get(Prototype.UndergroundBelt, 0)
assert underground_belts_in_inventory >= 2, f"Failed to craft Underground Belts. Expected at least 2 but got {underground_belts_in_inventory}"
print(f"Successfully crafted {underground_belts_in_inventory} Underground Belt(s)")

"""
Step 7: Craft fast-underground-belt
- Craft 1 fast-underground-belt (requires 2 underground belts and 40 iron gear wheels)
"""
# Calculate required resources
iron_gear_wheels_needed = 40
underground_belts_needed = 2

# Verify that we have enough resources in the inventory
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronGearWheel, 0) >= iron_gear_wheels_needed, f"Not enough Iron Gear Wheels. Needed {iron_gear_wheels_needed} but got {current_inventory.get(Prototype.IronGearWheel, 0)}"
assert current_inventory.get(Prototype.UndergroundBelt, 0) >= underground_belts_needed, f"Not enough Underground Belts. Needed {underground_belts_needed} but got {current_inventory.get(Prototype.UndergroundBelt, 0)}"

# Craft 1 fast-underground-belt
craft_item(Prototype.FastUndergroundBelt, quantity=1)
print("Crafted 1 Fast Underground Belt")

# Verify that the fast-underground-belt is in the inventory
fast_underground_belts_in_inventory = inspect_inventory().get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belts_in_inventory >= 1, f"Failed to craft Fast Underground Belt. Expected at least 1 but got {fast_underground_belts_in_inventory}"
print(f"Successfully crafted {fast_underground_belts_in_inventory} Fast Underground Belt(s)")

