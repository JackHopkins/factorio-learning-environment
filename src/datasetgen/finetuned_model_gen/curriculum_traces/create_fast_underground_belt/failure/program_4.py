
from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- Stone Furnace
- Iron Gear Wheel
- Transport Belt
- Underground Belt
- Fast Underground Belt
"""
# Print recipes
print("Stone Furnace Recipe: 5 stone")
print("Iron Gear Wheel Recipe: 2 iron plates")
print("Transport Belt Recipe: 1 iron gear wheel, 1 iron plate")
print("Underground Belt Recipe: 10 iron gear wheels, 1 transport belt")
print("Fast Underground Belt Recipe: 1 iron gear wheel, 1 underground belt")


"""
Step 2: Gather resources. We need to gather the following resources:
- 10 stone (for 2 stone furnaces)
- 20 iron ore (for 20 iron plates)
- 10 coal (for fueling the furnaces)
"""
# Define required resources
required_resources = {
    Resource.Stone: 10,
    Resource.IronOre: 20,
    Resource.Coal: 10
}

# Loop through required resources and collect them
for resource_type, required_quantity in required_resources.items():
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    # Move to the resource
    move_to(resource_position)
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    # Verify that we harvested enough
    current_inventory = inspect_inventory()
    assert current_inventory.get(resource_type) >= required_quantity, f"Failed to harvest enough {resource_type}. Expected at least {required_quantity}, but got {current_inventory.get(resource_type)}"
    print(f"Successfully harvested {harvested} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
for resource_type, required_quantity in required_resources.items():
    actual_quantity = final_inventory.get(resource_type, 0)
    print(f"{resource_type}: {actual_quantity}")
    assert actual_quantity >= required_quantity, f"Not enough {resource_type}. Expected at least {required_quantity}, but got {actual_quantity}"
    
print("Successfully gathered all required resources!")


"""
Step 3: Craft stone furnaces. We need to craft 2 stone furnaces.
"""
# Craft 2 stone furnaces
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=2)
print(f"Crafted {crafted_furnaces} stone furnaces")

# Verify that we have 2 stone furnaces in our inventory
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.StoneFurnace, 0) >= 2, f"Failed to craft 2 stone furnaces. Current inventory: {current_inventory}"
print("Successfully crafted 2 stone furnaces!")


"""
Step 4: Set up smelting area. We need to:
- Place 2 stone furnaces
- Fuel both furnaces with coal
"""
# Move to a suitable position for placing the furnaces
target_position = Position(x=0, y=0)
move_to(target_position)

# Place the first stone furnace
furnace1 = place_entity(Prototype.StoneFurnace, position=target_position)
print(f"Placed first stone furnace at {furnace1.position}")

# Place the second stone furnace next to the first one
furnace2 = place_entity_next_to(Prototype.StoneFurnace, direction=Direction.RIGHT, reference_position=furnace1.position)
print(f"Placed second stone furnace at {furnace2.position}")

# Insert coal into both furnaces
updated_furnace1 = insert_item(Prototype.Coal, furnace1, quantity=5)
updated_furnace2 = insert_item(Prototype.Coal, furnace2, quantity=5)

# Verify that coal was successfully inserted
assert updated_furnace1.fuel.get(Prototype.Coal, 0) > 0, "Failed to insert coal into first furnace"
assert updated_furnace2.fuel.get(Prototype.Coal, 0) > 0, "Failed to insert coal into second furnace"
print("Successfully fueled both furnaces")


"""
Step 5: Smelt iron plates. We need to:
- Smelt 20 iron ore into 20 iron plates
- Use both furnaces to speed up the process
- Ensure all plates are extracted from the furnaces
"""
# Divide iron ore equally between the two furnaces
iron_ore_per_furnace = 10

# Insert iron ore into both furnaces
updated_furnace1 = insert_item(Prototype.IronOre, updated_furnace1, quantity=iron_ore_per_furnace)
updated_furnace2 = insert_item(Prototype.IronOre, updated_furnace2, quantity=iron_ore_per_furnace)

# Wait for smelting to complete (0.7 seconds per ore)
smelting_time = 0.7 * iron_ore_per_furnace
sleep(smelting_time)

# Extract iron plates from both furnaces
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace1.position, quantity=iron_ore_per_furnace)
    extract_item(Prototype.IronPlate, updated_furnace2.position, quantity=iron_ore_per_furnace)
    
    # Check if we have enough iron plates
    current_inventory = inspect_inventory()
    if current_inventory.get(Prototype.IronPlate, 0) >= 20:
        break
    sleep(5)

# Verify that we have 20 iron plates
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.IronPlate, 0) >= 20, f"Failed to obtain 20 iron plates. Current inventory: {final_inventory}"
print("Successfully obtained required number of iron plates!")


"""
Step 6: Craft components. We need to craft the following components:
- 10 iron gear wheels (for underground belt)
- 1 transport belt
"""
# Craft 10 iron gear wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=10)
print(f"Crafted {crafted_gear_wheels} iron gear wheels")

# Verify that we have 10 iron gear wheels in our inventory
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronGearWheel, 0) >= 10, f"Failed to craft 10 iron gear wheels. Current inventory: {current_inventory}"

# Craft 1 transport belt
crafted_transport_belt = craft_item(Prototype.TransportBelt, quantity=1)
print(f"Crafted {crafted_transport_belt} transport belt")

# Verify that we have 1 transport belt in our inventory
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.TransportBelt, 0) >= 1, f"Failed to craft 1 transport belt. Current inventory: {current_inventory}"

print("Successfully crafted all required components!")


"""
Step 7: Craft underground belts. We need to craft 1 underground belt.
"""
# Craft 1 underground belt
crafted_underground_belt = craft_item(Prototype.UndergroundBelt, quantity=1)
print(f"Crafted {crafted_underground_belt} underground belt")

# Verify that we have 1 underground belt in our inventory
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.UndergroundBelt, 0) >= 1, f"Failed to craft 1 underground belt. Current inventory: {current_inventory}"

print("Successfully crafted 1 underground belt!")


"""
Step 8: Craft fast underground belt. We need to craft 1 fast underground belt.
"""
# Craft 1 fast underground belt
crafted_fast_underground_belt = craft_item(Prototype.FastUndergroundBelt, quantity=1)
print(f"Crafted {crafted_fast_underground_belt} fast underground belt")

# Verify that we have 1 fast underground belt in our inventory
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, f"Failed to craft 1 fast underground belt. Current inventory: {current_inventory}"

print("Successfully crafted 1 fast underground belt!")

