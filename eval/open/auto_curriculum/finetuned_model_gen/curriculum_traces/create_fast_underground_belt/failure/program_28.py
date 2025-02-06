

from instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- fast-underground-belt
- underground-belt
- iron-gear-wheel
"""
# Get recipes
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)

# Print recipes
print("fast-underground-belt recipe:", fast_underground_belt_recipe)
print("underground-belt recipe:", underground_belt_recipe)
print("iron-gear-wheel recipe:", iron_gear_wheel_recipe)

"""
Step 2: Gather resources. We need to gather:
- iron ore (at least 42)
- coal (at least 10 for fueling the furnace)
- stone (at least 5 for crafting a stone furnace)
"""
# Define required resources
required_resources = [
    (Resource.IronOre, 42),
    (Resource.Coal, 10),
    (Resource.Stone, 5)
]

# Gather each resource
for resource_type, required_quantity in required_resources:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory after gathering resources:")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")

# Assert that we have gathered at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 42, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 10, "Not enough Coal"
assert final_inventory.get(Resource.Stone, 0) >= 5, "Not enough Stone"

print("Successfully gathered all required resources.")

"""
Step 3: Craft and set up basic production infrastructure.
- Craft 1 stone furnace
- Place the stone furnace
"""
# Craft stone furnace
move_to(Position(x=0, y=0)) # Move to origin for crafting
stone_furnaces_crafted = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Stone furnaces crafted: {stone_furnaces_crafted}")

# Verify that we have crafted the stone furnace
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace, 0) >= 1, "Failed to craft stone furnace"

# Place stone furnace
placement_position = Position(x=2, y=2) # Example position
move_to(placement_position)
stone_furnace = place_entity(Prototype.StoneFurnace, position=placement_position)
print(f"Stone furnace placed at {stone_furnace.position}")

# Verify that the stone furnace has been placed
entities = get_entities({Prototype.StoneFurnace}, position=placement_position)
assert len(entities) > 0, "Failed to place stone furnace"

print("Successfully crafted and placed stone furnace.")

"""
Step 4: Smelt iron plates. We need to smelt at least 42 iron plates.
- Fuel the stone furnace with coal
- Smelt 42 iron ore into iron plates
"""
# Insert coal into stone furnace
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
assert coal_in_inventory >= 5, f"Not enough coal in inventory to fuel the furnace. Expected at least 5, found {coal_in_inventory}"

# Move to stone furnace position if needed
move_to(stone_furnace.position)
updated_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=5)
print("Inserted coal into stone furnace.")

# Insert iron ore into stone furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
assert iron_ore_in_inventory >= 42, f"Not enough iron ore in inventory to smelt. Expected at least 42, found {iron_ore_in_inventory}"
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=42)
print("Inserted iron ore into stone furnace.")

# Wait for smelting to complete
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * 42)
sleep(total_smelting_time)

# Extract iron plates from stone furnace
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=42)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= 42:
        break
    sleep(10)

print("Extracted iron plates from stone furnace.")

# Final inventory check
final_inventory_check = inspect_inventory()
print("Final inventory after smelting:")
print(f"Iron Plates: {final_inventory_check.get(Prototype.IronPlate, 0)}")
print(f"Coal: {final_inventory_check.get(Prototype.Coal, 0)}")
print(f"Stone: {final_inventory_check.get(Prototype.Stone, 0)}")

# Assert that we have smelted at least 42 iron plates
assert final_inventory_check.get(Prototype.IronPlate, 0) >= 42, "Failed to smelt required number of iron plates"
print("Successfully smelted required number of iron plates.")

"""
Step 5: Craft components. We need to craft:
- 2 underground-belts (each requires 5 iron gear wheels and 1 transport belt)
- 20 iron gear wheels (each requires 2 iron plates)
"""
# Crafting iron gear wheels
iron_gear_wheels_to_craft = 20
print(f"Crafting {iron_gear_wheels_to_craft} iron gear wheels...")
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=iron_gear_wheels_to_craft)
print(f"Crafted {crafted_gear_wheels} iron gear wheels")

# Verify that we have crafted the required number of iron gear wheels
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronGearWheel, 0) >= iron_gear_wheels_to_craft, f"Failed to craft required number of iron gear wheels. Expected: {iron_gear_wheels_to_craft}, Actual: {current_inventory.get(Prototype.IronGearWheel, 0)}"

# Crafting transport belts
transport_belts_to_craft = 2 # Each underground-belt requires 1 transport belt
print(f"Crafting {transport_belts_to_craft} transport belts...")
crafted_transport_belts = craft_item(Prototype.TransportBelt, quantity=transport_belts_to_craft)
print(f"Crafted {crafted_transport_belts} transport belts")

# Verify that we have crafted the required number of transport belts
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.TransportBelt, 0) >= transport_belts_to_craft, f"Failed to craft required number of transport belts. Expected: {transport_belts_to_craft}, Actual: {current_inventory.get(Prototype.TransportBelt, 0)}"

# Crafting underground belts
underground_belts_to_craft = 2
print(f"Crafting {underground_belts_to_craft} underground belts...")
crafted_underground_belts = craft_item(Prototype.UndergroundBelt, quantity=underground_belts_to_craft)
print(f"Crafted {crafted_underground_belts} underground belts")

# Verify that we have crafted the required number of underground belts
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.UndergroundBelt, 0) >= underground_belts_to_craft, f"Failed to craft required number of underground belts. Expected: {underground_belts_to_craft}, Actual: {current_inventory.get(Prototype.UndergroundBelt, 0)}"

print("Successfully crafted all required components.")

"""
Step 6: Craft the fast-underground-belt.
- Craft 1 fast-underground-belt (requires 2 underground-belts and 20 iron gear wheels)
"""
# Crafting fast underground belt
fast_underground_belts_to_craft = 1
print(f"Crafting {fast_underground_belts_to_craft} fast underground belts...")
crafted_fast_underground_belts = craft_item(Prototype.FastUndergroundBelt, quantity=fast_underground_belts_to_craft)
print(f"Crafted {crafted_fast_underground_belts} fast underground belts")

# Verify that we have crafted the required number of fast underground belts
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.FastUndergroundBelt, 0) >= fast_underground_belts_to_craft, f"Failed to craft required number of fast underground belts. Expected: {fast_underground_belts_to_craft}, Actual: {current_inventory.get(Prototype.FastUndergroundBelt, 0)}"

print("Successfully crafted the fast-underground-belt.")

"""Final verification step:
- Check the inventory to verify that we have crafted 1 fast-underground-belt
"""
# Check inventory for fast-underground-belt
current_inventory = inspect_inventory()
fast_underground_belt_count = current_inventory.get(Prototype.FastUndergroundBelt, 0)

# Assert that we have at least one fast-underground-belt
assert fast_underground_belt_count >= 1, f"Failed to craft required number of fast-underground-belts. Expected at least 1, but found {fast_underground_belt_count}"

print(f"Successfully crafted fast-underground-belt. Count in inventory: {fast_underground_belt_count}")

