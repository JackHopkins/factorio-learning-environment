

from factorio_instance import *

"""
Step 1: Print recipes. We need to print out the following recipes:
- Underground-belt: Takes 2 transport belts and 1 iron gear wheel
- Transport-belt: Takes 1 iron gear wheel and 1 iron plate
- Iron gear wheel: Takes 2 iron plates
- Stone furnace: Takes 5 stone
"""
# Print recipes
print("Recipes needed:")
print("Underground-belt: 2 transport belts, 1 iron gear wheel")
print("Transport-belt: 1 iron gear wheel, 1 iron plate")
print("Iron gear wheel: 2 iron plates")
print("Stone furnace: 5 stone")

"""
Step 2: Gather resources. We need to gather the following resources:
- Mine at least 12 stone (5 for furnace, 7 extra for safety)
- Mine at least 21 iron ore (for 21 iron plates)
- Mine at least 2 coal (for fuel in the furnace)
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 12),
    (Resource.IronOre, 21),
    (Resource.Coal, 2)
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
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.Stone, 0) >= 12, "Not enough Stone"
assert final_inventory.get(Resource.IronOre, 0) >= 21, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Not enough Coal"

print("Successfully gathered all required resources!")

"""
Step 3: Craft stone furnace. We need to craft 1 stone furnace using 5 stone.
"""
# Craft the stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)

# Verify that we have crafted the stone furnace
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace, 0) >= 1, f"Failed to craft stone furnace. Current inventory: {inventory}"
print("Successfully crafted a stone furnace")

"""
Step 4: Set up smelting. We need to set up a smelting area by:
- Placing the stone furnace
- Adding coal to the furnace as fuel
"""
# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed stone furnace at {furnace.position}")

# Add coal to the furnace as fuel
coal_quantity = 2  # Use all available coal
updated_furnace = insert_item(Prototype.Coal, furnace, coal_quantity)
print("Inserted coal into the furnace")

# Verify that the furnace has coal
coal_in_furnace = updated_furnace.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace > 0, "Failed to add coal to the furnace"
print(f"Coal successfully added to the furnace. Current coal in furnace: {coal_in_furnace}")

print("Smelting area set up successfully!")

"""
Step 5: Smelt iron plates. We need to smelt 21 iron ore into 21 iron plates. This will take approximately 21 seconds.
"""
# Insert all available Iron Ore into the Furnace
iron_ore_quantity = 21
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, iron_ore_quantity)
print("Inserted Iron Ore into the Furnace")

# Wait for smelting to complete
smelting_time = iron_ore_quantity * 1  # Each unit takes 1 second
sleep(smelting_time)

# Extract Iron Plates from the Furnace
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, iron_ore_quantity)
    current_inventory = inspect_inventory()
    iron_plates_count = current_inventory.get(Prototype.IronPlate, 0)
    
    if iron_plates_count >= iron_ore_quantity:
        break
    
    sleep(10)  # Wait a bit more if not all plates are ready

print(f"Extracted Iron Plates; Current Inventory Count: {iron_plates_count}")

# Final assertion checks
assert iron_plates_count >= 21, f"Failed to obtain required number of Iron Plates; Expected: 21, Found: {iron_plates_count}"
print("Successfully smelted and obtained required number of Iron Plates!")

"""
Step 6: Craft basic components. We need to craft the following components:
- 7 iron gear wheels (each takes 2 iron plates, so 14 iron plates total)
"""
# Craft 7 Iron Gear Wheels
craft_item(Prototype.IronGearWheel, quantity=7)

# Verify that we have crafted the Iron Gear Wheels
inventory_after_crafting_gears = inspect_inventory()
iron_gear_wheels_count = inventory_after_crafting_gears.get(Prototype.IronGearWheel, 0)
assert iron_gear_wheels_count >= 7, f"Failed to craft required number of Iron Gear Wheels; Expected: 7, Found: {iron_gear_wheels_count}"

print(f"Successfully crafted {iron_gear_wheels_count} Iron Gear Wheels")

"""
Step 7: Craft transport belts. We need to craft 4 transport belts. Each transport belt takes 1 iron gear wheel and 1 iron plate, so we need 4 iron gear wheels and 4 iron plates in total.
"""
# Craft 4 Transport Belts
craft_item(Prototype.TransportBelt, quantity=4)

# Verify that we have crafted the Transport Belts
inventory_after_crafting_belts = inspect_inventory()
transport_belts_count = inventory_after_crafting_belts.get(Prototype.TransportBelt, 0)
assert transport_belts_count >= 4, f"Failed to craft required number of Transport Belts; Expected: 4, Found: {transport_belts_count}"

print(f"Successfully crafted {transport_belts_count} Transport Belts")

"""
Step 8: Craft underground-belt. We need to craft 1 underground-belt. This requires 2 transport belts and 1 iron gear wheel.
"""
# Craft 1 Underground Belt
craft_item(Prototype.UndergroundBelt, quantity=1)

# Verify that we have crafted the Underground Belt
inventory_after_crafting_underground = inspect_inventory()
underground_belts_count = inventory_after_crafting_underground.get(Prototype.UndergroundBelt, 0)
assert underground_belts_count >= 1, f"Failed to craft required number of Underground Belts; Expected: 1, Found: {underground_belts_count}"

print(f"Successfully crafted {underground_belts_count} Underground Belts")

"""
Step 9: Verify crafting. We need to verify that we have successfully crafted the underground-belt.
"""
# Check the final inventory to confirm we have crafted the underground-belt
final_inventory = inspect_inventory()
underground_belt_count = final_inventory.get(Prototype.UndergroundBelt, 0)
assert underground_belt_count >= 1, "Failed to craft the Underground Belt"

print("Successfully crafted an Underground Belt!")

"""
Additional verification: Check that we have crafted all the required items by comparing the final inventory with the required quantities.
"""
# Define the required quantities
required_quantities = {
    Prototype.TransportBelt: 4,
    Prototype.IronGearWheel: 7,
    Prototype.IronPlate: 21,
    Prototype.StoneFurnace: 1,
    Prototype.UndergroundBelt: 1
}

# Check each required item
for item, required_quantity in required_quantities.items():
    actual_quantity = final_inventory.get(item, 0)
    assert actual_quantity >= required_quantity, f"Failed to craft required number of {item}; Expected: {required_quantity}, Found: {actual_quantity}"
    print(f"Successfully verified {item}; Required: {required_quantity}, Found: {actual_quantity}")

print("Final verification complete: All required items have been crafted successfully!")

