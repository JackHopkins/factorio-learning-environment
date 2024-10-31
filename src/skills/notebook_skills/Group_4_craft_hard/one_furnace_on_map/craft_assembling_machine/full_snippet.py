from factorio_instance import *

"""
Main Objective: We require one AssemblingMachine. The final success should be checked by looking if a AssemblingMachine is in inventory
"""



"""
Step 1: Gather resources
- Mine iron ore (at least 22)
- Mine copper ore (at least 5)
- Mine coal (at least 20 for fueling the furnace)
- Mine stone (at least 5 for crafting an additional furnace)
OUTPUT CHECK: Verify that we have at least 22 iron ore, 5 copper ore, 20 coal, and 5 stone in the inventory
"""
# Inventory at the start of step {}
#Step Execution

# Define the minimum quantities needed for each resource
required_resources = {
    Resource.IronOre: 22,
    Resource.CopperOre: 5,
    Resource.Coal: 20,
    Resource.Stone: 5
}

# Loop through each resource type and gather them
for resource_type, required_amount in required_resources.items():
    # Find nearest position of this resource type
    nearest_resource_position = nearest(resource_type)
    
    # Move to that position to start mining
    move_to(nearest_resource_position)
    
    # Harvest more than needed to ensure we have enough due to inefficiencies or losses
    harvested_amount = harvest_resource(nearest_resource_position, quantity=required_amount + 10)
    
    # Use the first element of the tuple for the resource name
    print(f"Harvested {harvested_amount} units of {resource_type[0]}.")
    
    # Verify that we have gathered enough of this resource in our inventory
    current_inventory = inspect_inventory()
    
    # Use the resource_type directly as the key for the inventory
    actual_amount_in_inventory = current_inventory[resource_type]
    
    assert actual_amount_in_inventory >= required_amount, (
        f"Failed to gather enough {resource_type[0]}. "
        f"Expected at least {required_amount}, but got {actual_amount_in_inventory}."
    )
    
print("Successfully gathered all necessary resources.")
print(f"Final Inventory State: {inspect_inventory()}")


"""
Step 2: Craft and set up furnaces
- Craft a stone furnace using 5 stone
- Move to the existing furnace on the map
- Place the newly crafted furnace next to the existing one
OUTPUT CHECK: Confirm that we now have two furnaces placed on the map
"""
# Inventory at the start of step {'coal': 30, 'stone': 15, 'iron-ore': 32, 'copper-ore': 15}
#Step Execution

# Step 1: Craft a Stone Furnace using 5 stones
print("Crafting a stone furnace...")
craft_item(Prototype.StoneFurnace, 1)
crafted_furnace_count = inspect_inventory()[Prototype.StoneFurnace]
assert crafted_furnace_count >= 1, "Failed to craft a stone furnace."
print(f"Successfully crafted {crafted_furnace_count} stone furnace(s).")

# Step 2: Locate and move near the existing furnace
existing_furnace_position = Position(x=-12.0, y=-12.0)
move_to(existing_furnace_position)

# Step 3: Place the newly crafted furnace next to the existing one
new_furnace = place_entity_next_to(
    Prototype.StoneFurnace,
    reference_position=existing_furnace_position,
    direction=Direction.RIGHT,
    spacing=0
)
print(f"Placed new stone furnace at {new_furnace.position}")

# Step 4: Verify that there are now two furnaces placed on the map
furnaces_on_map = get_entities({Prototype.StoneFurnace})
assert len(furnaces_on_map) == 2, f"Expected 2 furnaces but found {len(furnaces_on_map)}."
print("Confirmed that there are now two furnaces placed on the map.")


"""
Step 3: Smelt iron plates
- Move to the first furnace
- Add coal to the furnace for fuel
- Add iron ore to the furnace
- Wait for the iron plates to be smelted (22 iron plates needed)
OUTPUT CHECK: Verify that we have at least 22 iron plates in the inventory
"""
# Inventory at the start of step {'coal': 30, 'stone': 10, 'iron-ore': 32, 'copper-ore': 15}
#Step Execution

# Step 1: Select and move near the first stone furnace
first_furnace_position = Position(x=-12.0, y=-12.0)
move_to(first_furnace_position)

# Step 2: Get a reference to the first stone furnace entity
furnace_entities = get_entities({Prototype.StoneFurnace})
first_furnace = next(furnace for furnace in furnace_entities if furnace.position.is_close(first_furnace_position))

# Step 3: Add coal as fuel to the first stone furnace
coal_in_inventory = inspect_inventory()[Prototype.Coal]
print(f"Coal available in inventory: {coal_in_inventory}")
first_furnace = insert_item(Prototype.Coal, first_furnace, min(coal_in_inventory, 10)) # Use up to 10 units of coal

# Step 4: Add iron ore into the first stone furnace
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
print(f"Iron ore available in inventory: {iron_ore_in_inventory}")
first_furnace = insert_item(Prototype.IronOre, first_furnace, min(iron_ore_in_inventory, 22)) # Use up to 22 units of iron ore

# Step 5: Wait for smelting process (0.7 seconds per unit of ore)
sleep(min(iron_ore_in_inventory, 22) * 0.7)

# Step 6: Extract produced iron plates from the first stone furnace
extract_item(Prototype.IronPlate, first_furnace.position, min(iron_ore_in_inventory, 22))
print("Extracted produced Iron Plates from Furnace.")

# Step 7: Verify that there are at least 22 Iron Plates in inventory
current_iron_plate_count = inspect_inventory()[Prototype.IronPlate]
assert current_iron_plate_count >= 22,\
    f"Failed verification! Expected at least 22 Iron Plates but found {current_iron_plate_count}."

print("Successfully completed smelting step - At least required number of Iron Plates obtained.")


"""
Step 4: Smelt copper plates
- Move to the second furnace
- Add coal to the furnace for fuel
- Add copper ore to the furnace
- Wait for the copper plates to be smelted (5 copper plates needed)
OUTPUT CHECK: Verify that we have at least 5 copper plates in the inventory
"""
# Inventory at the start of step {'coal': 20, 'stone': 10, 'iron-ore': 10, 'copper-ore': 15, 'iron-plate': 22}
#Step Execution

# Step 1: Move near the second stone furnace
second_furnace_position = Position(x=-10.0, y=-12.0)
move_to(second_furnace_position)

# Step 2: Get a reference to the second stone furnace entity
furnace_entities = get_entities({Prototype.StoneFurnace})
second_furnace = next(furnace for furnace in furnace_entities if furnace.position.is_close(second_furnace_position))

# Step 3: Add coal as fuel to the second stone furnace
coal_in_inventory = inspect_inventory()[Prototype.Coal]
print(f"Coal available in inventory before fueling second furnace: {coal_in_inventory}")
second_furnace = insert_item(Prototype.Coal, second_furnace, min(coal_in_inventory, 10)) # Use up to 10 units of coal

# Step 4: Add copper ore into the second stone furnace
copper_ore_in_inventory = inspect_inventory()[Prototype.CopperOre]
print(f"Copper ore available in inventory before inserting into second furnace: {copper_ore_in_inventory}")
second_furnace = insert_item(Prototype.CopperOre, second_furnace, min(copper_ore_in_inventory, 5)) # Use up to 5 units of copper ore

# Step 5: Wait for smelting process (0.7 seconds per unit of ore)
sleep(min(copper_ore_in_inventory, 5) * 0.7)

# Step 6: Extract produced copper plates from the second stone furnace
extract_item(Prototype.CopperPlate, second_furnace.position, min(copper_ore_in_inventory, 5))
print("Extracted produced Copper Plates from Furnace.")

# Step 7: Verify that there are at least 5 Copper Plates in inventory
current_copper_plate_count = inspect_inventory()[Prototype.CopperPlate]
assert current_copper_plate_count >= 5,\
    f"Failed verification! Expected at least 5 Copper Plates but found {current_copper_plate_count}."

print("Successfully completed smelting step - At least required number of Copper Plates obtained.")


"""
Step 5: Craft intermediate components
- Craft 5 iron gear wheels (requires 10 iron plates)
- Craft 6 copper cables (requires 3 copper plates)
- Craft 3 electronic circuits (requires 3 iron plates, 6 copper cables)
OUTPUT CHECK: Confirm that we have 5 iron gear wheels and 3 electronic circuits in the inventory
"""
# Inventory at the start of step {'coal': 10, 'stone': 10, 'iron-ore': 10, 'copper-ore': 10, 'iron-plate': 22, 'copper-plate': 5}
#Step Execution

# Step 1: Craft Iron Gear Wheels
print("Crafting Iron Gear Wheels...")
craft_item(Prototype.IronGearWheel, 5)
iron_gear_wheels_count = inspect_inventory()[Prototype.IronGearWheel]
assert iron_gear_wheels_count >= 5, f"Failed to craft enough Iron Gear Wheels. Expected at least 5 but got {iron_gear_wheels_count}."
print(f"Successfully crafted {iron_gear_wheels_count} Iron Gear Wheels.")

# Step 2: Craft Copper Cables
print("Crafting Copper Cables...")
craft_item(Prototype.CopperCable, 6)
copper_cables_count = inspect_inventory()[Prototype.CopperCable]
assert copper_cables_count >= 6, f"Failed to craft enough Copper Cables. Expected at least 6 but got {copper_cables_count}."
print(f"Successfully crafted {copper_cables_count} Copper Cables.")

# Step 3: Craft Electronic Circuits
print("Crafting Electronic Circuits...")
craft_item(Prototype.ElectronicCircuit, 3)
electronic_circuits_count = inspect_inventory()[Prototype.ElectronicCircuit]
assert electronic_circuits_count >= 3, f"Failed to craft enough Electronic Circuits. Expected at least 3 but got {electronic_circuits_count}."
print(f"Successfully crafted {electronic_circuits_count} Electronic Circuits.")

# Final check for all intermediate components
assert iron_gear_wheels_count >= 5 and electronic_circuits_count >= 3,\
    "Final verification failed! Ensure you have at least the required number of Iron Gear Wheels and Electronic Circuits."

print("Successfully completed crafting of intermediate components - All required items are in inventory.")


"""
Step 6: Craft AssemblingMachine
- Craft 1 AssemblingMachine (requires 3 electronic circuits, 5 iron gear wheels, 9 iron plates)
OUTPUT CHECK: Verify that we have 1 AssemblingMachine in the inventory

##
"""
# Inventory at the start of step {'coal': 10, 'stone': 10, 'iron-ore': 10, 'copper-ore': 10, 'iron-plate': 9, 'copper-cable': 1, 'iron-gear-wheel': 5, 'electronic-circuit': 3}
#Step Execution

# Step 1: Craft an Assembling Machine
print("Crafting an Assembling Machine...")
craft_item(Prototype.AssemblingMachine1, 1)

# Step 2: Verify that there is at least one Assembling Machine in the inventory
assembling_machine_count = inspect_inventory()[Prototype.AssemblingMachine1]
assert assembling_machine_count >= 1, f"Failed to craft an Assembling Machine. Expected at least 1 but got {assembling_machine_count}."
print(f"Successfully crafted {assembling_machine_count} Assembling Machine(s).")

# Final confirmation of objective completion
if assembling_machine_count >= 1:
    print("Successfully completed main objective! An Assembling Machine is now available in the inventory.")
else:
    print("Main objective not achieved yet.")
