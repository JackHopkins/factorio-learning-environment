

from instance import *

"""
Objective: Set up initial iron plate production

Planning:
We need to set up a burner mining drill to mine iron ore and a furnace to smelt it into iron plates.
Since we have no entities on the map or in our inventory, we need to craft everything from scratch.
We'll need to gather resources, craft intermediate items, and then set up the production line.
"""

"""
Step 1: Print recipes
We need to print the recipes for burner mining drill and stone furnace
"""
# Print recipe for burner mining drill
print("Burner Mining Drill Recipe:")
print("3 iron gear wheels")
print("3 iron plates")
print("1 stone furnace")

# Print recipe for stone furnace
print("Stone Furnace Recipe:")
print("5 stone")

"""
Step 2: Gather raw resources
- Mine iron ore (at least 3 for gears)
- Mine stone (at least 5 for furnace)
- Mine coal (at least 10 for fuel)
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 3),
    (Resource.Stone, 5),
    (Resource.Coal, 10)
]

# Loop through each resource type and amount
for resource_type, required_amount in resources_to_gather:
    # Get the nearest position of the current resource type
    resource_position = nearest(resource_type)
    # Move to the resource position
    move_to(resource_position)
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_amount)
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_amount = current_inventory.get(resource_type, 0)
    assert actual_amount >= required_amount, f"Failed to gather enough {resource_type}. Required: {required_amount}, Actual: {actual_amount}"
    print(f"Successfully gathered {actual_amount} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")

# Assert that we have at least the required amounts
assert final_inventory.get(Resource.IronOre, 0) >= 3, "Not enough Iron Ore"
assert final_inventory.get(Resource.Stone, 0) >= 5, "Not enough Stone"
assert final_inventory.get(Resource.Coal, 0) >= 10, "Not enough Coal"

print("Successfully gathered all required resources!")

"""
Step 3: Craft intermediate items
- Craft stone furnace
- Smelt iron plates (using a temporary furnace)
- Craft iron gear wheels
"""
# Step 3.1: Craft stone furnace
print("Crafting stone furnace...")
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 stone furnace")

# Step 3.2: Smelt iron plates
print("Smelting iron plates...")
# Place a temporary furnace
player_position = inspect_entities().player_position
temp_furnace = place_entity(Prototype.StoneFurnace, position=Position(x=player_position[0] + 2, y=player_position[1]))
# Insert coal as fuel
insert_item(Prototype.Coal, temp_furnace, quantity=5)
# Insert iron ore
insert_item(Prototype.IronOre, temp_furnace, quantity=3)
# Wait for smelting
sleep(5)
# Extract iron plates
extract_item(Prototype.IronPlate, temp_furnace.position, quantity=3)
# Verify iron plates
iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
assert iron_plates >= 3, f"Failed to smelt enough Iron Plates. Expected at least 3, got {iron_plates}"
print(f"Successfully smelted {iron_plates} Iron Plates")

# Step 3.3: Craft iron gear wheels
print("Crafting iron gear wheels...")
craft_item(Prototype.IronGearWheel, quantity=3)
print("Crafted 3 Iron Gear Wheels")

# Verify iron gear wheels
iron_gear_wheels = inspect_inventory().get(Prototype.IronGearWheel, 0)
assert iron_gear_wheels >= 3, f"Failed to craft enough Iron Gear Wheels. Expected at least 3, got {iron_gear_wheels}"

print("Successfully crafted all intermediate items!")

"""
Step 4: Craft burner mining drill and stone furnace
- Craft burner mining drill (requires 1 iron gear wheel, 3 iron plates, 1 stone furnace)
- Craft an additional stone furnace
"""
# Step 4.1: Craft burner mining drill
print("Crafting burner mining drill...")
craft_item(Prototype.BurnerMiningDrill, quantity=1)
print("Crafted 1 Burner Mining Drill")

# Verify burner mining drill
burner_mining_drill = inspect_inventory().get(Prototype.BurnerMiningDrill, 0)
assert burner_mining_drill >= 1, f"Failed to craft Burner Mining Drill. Expected at least 1, got {burner_mining_drill}"

# Step 4.2: Craft an additional stone furnace
print("Crafting an additional stone furnace...")
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 additional Stone Furnace")

# Verify additional stone furnace
stone_furnace = inspect_inventory().get(Prototype.StoneFurnace, 0)
assert stone_furnace >= 1, f"Failed to craft additional Stone Furnace. Expected at least 1, got {stone_furnace}"

print("Successfully crafted all required entities!")

"""
Step 5: Set up the mining and smelting operation
- Place burner mining drill on iron ore patch
- Fuel the drill with coal
- Place stone furnace next to drill's output
- Connect drill to furnace using a burner inserter
"""
# Step 5.1: Place burner mining drill on iron ore patch
print("Placing burner mining drill...")
iron_ore_position = get_resource_patch(Resource.IronOre, nearest(Resource.IronOre))
move_to(iron_ore_position.bounding_box.center)
drill = place_entity(Prototype.BurnerMiningDrill, direction=Direction.UP, position=iron_ore_position.bounding_box.center)
print(f"Placed Burner Mining Drill at {drill.position}")

# Step 5.2: Fuel the burner mining drill with coal
print("Fueling burner mining drill...")
fueled_drill = insert_item(Prototype.Coal, drill, quantity=5)
coal_in_drill = fueled_drill.fuel.get(Prototype.Coal, 0)
assert coal_in_drill > 0, "Failed to fuel Burner Mining Drill"
print("Burner Mining Drill successfully fueled")

# Step 5.3: Place stone furnace next to drill's output
print("Placing stone furnace...")
# Calculate position for the furnace (next to the drill's drop position)
furnace_position = Position(x=drill.drop_position.x + 1, y=drill.drop_position.y)
move_to(furnace_position)
furnace = place_entity(Prototype.StoneFurnace, direction=Direction.UP, position=furnace_position)
print(f"Placed Stone Furnace at {furnace.position}")

# Step 5.4: Connect drill to furnace using a burner inserter
print("Connecting drill to furnace with burner inserter...")
inserter = place_entity(Prototype.BurnerInserter, direction=Direction.RIGHT, position=drill.drop_position)
# Rotate the inserter to face the furnace
inserter = rotate_entity(inserter, direction=Direction.LEFT)
print("Inserter placed and rotated")

# Fuel the inserter
inserter = insert_item(Prototype.Coal, inserter, quantity=5)
coal_in_inserter = inserter.fuel.get(Prototype.Coal, 0)
assert coal_in_inserter > 0, "Failed to fuel Inserter"
print("Inserter successfully fueled")

# Connect entities
connect_entities(drill.drop_position, inserter.pickup_position, Prototype.TransportBelt)
connect_entities(inserter.drop_position, furnace.position, Prototype.TransportBelt)
print("Drill connected to Furnace")

print("Mining and smelting operation set up successfully!")

"""
Step 6: Start iron plate production
- Wait for the furnace to smelt 10 iron ore into iron plates
- Extract the iron plates from the furnace
"""
# Step 6.1: Wait for iron plates to be produced
print("Waiting for iron plates to be produced...")
initial_iron_plate_count = inspect_inventory(furnace).get(Prototype.IronPlate, 0)

max_wait_time = 60  # Maximum time to wait in seconds
check_interval = 10  # Time between checks in seconds

for _ in range(0, max_wait_time, check_interval):
    sleep(check_interval)
    current_iron_plate_count = inspect_inventory(furnace).get(Prototype.IronPlate, 0)
    print(f"Current iron plate count: {current_iron_plate_count}")
    if current_iron_plate_count >= initial_iron_plate_count + 10:
        break

final_iron_plate_count = inspect_inventory(furnace).get(Prototype.IronPlate, 0)
print(f"Final iron plate count in furnace: {final_iron_plate_count}")

# Step 6.2: Extract iron plates from the furnace
print("Extracting iron plates from the furnace...")
extract_item(Prototype.IronPlate, furnace.position, quantity=10)

# Verify extraction
inventory_after_extraction = inspect_inventory()
extracted_iron_plates = inventory_after_extraction.get(Prototype.IronPlate, 0)
assert extracted_iron_plates >= 10, f"Failed to extract required number of Iron Plates. Expected at least 10, got {extracted_iron_plates}"
print(f"Successfully extracted {extracted_iron_plates} Iron Plates")

print("Iron plate production setup completed successfully!")

