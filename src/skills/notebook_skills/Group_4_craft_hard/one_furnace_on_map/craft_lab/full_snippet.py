from factorio_instance import *

"""
Main Objective: We require one Lab. The final success should be checked by looking if a Lab is in inventory
"""



"""
Step 1: Gather resources. We need to mine the following:
- Coal (for fuel and crafting)
- Iron ore (for iron plates, gear wheels, and electronic circuits)
- Copper ore (for copper plates and electronic circuits)
- Stone (for additional furnaces if needed)
OUTPUT CHECK: Verify that we have sufficient quantities of each resource in our inventory.
"""
# Inventory at the start of step {}
#Step Execution

# Define required resources and their target amounts
resources_needed = {
    Resource.IronOre: 40,  # Slightly more than needed for safety
    Resource.CopperOre: 20,
    Resource.Coal: 20,
    Resource.Stone: 10
}

# Loop through each required resource
for resource, target_amount in resources_needed.items():
    # Get nearest position of the current resource
    print(f"Finding nearest {resource}...")
    resource_position = nearest(resource)
    
    # Move towards the found position of the current resource
    print(f"Moving to {resource} location at {resource_position}...")
    move_to(resource_position)
    
    # Harvesting the required amount of current resource
    print(f"Harvesting {target_amount} units of {resource}...")
    
    # Attempt harvesting multiple times if necessary due to potential inefficiencies 
    attempts = 0
    while inspect_inventory().get(resource, 0) < target_amount and attempts < 5:
        harvest_resource(resource_position, quantity=target_amount)
        attempts += 1
    
    # Check if sufficient quantity has been gathered into inventory 
    actual_quantity = inspect_inventory().get(resource, 0)
    assert actual_quantity >= target_amount, f"Failed gathering enough {resource}. Expected:{target_amount}, but got:{actual_quantity}"

print("Successfully gathered all necessary resources.")
print(f"Final inventory: {inspect_inventory()}")


"""
Step 2: Fuel and use the existing furnace. 
- Move to the furnace at position (-12.0, -12.0)
- Add coal to the furnace as fuel
OUTPUT CHECK: Confirm that the furnace is fueled and ready for smelting.
"""
# Inventory at the start of step {'coal': 20, 'stone': 10, 'iron-ore': 40, 'copper-ore': 20}
#Step Execution

# First, move near the stone furnace so we can interact with it
furnace_position = Position(x=-12.0, y=-12.0)
print(f"Moving towards the stone furnace at {furnace_position}...")
move_to(furnace_position)

# Get current inventory state for logging purposes
current_inventory = inspect_inventory()
coal_in_inventory = current_inventory[Prototype.Coal]
print(f"Coal available in inventory: {coal_in_inventory}")

# Fetching the existing stone furnace entity
stone_furnaces = get_entities({Prototype.StoneFurnace})
stone_furnace = stone_furnaces[0]  # Assuming there's only one based on setup information

# Insert all available coal into the furnace as fuel
print("Inserting coal into the stone furnace...")
stone_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=coal_in_inventory)

# Verify if the insertion was successful by checking its status
if EntityStatus.NO_FUEL not in [status.value for status in [stone_furnace.status]]:
    print("The stone furnace is now fueled and ready for smelting.")
else:
    print("Failed to fuel the stove properly.")

# Log final state of inventory and entity after fueling action
final_inventory = inspect_inventory()
print(f"Final Inventory after fueling: {final_inventory}")
assert Prototype.Coal not in final_inventory or final_inventory[Prototype.Coal] < coal_in_inventory, "Coal wasn't inserted correctly."

# Confirm that there are no warnings related to 'no fuel' anymore 
assert EntityStatus.NO_FUEL != stone_furnace.status, "Furnace still indicates 'no fuel'."


"""
Step 3: Smelt iron plates. 
- Use the fueled furnace to smelt iron ore into iron plates
OUTPUT CHECK: Verify that we have at least 36 iron plates in our inventory.
"""
# Inventory at the start of step {'stone': 10, 'iron-ore': 40, 'copper-ore': 20}
#Step Execution

# Fetching existing stone furnace entity
stone_furnaces = get_entities({Prototype.StoneFurnace})
stone_furnace = stone_furnaces[0]  # Assuming there's only one based on setup information

# Get current inventory state for logging purposes
current_inventory = inspect_inventory()
iron_ore_in_inventory = current_inventory[Prototype.IronOre]
print(f"Iron ore available in inventory: {iron_ore_in_inventory}")

# Insert all available iron ore into the stone furnace
print("Inserting iron ore into the stone furnace...")
stone_furnace = insert_item(Prototype.IronOre, stone_furnace, quantity=iron_ore_in_inventory)

# Calculate expected number of iron plates after smelting
initial_iron_plates = current_inventory.get(Prototype.IronPlate, 0)
expected_iron_plates = initial_iron_plates + iron_ore_in_inventory

# Wait for smelting to complete; assume 0.7 seconds per unit of ore
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_in_inventory)
sleep(total_smelting_time)

max_attempts = 5
for _ in range(max_attempts):
    # Attempt extraction multiple times if necessary due to potential inefficiencies 
    extract_item(Prototype.IronPlate, stone_furnace.position, quantity=iron_ore_in_inventory)
    
    # Check how many plates are now in your inventory after extraction attempt 
    actual_iron_plates = inspect_inventory()[Prototype.IronPlate]

    if actual_iron_plates >= expected_iron_plates:
        break
    
    sleep(10)  # Wait a bit more if not all plates were ready yet 

print(f"Extracted {actual_iron_plates - initial_iron_plates} new Iron Plates.")
print(f"Inventory after extracting: {inspect_inventory()}")

# Confirm final count meets requirement (at least 36 iron plates)
required_iron_plates = 36
assert actual_iron_plates >= required_iron_plates, f"Failed gathering enough Iron Plates. Expected at least {required_iron_plates}, but got {actual_iron_plates}"


"""
Step 4: Smelt copper plates. 
- Use the same furnace to smelt copper ore into copper plates
OUTPUT CHECK: Verify that we have at least 15 copper plates in our inventory.
"""
# Inventory at the start of step {'stone': 10, 'copper-ore': 20, 'iron-plate': 40}
#Step Execution

# Fetching existing stone furnace entity
stone_furnaces = get_entities({Prototype.StoneFurnace})
stone_furnace = stone_furnaces[0]  # Assuming there's only one based on setup information

# Get current inventory state for logging purposes
current_inventory = inspect_inventory()
copper_ore_in_inventory = current_inventory[Prototype.CopperOre]
print(f"Copper ore available in inventory: {copper_ore_in_inventory}")

# Insert all available copper ore into the stone furnace
print("Inserting copper ore into the stone furnace...")
stone_furnace = insert_item(Prototype.CopperOre, stone_furnace, quantity=copper_ore_in_inventory)

# Calculate expected number of copper plates after smelting
initial_copper_plates = current_inventory.get(Prototype.CopperPlate, 0)
expected_copper_plates = initial_copper_plates + copper_ore_in_inventory

# Wait for smelting to complete; assume 0.7 seconds per unit of ore
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * copper_ore_in_inventory)
sleep(total_smelting_time)

max_attempts = 5
for _ in range(max_attempts):
    # Attempt extraction multiple times if necessary due to potential inefficiencies 
    extract_item(Prototype.CopperPlate, stone_furnace.position, quantity=copper_ore_in_inventory)
    
    # Check how many plates are now in your inventory after extraction attempt 
    actual_copper_plates = inspect_inventory()[Prototype.CopperPlate]

    if actual_copper_plates >= expected_copper_plates:
        break
    
    sleep(10)  # Wait a bit more if not all plates were ready yet 

print(f"Extracted {actual_copper_plates - initial_copper_plates} new Copper Plates.")
print(f"Inventory after extracting: {inspect_inventory()}")

# Confirm final count meets requirement (at least 15 copper plates)
required_copper_plates = 15
assert actual_copper_plates >= required_copper_plates, f"Failed gathering enough Copper Plates. Expected at least {required_copper_plates}, but got {actual_copper_plates}"


"""
Step 5: Craft intermediate components.
- Craft 10 iron gear wheels (requires 20 iron plates)
- Craft 30 copper cables (requires 15 copper plates)
- Craft 10 electronic circuits (requires 30 copper cables and 10 iron plates)
- Craft 4 transport belts (requires 2 iron gear wheels and 2 iron plates)
OUTPUT CHECK: Confirm that we have 10 iron gear wheels, 10 electronic circuits, and 4 transport belts in our inventory.
"""
# Inventory at the start of step {'stone': 10, 'iron-plate': 40, 'copper-plate': 20}
#Step Execution

# Step to craft intermediate components

# Craft Iron Gear Wheels
print("Crafting Iron Gear Wheels...")
craft_item(Prototype.IronGearWheel, quantity=10)
gear_wheels_count = inspect_inventory()[Prototype.IronGearWheel]
assert gear_wheels_count >= 10, f"Failed to craft Iron Gear Wheels. Expected at least 10 but got {gear_wheels_count}"
print(f"Successfully crafted {gear_wheels_count} Iron Gear Wheels.")

# Craft Copper Cables
print("Crafting Copper Cables...")
craft_item(Prototype.CopperCable, quantity=30)
copper_cable_count = inspect_inventory()[Prototype.CopperCable]
assert copper_cable_count >= 30, f"Failed to craft Copper Cables. Expected at least 30 but got {copper_cable_count}"
print(f"Successfully crafted {copper_cable_count} Copper Cables.")

# Craft Electronic Circuits
print("Crafting Electronic Circuits...")
craft_item(Prototype.ElectronicCircuit, quantity=10)
electronic_circuits_count = inspect_inventory()[Prototype.ElectronicCircuit]
assert electronic_circuits_count >= 10, f"Failed to craft Electronic Circuits. Expected at least 10 but got {electronic_circuits_count}"
print(f"Successfully crafted {electronic_circuits_count} Electronic Circuits.")

# Craft Transport Belts
print("Crafting Transport Belts...")
craft_item(Prototype.TransportBelt, quantity=4)
transport_belts_count = inspect_inventory()[Prototype.TransportBelt]
assert transport_belts_count >= 4, f"Failed to craft Transport Belts. Expected at least 4 but got {transport_belts_count}"
print(f"Successfully crafted {transport_belts_count} Transport Belts.")

# Final confirmation print statement
final_inventory_check = inspect_inventory()
if all([
    final_inventory_check[Prototype.IronGearWheel] >= 10,
    final_inventory_check[Prototype.ElectronicCircuit] >= 10,
    final_inventory_check[Prototype.TransportBelt] >= 4]):
    print("Successfully completed crafting all intermediate components.")
else:
    print("There was an issue completing all crafts.")


"""
Step 6: Craft the Lab.
- Use the crafted components to create one Lab
OUTPUT CHECK: Verify that we have one Lab in our inventory.

##
"""
# Inventory at the start of step {'transport-belt': 4, 'stone': 10, 'iron-plate': 8, 'copper-plate': 5, 'iron-gear-wheel': 8, 'electronic-circuit': 10}
#Step Execution

# Step to craft a lab

# Print current inventory before crafting
print("Current Inventory:", inspect_inventory())

# Crafting the lab
print("Crafting a Lab...")
craft_item(Prototype.Lab, quantity=1)

# Verify if the lab was successfully crafted by checking its count in inventory
lab_count = inspect_inventory()[Prototype.Lab]
assert lab_count >= 1, f"Failed to craft a Lab. Expected at least 1 but got {lab_count}"
print(f"Successfully crafted {lab_count} Labs.")

# Final confirmation print statement
final_inventory_check = inspect_inventory()
if final_inventory_check[Prototype.Lab] >= 1:
    print("Successfully completed crafting the Lab.")
else:
    print("There was an issue completing the lab craft.")
