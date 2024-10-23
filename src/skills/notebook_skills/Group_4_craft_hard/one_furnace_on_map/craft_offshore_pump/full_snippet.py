from factorio_instance import *

"""
Main Objective: We require one OffshorePump. The final success should be checked by looking if a OffshorePump is in inventory
"""



"""
Step 1: Gather resources. We need to mine the following:
- 5 iron ore
- 3 copper ore
- Coal (at least 10 for smelting)
- 5 stone (to craft an additional furnace)
OUTPUT CHECK: Verify that we have at least 5 iron ore, 3 copper ore, 10 coal, and 5 stone in our inventory.
"""
# Inventory at the start of step {}
#Step Execution

# Define the resources and their required quantities
resources_to_mine = [
    (Resource.IronOre, 5),
    (Resource.CopperOre, 3),
    (Resource.Coal, 10),
    (Resource.Stone, 5)
]

# Loop through each resource type and mine it
for resource_type, required_amount in resources_to_mine:
    # Find the nearest position of this resource type
    print(f"Finding nearest {resource_type}...")
    nearest_position = nearest(resource_type)
    
    # Move to that position
    print(f"Moving to {resource_type} at position {nearest_position}...")
    move_to(nearest_position)
    
    # Harvest the required amount of this resource
    print(f"Harvesting {required_amount} units of {resource_type}...")
    harvested_amount = harvest_resource(nearest_position, quantity=required_amount)
    
    # Verify that we've harvested enough by checking inventory
    current_inventory = inspect_inventory()
    
    assert current_inventory.get(resource_type) >= required_amount, (
        f"Failed to harvest enough {resource_type}. "
        f"Expected at least {required_amount}, but got {current_inventory.get(resource_type)}"
    )
    
print("Successfully gathered all necessary resources.")
print(f"Current Inventory: {inspect_inventory()}")

# Final assertion checks for all resources together as a summary check.
final_inventory = inspect_inventory()
assert final_inventory.get(Resource.IronOre) >= 5, "Not enough Iron Ore."
assert final_inventory.get(Resource.CopperOre) >= 3, "Not enough Copper Ore."
assert final_inventory.get(Resource.Coal) >= 10, "Not enough Coal."
assert final_inventory.get(Resource.Stone) >= 5, "Not enough Stone."

print("All initial gathering objectives met successfully!")


"""
Step 2: Craft an additional stone furnace. We need to carry out the following:
- Craft a stone furnace using 5 stone
OUTPUT CHECK: Verify that we now have 2 stone furnaces (1 in inventory, 1 on map)
"""
# Inventory at the start of step {'coal': 10, 'stone': 5, 'iron-ore': 5, 'copper-ore': 3}
#Step Execution

# Craft a stone furnace using 5 stones
print("Attempting to craft a Stone Furnace...")
crafted_furnace_count = craft_item(Prototype.StoneFurnace, 1)
assert crafted_furnace_count == 1, "Failed to craft Stone Furnace."

# Check current inventory for Stone Furnace count
inventory_after_crafting = inspect_inventory()
stone_furnace_in_inventory = inventory_after_crafting.get(Prototype.StoneFurnace, 0)
print(f"Stone Furnaces in Inventory after crafting: {stone_furnace_in_inventory}")

# Verify there is now exactly 1 Stone Furnace in inventory
assert stone_furnace_in_inventory == 1, f"Expected 1 Stone Furnace in inventory but found {stone_furnace_in_inventory}."

# Check existing entities on map for any placed furnaces
existing_stone_furnaces_on_map = get_entities({Prototype.StoneFurnace})
furnaces_on_map_count = len(existing_stone_furnaces_on_map)
print(f"Stone Furnaces currently on map: {furnaces_on_map_count}")

# Verify total number of furnaces (on map + in inventory) equals expected amount (2)
total_stone_furnaces = furnaces_on_map_count + stone_furnace_in_inventory
assert total_stone_furnaces == 2, f"Total Stone Furnaces should be 2 but found {total_stone_furnaces}."

print("Successfully crafted an additional Stone Furnace.")


"""
Step 3: Set up smelting operation. We need to:
- Place the new stone furnace next to the existing one
- Fuel both furnaces with coal
OUTPUT CHECK: Verify that both furnaces are placed and fueled
"""
# Inventory at the start of step {'stone-furnace': 1, 'coal': 10, 'iron-ore': 5, 'copper-ore': 3}
#Step Execution

# Step 3 Implementation

# Get the existing stone furnace entity on the map
existing_furnace = get_entities({Prototype.StoneFurnace})[0]
print(f"Existing Stone Furnace found at position {existing_furnace.position}")

# Place new stone furnace next to the existing one
new_furnace_position = Position(x=existing_furnace.position.x + 2, y=existing_furnace.position.y) # Assuming placement to right
move_to(new_furnace_position)
new_stone_furnace = place_entity(Prototype.StoneFurnace, Direction.UP, new_furnace_position)
print(f"Placed new Stone Furnace at position {new_stone_furnace.position}")

# Fueling process
coal_in_inventory = inspect_inventory()[Prototype.Coal]
half_coal_each = coal_in_inventory // 2

# Fuel existing furnace
existing_furnace = insert_item(Prototype.Coal, existing_furnace, half_coal_each)
print(f"Fueled Existing Stone Furnace with {half_coal_each} units of Coal")

# Fuel new furnace
new_stone_furnace = insert_item(Prototype.Coal, new_stone_furnace, half_coal_each)
print(f"Fueled New Stone Furnace with {half_coal_each} units of Coal")

# Verify that both furnaces are fueled (status should not be NO_FUEL)
assert EntityStatus.NO_FUEL not in [existing_furnace.status], "Existing furnace is out of fuel!"
assert EntityStatus.NO_FUEL not in [new_stone_furnace.status], "Newly placed furnace is out of fuel!"

print("Both furnaces are successfully placed and fueled.")


"""
Step 4: Smelt plates. We need to:
- Smelt 5 iron ore into 5 iron plates
- Smelt 3 copper ore into 3 copper plates
OUTPUT CHECK: Verify that we have 5 iron plates and 3 copper plates in our inventory
"""
# Inventory at the start of step {'iron-ore': 5, 'copper-ore': 3}
#Step Execution

# Get references to both stone furnaces
stone_furnaces = get_entities({Prototype.StoneFurnace})
furnace_iron = stone_furnaces[0]
furnace_copper = stone_furnaces[1]

print(f"Using Furnace at {furnace_iron.position} for Iron Ore")
print(f"Using Furnace at {furnace_copper.position} for Copper Ore")

# Insert Iron Ore into first furnace
iron_ore_count = inspect_inventory()[Prototype.IronOre]
furnace_iron = insert_item(Prototype.IronOre, furnace_iron, iron_ore_count)
print(f"Inserted {iron_ore_count} Iron Ore into first Stone Furnace.")

# Insert Copper Ore into second furnace
copper_ore_count = inspect_inventory()[Prototype.CopperOre]
furnace_copper = insert_item(Prototype.CopperOre, furnace_copper, copper_ore_count)
print(f"Inserted {copper_ore_count} Copper Ore into second Stone Furnace.")

# Calculate expected results
expected_iron_plates = iron_ore_count
expected_copper_plates = copper_ore_count

# Wait and check loop
max_attempts = 10
for attempt in range(max_attempts):
    print(f"Smelting attempt {attempt + 1}")
    
    # Wait for smelting (assuming about 3.5s per item for safety)
    sleep(max(iron_ore_count, copper_ore_count) * 3.5)
    
    # Try extracting Iron Plates
    extract_item(Prototype.IronPlate, furnace_iron.position, quantity=expected_iron_plates)
    
    # Try extracting Copper Plates
    extract_item(Prototype.CopperPlate, furnace_copper.position, quantity=expected_copper_plates)
    
    # Check current plate counts in inventory
    current_inventory = inspect_inventory()
    current_iron_plates = current_inventory.get(Prototype.IronPlate, 0)
    current_copper_plates = current_inventory.get(Prototype.CopperPlate, 0)
    
    print(f"Current inventory: Iron Plates: {current_iron_plates}, Copper Plates: {current_copper_plates}")
    
    # If we've reached desired amounts, break out of loop
    if current_iron_plates >= expected_iron_plates and current_copper_plates >= expected_copper_plates:
        print("Smelting completed successfully!")
        break
    
    print("Smelting not complete, waiting for next attempt...")

# Final verification
final_inventory = inspect_inventory()
final_iron_plates = final_inventory.get(Prototype.IronPlate, 0)
final_copper_plates = final_inventory.get(Prototype.CopperPlate, 0)

assert final_iron_plates >= expected_iron_plates, f"Failed to smelt enough Iron Plates. Expected {expected_iron_plates}, but got {final_iron_plates}"
assert final_copper_plates >= expected_copper_plates, f"Failed to smelt enough Copper Plates. Expected {expected_copper_plates}, but got {final_copper_plates}"

print(f"Successfully smelted {final_iron_plates} Iron Plates and {final_copper_plates} Copper Plates!")


"""
Step 5: Craft intermediate components. We need to craft:
- 1 iron gear wheel (requires 2 iron plates)
- 2 electronic circuits (requires 2 iron plates and 3 copper plates)
- 1 pipe (requires 1 iron plate)
OUTPUT CHECK: Verify that we have 1 iron gear wheel, 2 electronic circuits, and 1 pipe in our inventory
"""
# Inventory at the start of step {'iron-plate': 5, 'copper-plate': 3}
#Step Execution

# Step to craft intermediate components

# Initial Inventory Check
initial_inventory = inspect_inventory()
print(f"Initial Inventory: {initial_inventory}")

# Crafting Iron Gear Wheel
print("Crafting Iron Gear Wheel...")
iron_gear_wheel_count = craft_item(Prototype.IronGearWheel, quantity=1)
assert iron_gear_wheel_count == 1, "Failed to craft Iron Gear Wheel."
print("Successfully crafted Iron Gear Wheel.")

# Crafting Electronic Circuits
print("Crafting Electronic Circuits...")
electronic_circuit_count = craft_item(Prototype.ElectronicCircuit, quantity=2)
assert electronic_circuit_count == 2, "Failed to craft Electronic Circuits."
print("Successfully crafted Electronic Circuits.")

# Crafting Pipe
print("Crafting Pipe...")
pipe_count = craft_item(Prototype.Pipe, quantity=1)
assert pipe_count == 1, "Failed to craft Pipe."
print("Successfully crafted Pipe.")

# Final Inventory Check
final_inventory = inspect_inventory()
iron_gear_wheel_in_inventory = final_inventory.get(Prototype.IronGearWheel, 0)
electronic_circuits_in_inventory = final_inventory.get(Prototype.ElectronicCircuit, 0)
pipe_in_inventory = final_inventory.get(Prototype.Pipe, 0)

print(f"Final Inventory: {final_inventory}")

# Verify that all required components are present in the inventory
assert iron_gear_wheel_in_inventory >= 1, f"Expected at least one Iron Gear Wheel but found {iron_gear_wheel_in_inventory}."
assert electronic_circuits_in_inventory >= 2, f"Expected at least two Electronic Circuits but found {electronic_circuits_in_inventory}."
assert pipe_in_inventory >= 1, f"Expected at least one Pipe but found {pipe_in_inventory}."

print("Successfully crafted all intermediate components.")


"""
Step 6: Craft the OffshorePump. We need to:
- Use 2 electronic circuits, 1 iron gear wheel, and 1 pipe to craft 1 OffshorePump
OUTPUT CHECK: Verify that we have 1 OffshorePump in our inventory
##
"""
# Inventory at the start of step {'pipe': 1, 'iron-gear-wheel': 1, 'electronic-circuit': 2}
#Step Execution

# Initial Inventory Check
initial_inventory = inspect_inventory()
print(f"Initial Inventory before crafting OffshorePump: {initial_inventory}")

# Ensure we have all necessary components before crafting
assert initial_inventory.get(Prototype.ElectronicCircuit) >= 2, "Not enough Electronic Circuits."
assert initial_inventory.get(Prototype.IronGearWheel) >= 1, "Not enough Iron Gear Wheels."
assert initial_inventory.get(Prototype.Pipe) >= 1, "Not enough Pipes."

# Crafting OffshorePump
print("Crafting OffshorePump...")
offshore_pump_count = craft_item(Prototype.OffshorePump, quantity=1)
assert offshore_pump_count == 1, "Failed to craft Offshore Pump."
print("Successfully crafted Offshore Pump.")

# Final Inventory Check
final_inventory = inspect_inventory()
offshore_pump_in_inventory = final_inventory.get(Prototype.OffshorePump, 0)

print(f"Final Inventory after crafting: {final_inventory}")

# Verify that the crafted item is present in the inventory
assert offshore_pump_in_inventory >= 1, f"Expected at least one Offshore Pump but found {offshore_pump_in_inventory}."

print("Successfully completed objective of having an Offshore Pump in inventory.")
