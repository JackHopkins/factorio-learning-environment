
from instance import *

"""
Step 1: Print recipes for required items
"""
# Print recipe for fast-underground-belt
print("Fast-Underground-Belt recipe:")
print("2 iron gear wheels, 1 underground belt")

# Print recipe for underground-belt
print("Underground Belt recipe:")
print("10 iron gear wheels, 1 transport belt")

# Print recipe for transport-belt
print("Transport Belt recipe:")
print("1 iron gear wheel, 1 iron plate")

# Print recipe for iron gear wheel
print("Iron Gear Wheel recipe:")
print("2 iron plates")

"""
Step 2: Gather resources
- Mine coal (at least 1 for fuel)
- Mine stone (at least 6 for the furnace)
- Mine iron ore (at least 7 for iron plates)
"""
# Define resources to gather
resources_to_gather = [
    (Resource.Coal, 1),
    (Resource.Stone, 6),
    (Resource.IronOre, 7)
]

# Loop through each resource and gather it
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    print(f"Nearest {resource_type} found at: {resource_position}")

    # Move to the resource
    move_to(resource_position)
    print(f"Moved to {resource_type} patch at: {resource_position}")

    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    print(f"Harvested {harvested} of {resource_type}")

    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, \
        f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} of {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.Coal, 0) >= 1, \
    f"Final check failed for Coal. Required: 1, Actual: {final_inventory.get(Resource.Coal, 0)}"
assert final_inventory.get(Resource.Stone, 0) >= 6, \
    f"Final check failed for Stone. Required: 6, Actual: {final_inventory.get(Resource.Stone, 0)}"
assert final_inventory.get(Resource.IronOre, 0) >= 7, \
    f"Final check failed for Iron Ore. Required: 7, Actual: {final_inventory.get(Resource.IronOre, 0)}"

print("Successfully gathered all required resources!")

"""
Step 3: Craft and set up the furnace
- Craft a stone furnace
- Place the furnace
- Add coal to the furnace as fuel
"""
# Craft a stone furnace
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted {crafted_furnaces} Stone Furnace(s)")

# Check if crafting was successful
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.StoneFurnace, 0) >= 1, \
    f"Failed to craft Stone Furnace. Expected at least 1, but got {current_inventory.get(Prototype.StoneFurnace, 0)}"
print("Successfully crafted Stone Furnace")

# Place the stone furnace
placed_furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
print(f"Placed Stone Furnace at {placed_furnace.position}")

# Add coal to the furnace as fuel
coal_in_inventory = current_inventory.get(Prototype.Coal, 0)
print(f"Coal available in inventory: {coal_in_inventory}")
assert coal_in_inventory >= 1, f"Insufficient coal in inventory. Expected at least 1 but found {coal_in_inventory}"

updated_furnace = insert_item(Prototype.Coal, placed_furnace, quantity=1)
print("Inserted coal into the Stone Furnace")

# Verify that the coal was inserted
coal_in_furnace = updated_furnace.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace >= 1, f"Failed to insert coal into Stone Furnace. Expected at least 1 but found {coal_in_furnace}"
print("Successfully set up the Stone Furnace with fuel")

# Final inspection of entity status
inspection_results = inspect_entities(position=placed_furnace.position)
furnace_status = inspection_results.entities[0].status
print(f"Stone Furnace status after setup: {furnace_status}")

"""
Step 4: Smelt iron plates
- Place iron ore in the furnace
- Wait for the smelting process to complete
- Extract iron plates from the furnace
"""
# Check current inventory for iron ore
current_inventory = inspect_inventory()
iron_ore_in_inventory = current_inventory.get(Prototype.IronOre, 0)
print(f"Iron Ore available in inventory: {iron_ore_in_inventory}")
assert iron_ore_in_inventory >= 7, f"Insufficient Iron Ore in inventory. Expected at least 7 but found {iron_ore_in_inventory}"

# Insert Iron Ore into the Furnace
updated_furnace = insert_item(Prototype.IronOre, placed_furnace, quantity=7)
print("Inserted Iron Ore into the Stone Furnace")

# Wait for smelting process to complete
smelting_time_per_unit = 0.7  # Assuming it takes 0.7 seconds per unit to smelt
total_smelting_time = int(smelting_time_per_unit * 7)
sleep(total_smelting_time)

# Attempt to extract Iron Plates multiple times if needed
max_attempts_to_extract = 5
for attempt in range(max_attempts_to_extract):
    # Extract Iron Plates from the Furnace
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=7)

    # Check how many Iron Plates are now in inventory
    current_inventory = inspect_inventory()
    iron_plates_in_inventory = current_inventory.get(Prototype.IronPlate, 0)
    print(f"Attempt {attempt + 1}: Extracted Iron Plates; Current Inventory Count: {iron_plates_in_inventory}")

    if iron_plates_in_inventory >= 7:
        break

    sleep(10)  # Wait a bit before trying again if not all plates were extracted

# Final assertion check
assert iron_plates_in_inventory >= 7, f"Failed to produce required number of Iron Plates. Expected at least 7 but found {iron_plates_in_inventory}"
print("Successfully produced required number of Iron Plates!")

"""
Step 5: Craft intermediate products
- Craft 1 burner inserter (requires 1 iron gear wheel, 1 iron plate)
"""
# Check current inventory for required materials
current_inventory = inspect_inventory()
iron_plates_in_inventory = current_inventory.get(Prototype.IronPlate, 0)
print(f"Iron Plates available in inventory: {iron_plates_in_inventory}")
assert iron_plates_in_inventory >= 7, f"Insufficient Iron Plates in inventory. Expected at least 7 but found {iron_plates_in_inventory}"

# Craft Iron Gear Wheel first as it's needed for Burner Inserter
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=1)
print(f"Crafted {crafted_gear_wheels} Iron Gear Wheel(s)")

# Craft Burner Inserter
crafted_burner_inserters = craft_item(Prototype.BurnerInserter, quantity=1)
print(f"Crafted {crafted_burner_inserters} Burner Inserter(s)")

# Verify that the Burner Inserter was crafted successfully
current_inventory = inspect_inventory()
burner_inserters_in_inventory = current_inventory.get(Prototype.BurnerInserter, 0)
assert burner_inserters_in_inventory >= 1, f"Failed to craft required number of Burner Inserters. Expected at least 1 but found {burner_inserters_in_inventory}"
print("Successfully crafted required number of Burner Inserters!")

"""
Step 6: Craft underground-belt
- Craft 2 underground-belts (requires 10 iron gear wheels, 1 transport belt each)
"""
# Calculate total iron plates needed
total_iron_plates_needed = 10 * 2 + 1 * 2  # 10 iron gear wheels, 1 transport belt each

# Check current inventory for required materials
current_inventory = inspect_inventory()
iron_plates_in_inventory = current_inventory.get(Prototype.IronPlate, 0)
print(f"Iron Plates available in inventory: {iron_plates_in_inventory}")
assert iron_plates_in_inventory >= total_iron_plates_needed, \
    f"Insufficient Iron Plates in inventory. Expected at least {total_iron_plates_needed} but found {iron_plates_in_inventory}"

# Craft Iron Gear Wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=20)
print(f"Crafted {crafted_gear_wheels} Iron Gear Wheel(s)")

# Craft Transport Belts
crafted_transport_belts = craft_item(Prototype.TransportBelt, quantity=2)
print(f"Crafted {crafted_transport_belts} Transport Belt(s)")

# Craft Underground Belts
crafted_underground_belts = craft_item(Prototype.UndergroundBelt, quantity=2)
print(f"Crafted {crafted_underground_belts} Underground Belt(s)")

# Verify that the Underground Belts were crafted successfully
current_inventory = inspect_inventory()
underground_belts_in_inventory = current_inventory.get(Prototype.UndergroundBelt, 0)
assert underground_belts_in_inventory >= 2, \
    f"Failed to craft required number of Underground Belts. Expected at least 2 but found {underground_belts_in_inventory}"
print("Successfully crafted required number of Underground Belts!")

"""
Step 7: Craft fast-underground-belt
- Craft 1 fast-underground-belt (requires 2 iron gear wheels, 1 underground belt)
"""
# Check current inventory for required materials
current_inventory = inspect_inventory()
iron_plates_in_inventory = current_inventory.get(Prototype.IronPlate, 0)
underground_belts_in_inventory = current_inventory.get(Prototype.UndergroundBelt, 0)
print(f"Iron Plates available in inventory: {iron_plates_in_inventory}")
print(f"Underground Belts available in inventory: {underground_belts_in_inventory}")

# Craft Iron Gear Wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=2)
print(f"Crafted {crafted_gear_wheels} Iron Gear Wheel(s)")

# Craft Fast Underground Belt
crafted_fast_underground_belts = craft_item(Prototype.FastUndergroundBelt, quantity=1)
print(f"Crafted {crafted_fast_underground_belts} Fast Underground Belt(s)")

# Verify that the Fast Underground Belt was crafted successfully
current_inventory = inspect_inventory()
fast_underground_belts_in_inventory = current_inventory.get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belts_in_inventory >= 1, \
    f"Failed to craft required number of Fast Underground Belts. Expected at least 1 but found {fast_underground_belts_in_inventory}"
print("Successfully crafted required number of Fast Underground Belts!")

"""
Step 8: Verify the crafted items
- Check the inventory for the crafted items
"""
# Check current inventory for crafted items
current_inventory = inspect_inventory()
print(f"Current Inventory: {current_inventory}")

# Verify that all required items are in the inventory
assert current_inventory.get(Prototype.BurnerInserter, 0) >= 1, \
    f"Missing Burner Inserters. Expected at least 1 but found {current_inventory.get(Prototype.BurnerInserter, 0)}"
assert current_inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, \
    f"Missing Fast Underground Belts. Expected at least 1 but found {current_inventory.get(Prototype.FastUndergroundBelt, 0)}"

print("All required items are present in the inventory!")

# Print final inventory
final_inventory = inspect_inventory()
print(f"Final inventory after completing all steps: {final_inventory}")

