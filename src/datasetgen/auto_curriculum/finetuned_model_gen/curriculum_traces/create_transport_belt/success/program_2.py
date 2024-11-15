

from factorio_instance import *

"""
Step 1: Print recipe. We need to craft a transport belt. 
Recipe for transport belt: 1 iron gear wheel, 1 iron plate
We need to craft:
- transport belt: 1
"""

"""
Step 2: Gather resources
- Mine iron ore (at least 3 for 1 gear wheel and 1 plate)
- Mine stone (at least 5 for furnace)
- Mine coal (for fuel)
"""

# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 3),
    (Resource.Stone, 5),
    (Resource.Coal, 5)
]

# Loop through each resource and gather it
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    assert resource_position, f"Failed to find {resource_type}"

    # Move to the resource
    move_to(resource_position)

    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    
    # Check that we harvested the correct amount
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
for resource_type, required_quantity in resources_to_gather:
    actual_quantity = final_inventory.get(resource_type, 0)
    print(f"Final count of {resource_type}: {actual_quantity}")
    assert actual_quantity >= required_quantity, f"Final check failed for {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"

print("Successfully gathered all required resources")
print(f"Current inventory: {inspect_inventory()}")

"""
Step 3: Craft stone furnace and set it up
- Craft 1 stone furnace
- Place the furnace
- Add coal to the furnace as fuel
"""

# Craft the stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 Stone Furnace")

# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed Stone Furnace at {furnace.position}")

# Insert coal into the furnace as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=5)
print("Inserted coal into the Stone Furnace")

# Verify that the furnace has fuel
coal_in_furnace = updated_furnace.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace > 0, "Failed to insert coal into the furnace"
print("Stone Furnace successfully set up with fuel")

"""
Step 4: Smelt iron plates
- Smelt 3 iron ore into 3 iron plates
"""

# Insert iron ore into the furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} Iron Ore into the Stone Furnace")

# Wait for the smelting process to complete
smelting_time_per_unit = 0.7  # Assuming a constant smelting time per unit
total_smelting_time = int(smelting_time_per_unit * iron_ore_in_inventory)
sleep(total_smelting_time)

# Attempt to extract the smelted iron plates
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
    
    if iron_plates_in_inventory >= iron_ore_in_inventory:
        break
    
    sleep(10)  # Wait a bit more if all plates aren't ready

print(f"Extracted Iron Plates; Current Inventory Count: {iron_plates_in_inventory}")

assert iron_plates_in_inventory >= 3, f"Failed to obtain required number of Iron Plates! Expected at least 3 but got {iron_plates_in_inventory}"
print("Successfully smelted and extracted Iron Plates")

"""
Step 5: Craft iron gear wheel
- Craft 1 iron gear wheel (requires 2 iron plates)
"""

# Craft iron gear wheel
craft_item(Prototype.IronGearWheel, quantity=1)
print("Crafted 1 Iron Gear Wheel")

# Verify that the iron gear wheel was crafted
iron_gear_wheel_count = inspect_inventory().get(Prototype.IronGearWheel, 0)
assert iron_gear_wheel_count >= 1, f"Failed to craft Iron Gear Wheel! Expected at least 1 but got {iron_gear_wheel_count}"
print("Successfully crafted Iron Gear Wheel")

"""
Step 6: Craft transport belt
- Craft 1 transport belt (requires 1 iron gear wheel, 1 iron plate)
"""

# Craft transport belt
craft_item(Prototype.TransportBelt, quantity=1)
print("Crafted 1 Transport Belt")

# Verify that the transport belt was crafted
transport_belt_count = inspect_inventory().get(Prototype.TransportBelt, 0)
assert transport_belt_count >= 1, f"Failed to craft Transport Belt! Expected at least 1 but got {transport_belt_count}"
print("Successfully crafted Transport Belt")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory after crafting Transport Belt: {final_inventory}")

