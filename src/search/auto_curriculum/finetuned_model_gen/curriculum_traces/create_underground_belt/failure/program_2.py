
from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipe for underground belt, transport belt, iron gear wheel, and stone furnace
"""
# Print recipe for underground-belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print(f"underground-belt Recipe: {underground_belt_recipe}")

# Print recipe for transport-belt
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
print(f"transport-belt Recipe: {transport_belt_recipe}")

# Print recipe for iron-gear-wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(f"iron-gear-wheel Recipe: {iron_gear_wheel_recipe}")

# Print recipe for stone-furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"stone-furnace Recipe: {stone_furnace_recipe}")

"""
Step 2: Gather resources. We need to mine the following resources:
- 29 iron ore (21 for iron plates, 8 for iron gear wheels)
- 12 stone (for 2 stone furnaces)
- 2 coal (for fuel)
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 29),
    (Resource.Stone, 12),
    (Resource.Coal, 2)
]

# Loop through each resource we need to gather
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    print(f"Nearest {resource_type} found at: {resource_position}")

    # Move to the resource
    move_to(resource_position)
    print(f"Moved to {resource_type} patch at: {resource_position}")

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
print(f"Final inventory: {final_inventory}")

# Verify that we have gathered all required resources
for resource_type, required_quantity in resources_to_gather:
    actual_quantity = final_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Final check failed for {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"

print("Successfully gathered all required resources!")

"""
Step 3: Craft stone furnaces. We need to craft 2 stone furnaces.
"""
# Craft two stone furnaces
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=2)
print(f"Crafted {crafted_furnaces} Stone Furnaces")

# Check if we crafted the correct number of furnaces
inventory_after_crafting = inspect_inventory()
assert inventory_after_crafting.get(Prototype.StoneFurnace, 0) >= 2, "Failed to craft required number of Stone Furnaces"

print("Successfully crafted required number of Stone Furnaces")

"""
Step 4: Place and fuel furnaces. We need to:
- Place two stone furnaces
- Fuel both furnaces with coal
"""
# Place the first stone furnace
furnace1 = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
print(f"Placed first Stone Furnace at {furnace1.position}")

# Place the second stone furnace
furnace2 = place_entity(Prototype.StoneFurnace, position=Position(x=2, y=0))
print(f"Placed second Stone Furnace at {furnace2.position}")

# Fuel the first furnace with coal
fueled_furnace1 = insert_item(Prototype.Coal, furnace1, quantity=1)
print(f"Inserted coal into the first Stone Furnace")

# Fuel the second furnace with coal
fueled_furnace2 = insert_item(Prototype.Coal, furnace2, quantity=1)
print(f"Inserted coal into the second Stone Furnace")

# Check if both furnaces have been fueled
assert fueled_furnace1.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel the first Stone Furnace"
assert fueled_furnace2.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel the second Stone Furnace"

print("Successfully placed and fueled two Stone Furnaces")

"""
Step 5: Smelt iron plates. We need to:
- Smelt 21 iron ore into iron plates in one furnace
- Smelt 8 iron ore into iron plates in the other furnace
"""
# Split iron ore between the two furnaces
iron_ore_for_furnace1 = 21
iron_ore_for_furnace2 = 8

# Insert iron ore into the first furnace
updated_furnace1 = insert_item(Prototype.IronOre, fueled_furnace1, quantity=iron_ore_for_furnace1)
print(f"Inserted {iron_ore_for_furnace1} Iron Ore into the first Stone Furnace")

# Insert iron ore into the second furnace
updated_furnace2 = insert_item(Prototype.IronOre, fueled_furnace2, quantity=iron_ore_for_furnace2)
print(f"Inserted {iron_ore_for_furnace2} Iron Ore into the second Stone Furnace")

# Wait for smelting to complete; assume each unit takes about 0.7 seconds
smelting_time = max(iron_ore_for_furnace1, iron_ore_for_furnace2) * 0.7
sleep(smelting_time)

# Extract iron plates from both furnaces
extract_item(Prototype.IronPlate, updated_furnace1.position, quantity=iron_ore_for_furnace1)
extract_item(Prototype.IronPlate, updated_furnace2.position, quantity=iron_ore_for_furnace2)
print("Extracted Iron Plates from both Stone Furnaces")

# Verify that we have enough iron plates in our inventory
inventory_after_extraction = inspect_inventory()
total_iron_plates = inventory_after_extraction.get(Prototype.IronPlate, 0)
required_iron_plates = 21 + 8
assert total_iron_plates >= required_iron_plates, f"Failed to smelt required number of Iron Plates. Expected: {required_iron_plates}, Actual: {total_iron_plates}"

print(f"Successfully smelted {total_iron_plates} Iron Plates")

"""
Step 6: Craft transport belts. We need to craft 4 transport belts, which requires:
- 4 iron gear wheels (8 iron plates)
- 4 iron plates
"""
# Craft 4 iron gear wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=4)
print(f"Crafted {crafted_gear_wheels} Iron Gear Wheels")

# Craft 4 transport belts
crafted_transport_belts = craft_item(Prototype.TransportBelt, quantity=4)
print(f"Crafted {crafted_transport_belts} Transport Belts")

# Verify that we have crafted enough transport belts
inventory_after_crafting = inspect_inventory()
assert inventory_after_crafting.get(Prototype.TransportBelt, 0) >= 4, f"Failed to craft required number of Transport Belts. Expected: 4, Actual: {inventory_after_crafting.get(Prototype.TransportBelt, 0)}"

print("Successfully crafted required number of Transport Belts")

"""
Step 7: Craft iron gear wheels. We need to craft 7 iron gear wheels, which requires:
- 14 iron plates
"""
# Craft 7 iron gear wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=7)
print(f"Crafted {crafted_gear_wheels} Iron Gear Wheels")

# Verify that we have crafted enough gear wheels
inventory_after_crafting = inspect_inventory()
assert inventory_after_crafting.get(Prototype.IronGearWheel, 0) >= 7, f"Failed to craft required number of Iron Gear Wheels. Expected: 7, Actual: {inventory_after_crafting.get(Prototype.IronGearWheel, 0)}"

print("Successfully crafted required number of Iron Gear Wheels")

"""
Step 8: Craft underground belt. We need to craft 1 underground belt, which requires:
- 5 iron plates
- 10 iron gear wheels
- 2 transport belts
"""
# Craft 1 underground belt
crafted_underground_belts = craft_item(Prototype.UndergroundBelt, quantity=1)
print(f"Crafted {crafted_underground_belts} Underground Belt")

# Verify that we have crafted enough underground belts
inventory_after_crafting = inspect_inventory()
assert inventory_after_crafting.get(Prototype.UndergroundBelt, 0) >= 1, f"Failed to craft required number of Underground Belts. Expected: 1, Actual: {inventory_after_crafting.get(Prototype.UndergroundBelt, 0)}"

print("Successfully crafted required number of Underground Belts")

"""
Final step: Verify the result. We need to check if we have crafted at least 1 underground belt.
"""
# Final inventory check
final_inventory = inspect_inventory()
underground_belts_in_inventory = final_inventory.get(Prototype.UndergroundBelt, 0)
assert underground_belts_in_inventory >= 1, f"Final check failed for Underground Belts. Expected at least 1, but found {underground_belts_in_inventory}"
print(f"Successfully completed all steps! Final inventory: {final_inventory}")

