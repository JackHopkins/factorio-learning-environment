
from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- burner-mining-drill
- transport-belt
- underground-belt
"""

# Get and print the recipe for burner-mining-drill
burner_mining_drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
print(f"burner-mining-drill Recipe: {burner_mining_drill_recipe}")

# Get and print the recipe for transport-belt
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
print(f"transport-belt Recipe: {transport_belt_recipe}")

# Get and print the recipe for underground-belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print(f"underground-belt Recipe: {underground_belt_recipe}")

"""
Step 2: Gather raw resources. We need to gather the following resources:
- 12 stone (for 2 stone furnaces)
- 25 iron ore (for iron plates)
- 2 coal (for smelting)
"""

# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 12),
    (Resource.IronOre, 25),
    (Resource.Coal, 2)
]

# Loop through each resource and gather them
for resource_type, required_amount in resources_to_gather:
    # Find the nearest position for this resource
    resource_position = nearest(resource_type)
    print(f"Nearest {resource_type} found at: {resource_position}")

    # Move to the resource
    move_to(resource_position)
    print(f"Moved to {resource_type} position")

    # Harvest the resource
    harvested_amount = harvest_resource(resource_position, required_amount)
    print(f"Harvested {harvested_amount} {resource_type}")

    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_amount_in_inventory = current_inventory.get(resource_type, 0)
    assert actual_amount_in_inventory >= required_amount, f"Failed to gather enough {resource_type}. Required: {required_amount}, Actual: {actual_amount_in_inventory}"

print("Successfully gathered all necessary resources.")
print(f"Final inventory: {inspect_inventory()}")

"""
Step 3: Craft stone furnaces. We need to craft 2 stone furnaces:
- 1 for the burner mining drill
- 1 for smelting
"""

# Craft 2 stone furnaces
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=2)
print(f"Crafted {crafted_furnaces} Stone Furnaces")

# Check inventory to confirm we have 2 stone furnaces
inventory = inspect_inventory()
stone_furnaces_in_inventory = inventory.get(Prototype.StoneFurnace, 0)
assert stone_furnaces_in_inventory >= 2, f"Failed to craft enough Stone Furnaces. Expected: 2, Actual: {stone_furnaces_in_inventory}"
print("Successfully crafted 2 Stone Furnaces")

"""
Step 4: Set up smelting. We need to set up a smelting area to produce iron plates:
- Place a stone furnace
- Fuel it with coal
- Smelt 25 iron ore into iron plates
"""

# Move to origin before placing
origin = Position(x=0, y=0)
move_to(origin)

# Place a Stone Furnace
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed a Stone Furnace at {furnace.position}")

# Insert coal into the furnace as fuel
coal_inserted = insert_item(Prototype.Coal, furnace, quantity=2)
updated_furnace = get_entity(Prototype.StoneFurnace, furnace.position)
coal_in_furnace = updated_furnace.fuel.get(Prototype.Coal, 0)
print(f"Inserted {coal_inserted} coal into the Stone Furnace")

# Insert iron ore into the furnace for smelting
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
iron_ore_inserted = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_inserted} iron ore into the Stone Furnace")

# Wait for smelting to complete (approximately 0.7 seconds per ore)
smelting_time = iron_ore_inserted * 0.7
sleep(smelting_time)

# Extract iron plates from the furnace
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_inserted)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= iron_ore_inserted:
        break
    sleep(5)  # Give more time if needed

print(f"Extracted {current_iron_plate_count} iron plates from the Stone Furnace")
print(f"Final inventory after smelting: {inspect_inventory()}")

"""
Step 5: Craft iron gear wheels. We need to craft 4 iron gear wheels:
- 3 for the burner mining drill
- 1 for the transport belt
"""

# Craft 4 iron gear wheels
crafted_gears = craft_item(Prototype.IronGearWheel, quantity=4)
print(f"Crafted {crafted_gears} Iron Gear Wheels")

# Check inventory to confirm we have 4 iron gear wheels
inventory = inspect_inventory()
gear_wheels_in_inventory = inventory.get(Prototype.IronGearWheel, 0)
assert gear_wheels_in_inventory >= 4, f"Failed to craft enough Iron Gear Wheels. Expected: 4, Actual: {gear_wheels_in_inventory}"
print("Successfully crafted 4 Iron Gear Wheels")

"""
Step 6: Craft burner mining drill. We need to craft 1 burner mining drill using:
- 1 stone furnace
- 3 iron gear wheels
- 3 iron plates
"""

# Craft 1 burner mining drill
crafted_drill = craft_item(Prototype.BurnerMiningDrill, quantity=1)
print(f"Crafted {crafted_drill} Burner Mining Drill")

# Check inventory to confirm we have 1 burner mining drill
inventory = inspect_inventory()
drills_in_inventory = inventory.get(Prototype.BurnerMiningDrill, 0)
assert drills_in_inventory >= 1, f"Failed to craft Burner Mining Drill. Expected: 1, Actual: {drills_in_inventory}"
print("Successfully crafted 1 Burner Mining Drill")

"""
Step 7: Craft transport belt. We need to craft 7 transport belts using:
- 1 iron gear wheel
- 1 iron plate
(Note: This will actually produce 2 transport belts, but we need 12 in total for the task)
"""

# Craft 6 transport belts (3 crafting operations, each producing 2 belts)
crafted_belts = craft_item(Prototype.TransportBelt, quantity=6)
print(f"Crafted {crafted_belts} Transport Belts")

# Check inventory to confirm we have at least 12 transport belts
inventory = inspect_inventory()
belts_in_inventory = inventory.get(Prototype.TransportBelt, 0)
assert belts_in_inventory >= 12, f"Failed to craft enough Transport Belts. Expected: 12, Actual: {belts_in_inventory}"
print("Successfully crafted at least 12 Transport Belts")

"""
Step 8: Craft underground belt. We need to craft 1 underground belt using:
- 5 iron gear wheels
- 10 iron plates
(Note: This will actually produce 2 underground belts, but we only need 1 for the task)
"""

# Craft 1 underground belt
crafted_underground_belt = craft_item(Prototype.UndergroundBelt, quantity=1)
print(f"Crafted {crafted_underground_belt} Underground Belts")

# Check inventory to confirm we have at least 1 underground belt
inventory = inspect_inventory()
underground_belts_in_inventory = inventory.get(Prototype.UndergroundBelt, 0)
assert underground_belts_in_inventory >= 1, f"Failed to craft enough Underground Belts. Expected: 1, Actual: {underground_belts_in_inventory}"
print("Successfully crafted at least 1 Underground Belt")

"""
Step 9: Verify final inventory. We need to verify that we have crafted the correct items:
- 1 burner mining drill
- 12 transport belts
- 1 underground belt
"""

# Check inventory for burner mining drill
drills_in_inventory = inventory.get(Prototype.BurnerMiningDrill, 0)
assert drills_in_inventory >= 1, f"Failed to verify Burner Mining Drill. Expected: 1, Actual: {drills_in_inventory}"

# Check inventory for transport belts
belts_in_inventory = inventory.get(Prototype.TransportBelt, 0)
assert belts_in_inventory >= 12, f"Failed to verify Transport Belts. Expected: 12, Actual: {belts_in_inventory}"

# Check inventory for underground belts
underground_belts_in_inventory = inventory.get(Prototype.UndergroundBelt, 0)
assert underground_belts_in_inventory >= 1, f"Failed to verify Underground Belts. Expected: 1, Actual: {underground_belts_in_inventory}"

print("Successfully verified final inventory with all required items.")
print(f"Final inventory: {inspect_inventory()}")
