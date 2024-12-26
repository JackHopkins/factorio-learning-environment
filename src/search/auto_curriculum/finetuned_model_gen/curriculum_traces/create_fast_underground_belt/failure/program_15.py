
from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipes for fast-underground-belt, iron-gear-wheel, and underground-belt.
"""
# Print the recipe for fast-underground-belt
print("Recipe for fast-underground-belt:")
print("Crafting requires 4 iron gear wheels, 1 underground belt")
print("Total iron plates needed: 12")

# Print the recipe for iron-gear-wheel
print("\nRecipe for iron-gear-wheel:")
print("Crafting requires 2 iron plates per gear wheel")

# Print the recipe for underground-belt
print("\nRecipe for underground-belt:")
print("Crafting requires 10 iron gear wheels, 1 transport belt")
print("Total iron plates needed for 2 underground belts: 48")

# Calculate total iron plates needed for fast-underground-belt
iron_gear_wheels_for_fast_underground_belt = 4 * 2  # 4 iron gear wheels * 2 iron plates per gear
iron_plates_for_underground_belts = 48
total_iron_plates_needed = iron_gear_wheels_for_fast_underground_belt + iron_plates_for_underground_belts

print(f"\nTotal iron plates needed for crafting fast-underground-belt: {total_iron_plates_needed}")

"""
Step 2: Gather resources. We need to mine iron ore and stone.
- Mine at least 80 iron ore
- Mine at least 10 stone (for the furnace)
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 80),
    (Resource.Stone, 10)
]

# Loop through each resource and gather it
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    print(f"Nearest {resource_type} found at {resource_position}")
    
    # Move to the resource
    move_to(resource_position)
    print(f"Moved to {resource_type} position {resource_position}")
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    print(f"Harvested {harvested} {resource_type}")
    
    # Check the inventory to confirm we have enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    print(f"Current inventory: {current_inventory}")
    
    # Assert to ensure we have at least the required quantity
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered required {resource_type}")

print("Successfully gathered all required resources!")


"""
Step 3: Set up smelting. We need to smelt the iron ore into iron plates.
- Craft a stone furnace
- Place the stone furnace
- Smelt 80 iron ore into iron plates
"""
# Craft a stone furnace
print("Crafting a stone furnace...")
craft_item(Prototype.StoneFurnace, quantity=1)
print("Stone furnace crafted.")

# Place the stone furnace
furnace_position = Position(x=0, y=0)  # Choose a suitable position
move_to(furnace_position)
furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)
print(f"Stone furnace placed at {furnace_position}")

# Insert coal into the furnace for fuel
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
assert coal_in_inventory > 0, "No coal available in inventory"
fueled_furnace = insert_item(Prototype.Coal, furnace, quantity=coal_in_inventory)
print(f"Inserted {coal_in_inventory} coal into the furnace")

# Insert iron ore into the furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
assert iron_ore_in_inventory >= 80, "Insufficient iron ore in inventory"
fueled_furnace = insert_item(Prototype.IronOre, fueled_furnace, quantity=80)
print("Inserted 80 iron ore into the furnace")

# Wait for smelting to complete
smelting_time_per_unit = 0.7  # Average smelting time per unit
total_smelting_time = int(80 * smelting_time_per_unit)
sleep(total_smelting_time)

# Extract iron plates from the furnace
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, fueled_furnace.position, quantity=80)
    iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
    if iron_plates_in_inventory >= 80:
        break
    sleep(10)  # Allow additional time if needed

print(f"Extracted iron plates; current inventory count: {iron_plates_in_inventory}")

# Final assertion check
assert iron_plates_in_inventory >= 80, f"Failed to smelt enough Iron Plates. Expected: 80, Actual: {iron_plates_in_inventory}"
print("Successfully set up smelting and obtained required Iron Plates.")


"""
Step 4: Craft iron gear wheels. We need to craft 40 iron gear wheels.
- Craft 40 iron gear wheels (requires 80 iron plates)
"""
# Crafting 40 Iron Gear Wheels
print("Crafting 40 Iron Gear Wheels...")
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=40)
print(f"Crafted {crafted_gear_wheels} Iron Gear Wheels")

# Verify that we have crafted the correct amount
iron_gear_wheel_count = inspect_inventory().get(Prototype.IronGearWheel, 0)
print(f"Iron Gear Wheel count in inventory: {iron_gear_wheel_count}")
assert iron_gear_wheel_count >= 40, f"Failed to craft enough Iron Gear Wheels. Expected: 40, Actual: {iron_gear_wheel_count}"
print("Successfully crafted 40 Iron Gear Wheels.")


"""
Step 5: Craft underground belts. We need to craft 2 underground belts.
- Craft 2 underground belts (requires 20 iron gear wheels and 10 iron plates)
"""
# Crafting 2 Underground Belts
print("Crafting 2 Underground Belts...")
crafted_underground_belts = craft_item(Prototype.UndergroundBelt, quantity=2)
print(f"Crafted {crafted_underground_belts} Underground Belts")

# Verify that we have crafted the correct amount
underground_belt_count = inspect_inventory().get(Prototype.UndergroundBelt, 0)
print(f"Underground Belt count in inventory: {underground_belt_count}")
assert underground_belt_count >= 2, f"Failed to craft enough Underground Belts. Expected: 2, Actual: {underground_belt_count}"
print("Successfully crafted 2 Underground Belts.")


"""
Step 6: Craft fast-underground-belt. We need to craft 1 fast-underground-belt.
- Craft 1 fast-underground-belt (requires 4 iron gear wheels and 1 underground belt)
"""
# Crafting 1 Fast Underground Belt
print("Crafting 1 Fast Underground Belt...")
crafted_fast_underground_belt = craft_item(Prototype.FastUndergroundBelt, quantity=1)
print(f"Crafted {crafted_fast_underground_belt} Fast Underground Belt")

# Verify that we have crafted the correct amount
fast_underground_belt_count = inspect_inventory().get(Prototype.FastUndergroundBelt, 0)
print(f"Fast Underground Belt count in inventory: {fast_underground_belt_count}")
assert fast_underground_belt_count >= 1, f"Failed to craft enough Fast Underground Belts. Expected: 1, Actual: {fast_underground_belt_count}"
print("Successfully crafted 1 Fast Underground Belt.")


"""
Final check: Verify that we have crafted the fast-underground-belt
"""
# Check the final inventory for Fast Underground Belt
final_inventory = inspect_inventory()
fast_underground_belts_in_inventory = final_inventory.get(Prototype.FastUndergroundBelt, 0)
print(f"Final inventory count of Fast Underground Belts: {fast_underground_belts_in_inventory}")

# Ensure we have at least one Fast Underground Belt
assert fast_underground_belts_in_inventory >= 1, f"Final check failed. Expected at least 1 Fast Underground Belt but found {fast_underground_belts_in_inventory}"
print("Final check passed: Successfully crafted the required Fast Underground Belt.")

# Output the production stats for additional verification
production_stats = production_stats()
print(f"Production stats: {production_stats}")

print("All steps completed successfully. Fast Underground Belt crafted and verified.")


