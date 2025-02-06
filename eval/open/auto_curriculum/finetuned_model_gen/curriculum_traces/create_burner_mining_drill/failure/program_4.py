

from instance import *

"""
Step 1: Gather raw resources
- Mine stone (need at least 5 for furnace)
- Mine iron ore (need at least 26 for iron plates)
- Mine coal (need at least 2 for fuel)
"""

# Define the resources we need to mine
resources_to_mine = [
    (Resource.Stone, 6),
    (Resource.IronOre, 26),
    (Resource.Coal, 2)
]

# Loop over each resource we need to mine
for resource_type, required_quantity in resources_to_mine:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    # Move to the resource
    move_to(resource_position)
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    # Get the current inventory
    current_inventory = inspect_inventory()
    # Check if we have harvested enough
    assert current_inventory.get(resource_type, 0) >= required_quantity, f"Failed to harvest enough {resource_type}. Required: {required_quantity}, Actual: {current_inventory.get(resource_type, 0)}"
    print(f"Successfully harvested {harvested} {resource_type}")

print("Successfully gathered all raw resources")

# Check final inventory
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Iron ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.Stone, 0) >= 6, "Not enough stone"
assert final_inventory.get(Resource.IronOre, 0) >= 26, "Not enough iron ore"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Not enough coal"

print("All required resources successfully gathered")


"""
Step 2: Craft stone furnace
- Craft 1 stone furnace (requires 5 stone)
"""

# Craft a stone furnace
crafted_furnaces = craft_item(Prototype.StoneFurnace, 1)
print(f"Crafted {crafted_furnaces} stone furnace(s)")

# Check the inventory for the stone furnace
inventory_after_crafting = inspect_inventory()
furnaces_in_inventory = inventory_after_crafting.get(Prototype.StoneFurnace, 0)
assert furnaces_in_inventory >= 1, f"Failed to craft stone furnace. Expected at least 1, but found {furnaces_in_inventory}"
print(f"Successfully crafted and verified {furnaces_in_inventory} stone furnace(s)")

# Verify that we have the necessary ingredients in our inventory
stone_in_inventory = inventory_after_crafting.get(Resource.Stone, 0)
assert stone_in_inventory >= 1, f"Insufficient stone in inventory. Expected at least 1, but found {stone_in_inventory}"
print(f"Sufficient stone in inventory: {stone_in_inventory}")

print("Stone furnace successfully crafted and verified")


"""
Step 3: Craft iron plates
- Place stone furnace
- Add coal as fuel to the furnace
- Smelt 26 iron ore to create 26 iron plates
"""

# Place the stone furnace at the origin
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed stone furnace at {origin}")

# Insert coal into the furnace as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=2)
print("Inserted coal into the furnace")

# Insert all available iron ore into the furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} iron ore into the furnace")

# Wait for the smelting process to complete
smelting_time = 0.7 * iron_ore_in_inventory  # 0.7 second per ore
sleep(smelting_time)

# Extract the iron plates
expected_iron_plates = 26
max_attempts = 5
for attempt in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=expected_iron_plates)
    iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
    if iron_plates_in_inventory >= expected_iron_plates:
        break
    sleep(10)  # Wait a bit more if needed
print(f"Extracted {iron_plates_in_inventory} iron plates")

# Verify that we have at least 26 iron plates
assert iron_plates_in_inventory >= expected_iron_plates, f"Failed to obtain required number of iron plates. Expected: {expected_iron_plates}, Actual: {iron_plates_in_inventory}"
print("Successfully obtained required number of iron plates")

# Check the final inventory state
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Iron plates: {final_inventory.get(Prototype.IronPlate, 0)}")
print(f"Remaining coal: {final_inventory.get(Prototype.Coal, 0)}")
print(f"Remaining iron ore: {final_inventory.get(Prototype.IronOre, 0)}")

# Assert that we have at least 26 iron plates
assert final_inventory.get(Prototype.IronPlate, 0) >= 26, "Not enough iron plates"
print("All required iron plates successfully obtained")


"""
Step 4: Craft intermediate items
- Craft 3 iron gear wheels (requires 6 iron plates)
- Craft 1 transport-belt (requires 1 iron gear wheel, 1 iron plate for 2)
- Craft 1 burner-inserter (requires 1 iron gear wheel, 2 iron plates)
- Craft 1 firearm-magazine (requires 4 iron plates)
"""

# Craft 3 iron gear wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, 3)
print(f"Crafted {crafted_gear_wheels} iron gear wheel(s)")

# Craft 4 transport-belts (requires 1 iron gear wheel, 1 iron plate for 2)
crafted_transport_belts = craft_item(Prototype.TransportBelt, 4)
print(f"Crafted {crafted_transport_belts} transport-belt(s)")

# Craft 1 burner-inserter (requires 1 iron gear wheel, 2 iron plates)
crafted_burner_inserter = craft_item(Prototype.BurnerInserter, 1)
print(f"Crafted {crafted_burner_inserter} burner-inserter(s)")

# Craft 1 firearm-magazine (requires 4 iron plates)
crafted_firearm_magazine = craft_item(Prototype.FirearmMagazine, 1)
print(f"Crafted {crafted_firearm_magazine} firearm-magazine(s)")

# Check the inventory for crafted items
inventory_after_crafting = inspect_inventory()

# Verify that we have crafted the required number of each item
assert inventory_after_crafting.get(Prototype.IronGearWheel, 0) >= 3, f"Failed to craft required number of iron gear wheels. Expected: 3, Actual: {inventory_after_crafting.get(Prototype.IronGearWheel, 0)}"
assert inventory_after_crafting.get(Prototype.TransportBelt, 0) >= 4, f"Failed to craft required number of transport-belts. Expected: 4, Actual: {inventory_after_crafting.get(Prototype.TransportBelt, 0)}"
assert inventory_after_crafting.get(Prototype.BurnerInserter, 0) >= 1, f"Failed to craft required number of burner-inserters. Expected: 1, Actual: {inventory_after_crafting.get(Prototype.BurnerInserter, 0)}"
assert inventory_after_crafting.get(Prototype.FirearmMagazine, 0) >= 1, f"Failed to craft required number of firearm-magazines. Expected: 1, Actual: {inventory_after_crafting.get(Prototype.FirearmMagazine, 0)}"

print("Successfully crafted all intermediate items")


"""
Step 5: Craft burner-mining-drill
- Craft 1 burner-mining-drill (requires 3 iron gear wheels, 3 iron plates, 1 stone furnace)
"""

# Craft 1 burner-mining-drill
crafted_drills = craft_item(Prototype.BurnerMiningDrill, 1)
print(f"Crafted {crafted_drills} burner-mining-drill(s)")

# Check the inventory for the crafted drill
inventory_after_crafting = inspect_inventory()
drills_in_inventory = inventory_after_crafting.get(Prototype.BurnerMiningDrill, 0)
assert drills_in_inventory >= 1, f"Failed to craft burner-mining-drill. Expected at least 1, but found {drills_in_inventory}"
print(f"Successfully crafted and verified {drills_in_inventory} burner-mining-drill(s)")

print("Burner-mining-drill successfully crafted and verified")
print("All steps completed successfully!")

