from factorio_instance import *

"""
Main Objective: We require one ElectricMiningDrill. The final success should be checked by looking if a ElectricMiningDrill is in inventory
"""



"""
Step 1: Gather raw resources
- Mine iron ore (at least 23)
- Mine copper ore (at least 5)
- Mine coal (at least 10 for fueling the furnace)
OUTPUT CHECK: Verify that we have at least 23 iron ore, 5 copper ore, and 10 coal in our inventory
"""
# Inventory at the start of step {}
#Step Execution

# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 23),
    (Resource.CopperOre, 5),
    (Resource.Coal, 10)
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
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Copper Ore: {final_inventory.get(Resource.CopperOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 23, "Not enough Iron Ore"
assert final_inventory.get(Resource.CopperOre, 0) >= 5, "Not enough Copper Ore"
assert final_inventory.get(Resource.Coal, 0) >= 10, "Not enough Coal"

print("Successfully gathered all required resources!")


"""
Step 2: Prepare the furnace for smelting
- Move to the stone furnace at position (-12.0, -12.0)
- Add coal to the furnace as fuel
OUTPUT CHECK: Verify that the furnace status is no longer 'no_fuel'
"""
# Inventory at the start of step {'coal': 10, 'iron-ore': 23, 'copper-ore': 5}
#Step Execution

# Step 2: Prepare the furnace for smelting

# Get the position of the stone furnace
furnace_position = Position(x=-12.0, y=-12.0)

# Move to the stone furnace's location
move_to(furnace_position)
print(f"Moved to stone furnace at {furnace_position}")

# Inspect current inventory for available coal
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
print(f"Coal available in inventory: {coal_in_inventory}")

# Ensure there is enough coal before proceeding (we expect at least 10 based on previous steps)
assert coal_in_inventory >= 10, f"Insufficient coal in inventory! Expected at least 10 but found {coal_in_inventory}"

# Retrieve all entities around us and find our target stove
entities_around = get_entities()
stone_furnaces = [entity for entity in entities_around if entity.name == Prototype.StoneFurnace.value[0]]
assert len(stone_furnaces) > 0, "No stone furnaces found nearby!"

stone_furnace = stone_furnaces[0]
print(f"Found a stone furnace at {stone_furnace.position} with status '{stone_furnace.status}'")

# Insert coal into the stone furnace as fuel
insert_item(Prototype.Coal, stone_furnace, quantity=coal_in_inventory)
print("Inserted coal into the stone furnace.")

# Re-inspect entities around us to check updated status of stove post-insertion
updated_stone_furnace_status = inspect_entities(position=furnace_position).get_entity(Prototype.StoneFurnace).status

# Check if stove's status has changed from 'no_fuel'
assert updated_stone_furnace_status != EntityStatus.NO_FUEL, "Failed to add fuel to the stove!"
print("Successfully added fuel; stove is now ready for smelting.")


"""
Step 3: Smelt iron plates
- Smelt 23 iron ore into iron plates
OUTPUT CHECK: Verify that we have 23 iron plates in our inventory
"""
# Inventory at the start of step {'iron-ore': 23, 'copper-ore': 5}
#Step Execution

# Step 3: Smelt Iron Plates

# Get entities around us again to ensure we have an updated view
entities_around = get_entities()
stone_furnaces = [entity for entity in entities_around if entity.name == Prototype.StoneFurnace.value[0]]
assert len(stone_furnaces) > 0, "No stone furnaces found nearby!"

stone_furnace = stone_furnaces[0]
print(f"Using stone furnace at {stone_furnace.position} with status '{stone_furnace.status}'")

# Check current inventory for available iron ore
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
print(f"Iron Ore available in inventory: {iron_ore_in_inventory}")

# Ensure there is enough iron ore before proceeding (we expect exactly 23 based on previous steps)
assert iron_ore_in_inventory >= 23, f"Insufficient Iron Ore! Expected at least 23 but found {iron_ore_in_inventory}"

# Insert all available Iron Ore into the Stone Furnace
insert_item(Prototype.IronOre, stone_furnace, quantity=iron_ore_in_inventory)
print("Inserted Iron Ore into the Stone Furnace.")

# Calculate expected number of Iron Plates after smelting
initial_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
expected_final_count = initial_iron_plate_count + iron_ore_in_inventory

# Wait for smelting to complete; assume each unit takes approximately 0.7 seconds
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_in_inventory)
sleep(total_smelting_time)

max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    # Attempt to extract all possible Iron Plates from Furnace's output slot
    extract_item(Prototype.IronPlate, stone_furnace.position, quantity=iron_ore_in_inventory)

    # Re-check inventory count post-extraction attempt
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)

    # If we've reached or exceeded expected plate count then break out of loop early
    if current_iron_plate_count >= expected_final_count:
        break
    
    sleep(10) # Allow additional time if needed

print(f"Extracted Iron Plates; Current Inventory Count: {current_iron_plate_count}")
print(f"Inventory after extracting: {inspect_inventory()}")

# Final assertion check ensuring successful completion of objective criteria 
assert current_iron_plate_count >= expected_final_count, f"Failed to obtain required number of Iron Plates! Expected: {expected_final_count}, Found: {current_iron_plate_count}"
print("Successfully obtained required number of Iron Plates!")


"""
Step 4: Smelt copper plates
- Smelt 5 copper ore into copper plates
OUTPUT CHECK: Verify that we have 5 copper plates in our inventory
"""
# Inventory at the start of step {'copper-ore': 5, 'iron-plate': 23}
#Step Execution

# Step 4: Smelt Copper Plates

# Get entities around us again to ensure we have an updated view
entities_around = get_entities()
stone_furnaces = [entity for entity in entities_around if entity.name == Prototype.StoneFurnace.value[0]]
assert len(stone_furnaces) > 0, "No stone furnaces found nearby!"

stone_furnace = stone_furnaces[0]
print(f"Using stone furnace at {stone_furnace.position} with status '{stone_furnace.status}'")

# Check current inventory for available copper ore
copper_ore_in_inventory = inspect_inventory().get(Prototype.CopperOre, 0)
print(f"Copper Ore available in inventory: {copper_ore_in_inventory}")

# Ensure there is enough copper ore before proceeding (we expect exactly 5 based on previous steps)
assert copper_ore_in_inventory >= 5, f"Insufficient Copper Ore! Expected at least 5 but found {copper_ore_in_inventory}"

# Insert all available Copper Ore into Stone Furnace
insert_item(Prototype.CopperOre, stone_furnace, quantity=copper_ore_in_inventory)
print("Inserted Copper Ore into Stone Furnace.")

# Calculate expected number of Copper Plates after smelting
initial_copper_plate_count = inspect_inventory().get(Prototype.CopperPlate, 0)
expected_final_count = initial_copper_plate_count + copper_ore_in_inventory

# Wait for smelting to complete; assume each unit takes approximately 0.7 seconds
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * copper_ore_in_inventory)
sleep(total_smelting_time)

max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    # Attempt to extract all possible Copper Plates from Furnace's output slot
    extract_item(Prototype.CopperPlate, stone_furnace.position, quantity=copper_ore_in_inventory)

    # Re-check inventory count post-extraction attempt
    current_copper_plate_count = inspect_inventory().get(Prototype.CopperPlate, 0)

    # If we've reached or exceeded expected plate count then break out of loop early
    if current_copper_plate_count >= expected_final_count:
        break
    
    sleep(10) # Allow additional time if needed

print(f"Extracted Copper Plates; Current Inventory Count: {current_copper_plate_count}")
print(f"Inventory after extracting: {inspect_inventory()}")

# Final assertion check ensuring successful completion of objective criteria 
assert current_copper_plate_count >= expected_final_count, f"Failed to obtain required number of Copper Plates! Expected: {expected_final_count}, Found: {current_copper_plate_count}"
print("Successfully obtained required number of Copper Plates!")


"""
Step 5: Craft iron gear wheels
- Craft 5 iron gear wheels (requires 10 iron plates)
OUTPUT CHECK: Verify that we have 5 iron gear wheels in our inventory
"""
# Inventory at the start of step {'iron-plate': 23, 'copper-plate': 5}
#Step Execution

# Step: Craft Iron Gear Wheels

# Check current inventory for available iron plates
iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
print(f"Iron Plates available in inventory: {iron_plates_in_inventory}")

# Ensure there is enough iron plate before proceeding (we expect at least 10 based on requirement)
assert iron_plates_in_inventory >= 10, f"Insufficient Iron Plates! Expected at least 10 but found {iron_plates_in_inventory}"

# Crafting process - Crafting 5 Iron Gear Wheels
craft_item(Prototype.IronGearWheel, quantity=5)
print("Crafted 5 Iron Gear Wheels.")

# Verify that we have crafted enough Iron Gear Wheels
iron_gear_wheels_count = inspect_inventory().get(Prototype.IronGearWheel, 0)
assert iron_gear_wheels_count >= 5, f"Failed to craft required number of Iron Gear Wheels! Expected: At least 5, Found: {iron_gear_wheels_count}"
print(f"Successfully crafted required number of Iron Gear Wheels; Current Inventory Count: {iron_gear_wheels_count}")


"""
Step 6: Craft copper cables
- Craft 9 copper cables (requires 5 copper plates)
OUTPUT CHECK: Verify that we have 9 copper cables in our inventory
"""
# Inventory at the start of step {'iron-plate': 13, 'copper-plate': 5, 'iron-gear-wheel': 5}
#Step Execution

# Step: Craft Copper Cables

# Check current inventory for available copper plates
copper_plates_in_inventory = inspect_inventory().get(Prototype.CopperPlate, 0)
print(f"Copper Plates available in inventory: {copper_plates_in_inventory}")

# Ensure there is enough copper plate before proceeding (we expect exactly 5 based on requirement)
assert copper_plates_in_inventory >= 5, f"Insufficient Copper Plates! Expected at least 5 but found {copper_plates_in_inventory}"

# Crafting process - Crafting 9 Copper Cables
craft_item(Prototype.CopperCable, quantity=9)
print("Crafted 9 Copper Cables.")

# Verify that we have crafted enough Copper Cables
copper_cable_count = inspect_inventory().get(Prototype.CopperCable, 0)
assert copper_cable_count >= 9, f"Failed to craft required number of Copper Cables! Expected: At least 9, Found: {copper_cable_count}"
print(f"Successfully crafted required number of Copper Cables; Current Inventory Count: {copper_cable_count}")


"""
Step 7: Craft electronic circuits
- Craft 3 electronic circuits (requires 9 copper cables and 3 iron plates)
OUTPUT CHECK: Verify that we have 3 electronic circuits in our inventory
"""
# Inventory at the start of step {'iron-plate': 13, 'copper-cable': 10, 'iron-gear-wheel': 5}
#Step Execution

# Step: Craft Electronic Circuits

# Check current inventory for available resources
copper_cables_in_inventory = inspect_inventory().get(Prototype.CopperCable, 0)
iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)

print(f"Copper Cables available in inventory: {copper_cables_in_inventory}")
print(f"Iron Plates available in inventory: {iron_plates_in_inventory}")

# Ensure there are enough resources before proceeding (we expect exactly what is needed based on requirement)
assert copper_cables_in_inventory >= 9, f"Insufficient Copper Cables! Expected at least 9 but found {copper_cables_in_inventory}"
assert iron_plates_in_inventory >= 3, f"Insufficient Iron Plates! Expected at least 3 but found {iron_plates_in_inventory}"

# Crafting process - Crafting 3 Electronic Circuits
craft_item(Prototype.ElectronicCircuit, quantity=3)
print("Crafted 3 Electronic Circuits.")

# Verify that we have crafted enough Electronic Circuits
electronic_circuits_count = inspect_inventory().get(Prototype.ElectronicCircuit, 0)
assert electronic_circuits_count >= 3, f"Failed to craft required number of Electronic Circuits! Expected: At least 3, Found: {electronic_circuits_count}"
print(f"Successfully crafted required number of Electronic Circuits; Current Inventory Count: {electronic_circuits_count}")


"""
Step 8: Craft ElectricMiningDrill
- Craft 1 ElectricMiningDrill (requires 3 electronic circuits, 5 iron gear wheels, and 10 iron plates)
OUTPUT CHECK: Verify that we have 1 ElectricMiningDrill in our inventory

##
"""
# Inventory at the start of step {'iron-plate': 10, 'copper-cable': 1, 'iron-gear-wheel': 5, 'electronic-circuit': 3}
#Step Execution

# Step: Craft Electric Mining Drill

# Check current inventory for required items
iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
iron_gear_wheels_in_inventory = inspect_inventory().get(Prototype.IronGearWheel, 0)
electronic_circuits_in_inventory = inspect_inventory().get(Prototype.ElectronicCircuit, 0)

print(f"Iron Plates available in inventory: {iron_plates_in_inventory}")
print(f"Iron Gear Wheels available in inventory: {iron_gear_wheels_in_inventory}")
print(f"Electronic Circuits available in inventory: {electronic_circuits_in_inventory}")

# Ensure there are enough resources before proceeding (we expect exactly what is needed based on requirement)
assert iron_plates_in_inventory >= 10, f"Insufficient Iron Plates! Expected at least 10 but found {iron_plates_in_inventory}"
assert iron_gear_wheels_in_inventory >= 5, f"Insufficient Iron Gear Wheels! Expected at least 5 but found {iron_gear_wheels_in_inventory}"
assert electronic_circuits_in_inventory >= 3, f"Insufficient Electronic Circuits! Expected at least 3 but found {electronic_circuits_in_inventory}"

# Crafting process - Crafting an Electric Mining Drill
craft_item(Prototype.ElectricMiningDrill, quantity=1)
print("Crafted an Electric Mining Drill.")

# Verify that we have crafted an Electric Mining Drill
electric_mining_drill_count = inspect_inventory().get(Prototype.ElectricMiningDrill, 0)
assert electric_mining_drill_count >= 1, f"Failed to craft required number of Electric Mining Drills! Expected: At least 1, Found: {electric_mining_drill_count}"
print(f"Successfully crafted required number of Electric Mining Drills; Current Inventory Count: {electric_mining_drill_count}")

# Final success message indicating completion of main objective.
if electric_mining_drill_count >=1:
    print("Successfully completed the main objective by crafting an ElectricMiningDrill!")
