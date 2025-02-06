
from instance import *

"""
Step 1: Print recipes. We need to craft a fast-transport-belt.
For this, we need to craft a transport-belt first.
We also need to craft a stone-furnace to smelt iron plates.
We need to gather iron ore, coal, and stone for crafting.
"""
# Print recipes
print("Recipes:")
print("Transport Belt: 1 iron gear wheel, 1 iron plate")
print("Fast Transport Belt: 2 transport belts, 4 iron gear wheels")

# Get recipe for stone furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace recipe: {stone_furnace_recipe}")

"""
Step 2: Gather resources
- Mine iron ore (at least 3 for 3 iron plates)
- Mine coal (at least 1 for fueling the furnace)
- Mine stone (at least 6 for crafting a stone furnace)
"""
# Define resources to gather
resources_to_gather = [
    (Resource.IronOre, 3),
    (Resource.Coal, 1),
    (Resource.Stone, 6)
]

# Gather resources
for resource_type, required_quantity in resources_to_gather:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)

    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Verify gathered resources
final_inventory = inspect_inventory()
print("Final inventory after gathering resources:")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")

# Final assertion to ensure all resources are gathered
assert all(final_inventory.get(resource, 0) >= quantity for resource, quantity in resources_to_gather), "Not all required resources were gathered"
print("Successfully gathered all required resources")

"""
Step 3: Craft stone furnace
- Craft 1 stone furnace using 5 stone
"""
# Craft stone furnace
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
assert crafted_furnaces == 1, f"Expected to craft 1 Stone Furnace but got {crafted_furnaces}"
print("Successfully crafted 1 Stone Furnace")

# Verify inventory after crafting
inventory_after_crafting = inspect_inventory()
print("Inventory after crafting Stone Furnace:")
print(f"Stone Furnaces: {inventory_after_crafting.get(Prototype.StoneFurnace, 0)}")

# Ensure we still have at least one stone left for the furnace
remaining_stone = inventory_after_crafting.get(Resource.Stone, 0)
assert remaining_stone >= 1, f"Expected at least 1 Stone remaining but got {remaining_stone}"
print(f"Remaining Stone: {remaining_stone}")

# Check that all other required resources are still in inventory
iron_ore_count = inventory_after_crafting.get(Resource.IronOre, 0)
coal_count = inventory_after_crafting.get(Resource.Coal, 0)

assert iron_ore_count >= 3, f"Expected at least 3 Iron Ore but got {iron_ore_count}"
assert coal_count >= 1, f"Expected at least 1 Coal but got {coal_count}"
print("Successfully verified inventory after crafting Stone Furnace")

"""
Step 4: Set up smelting
- Place the stone furnace
- Fuel the furnace with coal
- Smelt iron ore into 3 iron plates
"""
# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)

# Fuel the furnace with coal
coal_count = inspect_inventory().get(Prototype.Coal, 0)
fueled_furnace = insert_item(Prototype.Coal, furnace, quantity=coal_count)

# Insert iron ore into the stone furnace
iron_ore_count = inspect_inventory().get(Prototype.IronOre, 0)
furnace_with_ore = insert_item(Prototype.IronOre, fueled_furnace, quantity=iron_ore_count)
print(f"Inserted {iron_ore_count} Iron Ore into the Stone Furnace")

# Wait for smelting to complete
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_count)
sleep(total_smelting_time)

# Extract iron plates from the furnace
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, furnace_with_ore.position, quantity=iron_ore_count)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= 3:
        break
    sleep(10)

assert current_iron_plate_count >= 3, f"Failed to obtain required number of Iron Plates; expected 3 but got {current_iron_plate_count}"
print(f"Successfully obtained {current_iron_plate_count} Iron Plates")

# Verify inventory after smelting
inventory_after_smelting = inspect_inventory()
iron_plate_count = inventory_after_smelting.get(Prototype.IronPlate, 0)
assert iron_plate_count >= 3, f"Expected at least 3 Iron Plates but got {iron_plate_count}"
print("Successfully verified inventory after smelting")

"""
Step 5: Craft transport-belt
- Craft 2 transport-belts (1 for fast-transport-belt, 1 for task requirement) using 2 iron gear wheels and 2 iron plates
"""
# Craft iron gear wheels
iron_plates_needed_for_gears = 2
iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
assert iron_plates_in_inventory >= iron_plates_needed_for_gears, f"Not enough iron plates to craft gear wheels: have {iron_plates_in_inventory}, need {iron_plates_needed_for_gears}"

crafted_gears = craft_item(Prototype.IronGearWheel, quantity=2)
assert crafted_gears == 2, f"Expected to craft 2 Iron Gear Wheels but got {crafted_gears}"
print("Successfully crafted 2 Iron Gear Wheels")

# Craft transport-belts
crafted_transport_belts = craft_item(Prototype.TransportBelt, quantity=2)
assert crafted_transport_belts == 2, f"Expected to craft 2 Transport Belts but got {crafted_transport_belts}"
print("Successfully crafted 2 Transport Belts")

# Verify inventory after crafting
inventory_after_crafting = inspect_inventory()
print("Inventory after crafting:")
print(f"Transport Belts: {inventory_after_crafting.get(Prototype.TransportBelt, 0)}")

transport_belt_count = inventory_after_crafting.get(Prototype.TransportBelt, 0)
assert transport_belt_count >= 2, f"Failed to craft required number of Transport Belts; expected at least 2 but got {transport_belt_count}"
print(f"Successfully obtained {transport_belt_count} Transport Belts")

"""
Step 6: Craft fast-transport-belt
- Craft 1 fast-transport-belt using 1 transport-belt and 2 iron gear wheels
"""
# Craft iron gear wheels
crafted_gears = craft_item(Prototype.IronGearWheel, quantity=2)
assert crafted_gears == 2, f"Expected to craft 2 Iron Gear Wheels but got {crafted_gears}"
print("Successfully crafted 2 Iron Gear Wheels")

# Craft fast-transport-belt
crafted_fast_transport_belt = craft_item(Prototype.FastTransportBelt, quantity=1)
assert crafted_fast_transport_belt == 1, f"Expected to craft 1 Fast Transport Belt but got {crafted_fast_transport_belt}"
print("Successfully crafted 1 Fast Transport Belt")

# Verify inventory after crafting
inventory_after_crafting = inspect_inventory()
print("Inventory after crafting:")
print(f"Fast Transport Belts: {inventory_after_crafting.get(Prototype.FastTransportBelt, 0)}")

fast_transport_belt_count = inventory_after_crafting.get(Prototype.FastTransportBelt, 0)
assert fast_transport_belt_count >= 1, f"Failed to craft required number of Fast Transport Belts; expected at least 1 but got {fast_transport_belt_count}"
print(f"Successfully obtained {fast_transport_belt_count} Fast Transport Belts")

print("Successfully completed all steps and crafted a Fast Transport Belt!")
