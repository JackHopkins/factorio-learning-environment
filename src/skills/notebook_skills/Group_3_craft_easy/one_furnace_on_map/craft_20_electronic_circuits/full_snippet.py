from factorio_instance import *

"""
Main Objective: We need 20 electronic circuits. The final success should be checked by looking if 10 electronic circuits are in inventory
"""



"""
Step 1: Gather raw materials
- Mine coal for fuel (at least 20 pieces)
- Mine iron ore (at least 20 pieces)
- Mine copper ore (at least 60 pieces)
OUTPUT CHECK: Verify that we have at least 20 coal, 20 iron ore, and 60 copper ore in the inventory
"""
# Inventory at the start of step {}
#Step Execution

# Define the resources needed along with their quantities
resources_needed = [
    (Resource.Coal, 20),
    (Resource.IronOre, 20),
    (Resource.CopperOre, 60)
]

# Loop through each required resource
for resource_type, required_quantity in resources_needed:
    # Find the nearest position for this resource
    print(f"Finding nearest {resource_type}...")
    position = nearest(resource_type)
    
    # Move to the position where this resource is located
    print(f"Moving to {resource_type} at position {position}...")
    move_to(position)
    
    # Harvest the necessary quantity of this resource
    print(f"Harvesting {required_quantity} units of {resource_type}...")
    harvested = harvest_resource(position=position, quantity=required_quantity)
    print(f"Actually harvested: {harvested} units of {resource_type}")
    
    # Check if we have harvested enough by inspecting our inventory
    current_inventory = inspect_inventory()
    
    # Log current inventory status after harvesting this particular resource
    print(f"Current Inventory after harvesting {resource_type}: {current_inventory}")
    
    # Assert that we have at least as much as needed for this specific resource type
    assert current_inventory.get(resource_type, 0) >= required_quantity,\
        f"Failed to gather enough {resource_type}. Expected at least {required_quantity}, but got {current_inventory.get(resource_type, 0)}"

print("Successfully gathered all raw materials.")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory after gathering all resources: {final_inventory}")

# Assert that we have the required quantities of each resource
assert final_inventory.get(Resource.Coal, 0) >= 20, f"Not enough coal. Expected at least 20, but got {final_inventory.get(Resource.Coal, 0)}"
assert final_inventory.get(Resource.IronOre, 0) >= 20, f"Not enough iron ore. Expected at least 20, but got {final_inventory.get(Resource.IronOre, 0)}"
assert final_inventory.get(Resource.CopperOre, 0) >= 60, f"Not enough copper ore. Expected at least 60, but got {final_inventory.get(Resource.CopperOre, 0)}"

print("All required resources have been successfully gathered and verified.")


"""
Step 2: Prepare the furnace for smelting
- Move to the furnace at position (-12.0, -12.0)
- Add coal to the furnace as fuel
OUTPUT CHECK: Verify that the furnace status is no longer 'NO_FUEL'
"""
# Inventory at the start of step {'coal': 20, 'iron-ore': 20, 'copper-ore': 60}
#Step Execution

# Step 2: Prepare the furnace for smelting

# Move to where our stone-furnace is located
furnace_position = Position(x=-12.0, y=-12.0)
print(f"Moving to stone-furnace at {furnace_position}...")
move_to(furnace_position)

# Get current state of our inventory before fueling
inventory_before_fueling = inspect_inventory()
coal_in_inventory = inventory_before_fueling.get(Prototype.Coal, 0)
print(f"Coal available in inventory before fueling: {coal_in_inventory}")

# Get the stone furnace
stone_furnaces = get_entities({Prototype.StoneFurnace})
assert len(stone_furnaces) > 0, "No stone furnaces found!"
stone_furnace = stone_furnaces[0]

# Insert all available coal into the stone-furnace
insert_item(Prototype.Coal, target=stone_furnace, quantity=coal_in_inventory)
print(f"Inserted {coal_in_inventory} units of coal into stone-furnace.")

# Get the updated furnace object
updated_furnaces = get_entities({Prototype.StoneFurnace})
assert len(updated_furnaces) > 0, "Stone furnace not found after refueling!"
updated_furnace = updated_furnaces[0]

print(f"Updated status of stone-furnace after fueling: {updated_furnace.status}")

# Check that the furnace has fuel
assert updated_furnace.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel up! Stone-furnace still has no coal."

print("Successfully fueled up and prepared the stone-furnace for smelting.")


"""
Step 3: Smelt iron plates
- Add iron ore to the furnace
- Wait for smelting to complete (20 seconds for 20 iron plates)
- Collect 20 iron plates from the furnace
OUTPUT CHECK: Verify that we have 20 iron plates in the inventory
"""
# Inventory at the start of step {'iron-ore': 20, 'copper-ore': 60}
#Step Execution

# Step 3 Implementation

# Get current state of our inventory before inserting ores
inventory_before_smelting = inspect_inventory()
iron_ore_in_inventory = inventory_before_smelting.get(Prototype.IronOre, 0)
print(f"Iron ore available in inventory before smelting: {iron_ore_in_inventory}")

# Insert all available iron ore into the stone-furnace
stone_furnace = get_entities({Prototype.StoneFurnace})[0]
insert_item(Prototype.IronOre, target=stone_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} units of iron ore into stone-furnace.")

# Wait for smelting to complete (20 seconds for 20 pieces of iron)
sleep(20)

# Extracting produced Iron Plates from Stone Furnace
extract_item(Prototype.IronPlate, stone_furnace.position, quantity=iron_ore_in_inventory)
print("Attempted to extract all possible iron plates from the furnace.")

# Verify that we have at least 20 Iron Plates in our Inventory
current_inventory = inspect_inventory()
iron_plate_count = current_inventory.get(Prototype.IronPlate, 0)

assert iron_plate_count >= 20,\
    f"Failed to gather enough Iron Plates. Expected at least 20 but got {iron_plate_count}"

print("Successfully gathered required number of Iron Plates.")


"""
Step 4: Smelt copper plates
- Add copper ore to the furnace
- Wait for smelting to complete (60 seconds for 60 copper plates)
- Collect 60 copper plates from the furnace
OUTPUT CHECK: Verify that we have 60 copper plates in the inventory
"""
# Inventory at the start of step {'copper-ore': 60, 'iron-plate': 20}
#Step Execution

# Get current state of our inventory before inserting ores
inventory_before_smelting = inspect_inventory()
copper_ore_in_inventory = inventory_before_smelting.get(Prototype.CopperOre, 0)
print(f"Copper ore available in inventory before smelting: {copper_ore_in_inventory}")

# Insert all available copper ore into the stone-furnace
stone_furnace = get_entities({Prototype.StoneFurnace})[0]
insert_item(Prototype.CopperOre, target=stone_furnace, quantity=copper_ore_in_inventory)
print(f"Inserted {copper_ore_in_inventory} units of copper ore into stone-furnace.")

# Initialize copper plate count
copper_plate_count = 0
max_attempts = 10
attempt = 0

while copper_plate_count < 60 and attempt < max_attempts:
    # Wait for some smelting to occur
    sleep(20)
    
    # Check furnace status
    updated_furnace = get_entities({Prototype.StoneFurnace})[0]
    print(f"Furnace status: {updated_furnace.status}")
    print(f"Furnace contents: {updated_furnace.furnace_result}")
    
    # Extract plates (try to extract more than what's likely there)
    extract_item(Prototype.CopperPlate, stone_furnace.position, quantity=30)
    
    # Check inventory
    current_inventory = inspect_inventory()
    copper_plate_count = current_inventory.get(Prototype.CopperPlate, 0)
    print(f"Current copper plate count: {copper_plate_count}")
    
    attempt += 1

# Final inventory check
final_inventory = inspect_inventory()
copper_plate_count = final_inventory.get(Prototype.CopperPlate, 0)

assert copper_plate_count >= 60, f"Failed to gather enough Copper Plates. Expected at least 60 but got {copper_plate_count}"

print(f"Successfully gathered {copper_plate_count} Copper Plates.")
print(f"Final inventory: {final_inventory}")


"""
Step 5: Craft copper cables
- Craft 120 copper cables using 60 copper plates
OUTPUT CHECK: Verify that we have 120 copper cables in the inventory
"""
# Inventory at the start of step {'iron-plate': 20, 'copper-plate': 60}
#Step Execution

# Step 5: Craft Copper Cables

# Inspect current inventory to check available resources
current_inventory = inspect_inventory()
copper_plates_available = current_inventory.get(Prototype.CopperPlate, 0)
print(f"Copper plates available in inventory before crafting: {copper_plates_available}")

# Calculate how many copper cables we can craft (each cable requires one plate)
cables_to_craft = min(copper_plates_available * 2, 120) # We want to craft exactly or up to a max of 120

# Craft the required number of copper cables
crafted_cables = craft_item(Prototype.CopperCable, quantity=cables_to_craft)
print(f"Crafted {crafted_cables} units of Copper Cable.")

# Verify that we have crafted at least as many as needed
final_inventory = inspect_inventory()
copper_cable_count = final_inventory.get(Prototype.CopperCable, 0)

assert copper_cable_count >= 120,\
    f"Failed to gather enough Copper Cables. Expected at least 120 but got {copper_cable_count}"

print("Successfully crafted and verified required number of Copper Cables.")


"""
Step 6: Craft electronic circuits
- Craft 20 electronic circuits using 120 copper cables and 20 iron plates
OUTPUT CHECK: Verify that we have 20 electronic circuits in the inventory

##
"""
# Inventory at the start of step {'iron-plate': 20, 'copper-cable': 120}
#Step Execution

# Step 6 Implementation

# Inspect current inventory to check available resources
current_inventory = inspect_inventory()
copper_cables_available = current_inventory.get(Prototype.CopperCable, 0)
iron_plates_available = current_inventory.get(Prototype.IronPlate, 0)

print(f"Copper cables available in inventory before crafting: {copper_cables_available}")
print(f"Iron plates available in inventory before crafting: {iron_plates_available}")

# Calculate how many electronic circuits we can craft (each circuit requires one cable and one plate)
circuits_to_craft = min(copper_cables_available, iron_plates_available) # We want to craft exactly or up to a max of what is possible

# Craft the required number of electronic circuits
crafted_circuits = craft_item(Prototype.ElectronicCircuit, quantity=circuits_to_craft)
print(f"Crafted {crafted_circuits} units of Electronic Circuit.")

# Verify that we have crafted at least as many as needed
final_inventory = inspect_inventory()
electronic_circuit_count = final_inventory.get(Prototype.ElectronicCircuit, 0)

assert electronic_circuit_count >= 20,\
    f"Failed to gather enough Electronic Circuits. Expected at least 20 but got {electronic_circuit_count}"

print("Successfully crafted and verified required number of Electronic Circuits.")
