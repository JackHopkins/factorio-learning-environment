from factorio_instance import *

"""
Main Objective: We need to craft 7 electronic circuits. The final success should be checked by looking if the electronic circuits are in inventory
"""



"""
Step 1: Print recipes. We need to craft electronic circuits, copper cables, and stone furnaces. Print out the recipes for these items.
"""
# Inventory at the start of step {}
#Step Execution

# Step 1: Get and print recipe for electronic circuits
electronic_circuit_recipe = get_prototype_recipe(Prototype.ElectronicCircuit)
print(f"Electronic Circuit Recipe: {electronic_circuit_recipe}")

# Step 2: Get and print recipe for copper cables
copper_cable_recipe = get_prototype_recipe(Prototype.CopperCable)
print(f"Copper Cable Recipe: {copper_cable_recipe}")

# Step 3: Get and print recipe for stone furnaces
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace Recipe: {stone_furnace_recipe}")


"""
Step 2: Gather additional resources. We need to mine:
- At least 10 stone for crafting 2 stone furnaces
- At least 20 coal for fueling the furnaces
"""
# Inventory at the start of step {}
#Step Execution

# Define resources required
resources_needed = [(Resource.Stone, 12), (Resource.Coal, 25)]

# Loop through each resource type and gather them
for resource_type, amount in resources_needed:
    # Find nearest position of the current resource
    resource_position = nearest(resource_type)
    
    # Move towards that position to start mining
    print(f"Moving towards {resource_type} at position {resource_position}")
    move_to(resource_position)
    
    # Start harvesting the specified amount
    harvested_amount = harvest_resource(resource_position, amount)
    
    # Verify if we've successfully harvested enough resources
    inventory_count = inspect_inventory()[resource_type]
    assert inventory_count >= amount, f"Failed to gather enough {resource_type}. Expected {amount}, but got {inventory_count}"
    
    print(f"Successfully gathered {harvested_amount} of {resource_type}. Current inventory count is {inventory_count}")

# Final check on overall inventory after gathering all necessary materials
final_inventory = inspect_inventory()
print(f"Final inventory after gathering resources: {final_inventory}")

# Assert that we have the required amounts
assert final_inventory[Resource.Stone] >= 12, f"Not enough stone. Expected at least 12, but got {final_inventory[Resource.Stone]}"
assert final_inventory[Resource.Coal] >= 25, f"Not enough coal. Expected at least 25, but got {final_inventory[Resource.Coal]}"


"""
Step 3: Craft stone furnaces. We need to craft 2 stone furnaces using the gathered stone.
"""
# Inventory at the start of step {'coal': 25, 'stone': 12}
#Step Execution

# Craft two stone furnaces using the gathered stones
print("Crafting 2 Stone Furnaces...")
craft_item(Prototype.StoneFurnace, 2)

# Verify if we've successfully crafted two stone furnaces
stone_furnace_count = inspect_inventory()[Prototype.StoneFurnace]
assert stone_furnace_count >= 2, f"Failed to craft enough Stone Furnaces. Expected at least 2, but got {stone_furnace_count}"

print(f"Successfully crafted {stone_furnace_count} Stone Furnaces")


"""
Step 4: Set up smelting operation. We need to:
- Place down the two stone furnaces
- Fuel both furnaces with coal
- Move to the chest and retrieve the iron and copper ore
"""
# Inventory at the start of step {'stone-furnace': 2, 'coal': 25, 'stone': 2}
#Step Execution

# Step 4: Set up smelting operation

# Retrieve positions for placing furnaces
chest_position = Position(x=-11.5, y=-11.5)
furnace_pos_1 = Position(x=chest_position.x + 2, y=chest_position.y) # Place first furnace right of chest
furnace_pos_2 = Position(x=chest_position.x - 2, y=chest_position.y) # Place second furnace left of chest

print(f"Placing first stone furnace at {furnace_pos_1}")
move_to(furnace_pos_1)
furnace1 = place_entity(Prototype.StoneFurnace, direction=Direction.UP, position=furnace_pos_1)

print(f"Placing second stone furnace at {furnace_pos_2}")
move_to(furnace_pos_2)
furnace2 = place_entity(Prototype.StoneFurnace, direction=Direction.UP, position=furnace_pos_2)

# Fuel both furnaces with coal
coal_count_per_furnace = 10  # Assuming an equal distribution of coal for initial fueling

print("Fueling first stone furnace with coal")
insert_item(Prototype.Coal, furnace1, quantity=coal_count_per_furnace)

print("Fueling second stone furnace with coal")
insert_item(Prototype.Coal, furnace2, quantity=coal_count_per_furnace)

# Move to wooden chest and retrieve ores
print("Moving to wooden chest to retrieve ores")
move_to(chest_position)

# Use inspect_entities to get detailed information about entities around the chest position
entities_around_chest = inspect_entities(chest_position, radius=1).entities
chest = next((entity for entity in entities_around_chest if entity.name == "wooden-chest"), None)

if chest is None:
    raise Exception("Wooden chest not found at the expected position")

# Extract iron and copper ore from the chest
iron_ore_extracted = extract_item(Prototype.IronOre, chest.position, quantity=9)
copper_ore_extracted = extract_item(Prototype.CopperOre, chest.position, quantity=15)

# Verify extraction success by checking inventory counts
inventory_after_extraction = inspect_inventory()
assert inventory_after_extraction.get(Prototype.IronOre, 0) >= iron_ore_extracted, \
    f"Failed to extract enough Iron Ore from Chest. Expected at least {iron_ore_extracted} but got {inventory_after_extraction.get(Prototype.IronOre, 0)}"
assert inventory_after_extraction.get(Prototype.CopperOre, 0) >= copper_ore_extracted, \
    f"Failed to extract enough Copper Ore from Chest. Expected at least {copper_ore_extracted} but got {inventory_after_extraction.get(Prototype.CopperOre, 0)}"

print(f"Successfully set up smelting operation. Extracted {iron_ore_extracted} Iron Ore and {copper_ore_extracted} Copper Ore.")
print(f"Current inventory: {inspect_inventory()}")


"""
Step 5: Smelt plates. We need to:
- Smelt 9 iron ore into 9 iron plates
- Smelt 15 copper ore into 15 copper plates
"""
# Inventory at the start of step {'coal': 5, 'stone': 2, 'iron-ore': 9, 'copper-ore': 15}
#Step Execution

# Get reference to both furnaces
stone_furnaces = get_entities({Prototype.StoneFurnace})
assert len(stone_furnaces) >= 2, "Expected at least two Stone Furnaces on map"

# Assigning specific roles to each furnace
iron_furnace = next(f for f in stone_furnaces if f.position == Position(x=-14.0, y=-12.0))
copper_furnace = next(f for f in stone_furnaces if f.position == Position(x=-10.0, y=-12.0))

# Insert Iron Ore into Furnace dedicated for Iron Plates
print("Inserting Iron Ore into Furnace dedicated for Iron Plates")
insert_item(Prototype.IronOre, iron_furnace, quantity=9)

# Insert Copper Ore into Furnace dedicated for Copper Plates
print("Inserting Copper Ore into Furnace dedicated for Copper Plates")
insert_item(Prototype.CopperOre, copper_furnace, quantity=15)

# Calculate total waiting time needed based on maximum number of items being smelted concurrently
total_wait_time = max(9 * 0.7, 15 * 0.7)
print(f"Waiting {total_wait_time} seconds for smelting process to complete...")
sleep(total_wait_time)

# Extract Smelted Iron Plates from corresponding Furnace
extract_item(Prototype.IronPlate, iron_furnace.position, quantity=9)
print("Extracted Iron Plates")

# Extract Smelted Copper Plates from corresponding Furnace
extract_item(Prototype.CopperPlate, copper_furnace.position, quantity=15)
print("Extracted Copper Plates")

# Verify success by checking updated inventory counts
inventory_after_smelting = inspect_inventory()
assert inventory_after_smelting.get(Prototype.IronPlate) >= 9,\
    f"Failed to obtain enough Iron Plates; expected at least 9 but got {inventory_after_smelting.get(Prototype.IronPlate)}"
assert inventory_after_smelting.get(Prototype.CopperPlate) >= 15,\
    f"Failed to obtain enough Copper Plates; expected at least 15 but got {inventory_after_smelting.get(Prototype.CopperPlate)}"

print("Successfully completed smelting operation.")


"""
Step 6: Craft copper cables. We need to craft 21 copper cables using 11 copper plates.
"""
# Inventory at the start of step {'coal': 5, 'stone': 2, 'iron-plate': 9, 'copper-plate': 15}
#Step Execution

# Check initial amount of Copper Plates in Inventory
copper_plates_in_inventory = inspect_inventory().get(Prototype.CopperPlate, 0)
print(f"Initial Copper Plates in Inventory: {copper_plates_in_inventory}")

# Ensure we have enough Copper Plates to craft Copper Cables
assert copper_plates_in_inventory >= 11, f"Not enough Copper Plates! Expected at least 11 but found {copper_plates_in_inventory}"

# Crafting Copper Cables
print("Crafting 21 Copper Cables...")
crafted_cables = craft_item(Prototype.CopperCable, quantity=21)

# Log how many were crafted successfully
print(f"Crafted {crafted_cables} Copper Cables")

# Verify success by checking updated inventory counts
inventory_after_crafting = inspect_inventory()
copper_cable_count = inventory_after_crafting.get(Prototype.CopperCable, 0)
assert copper_cable_count >= 21, f"Failed to craft enough Copper Cables; expected at least 21 but got {copper_cable_count}"

print("Successfully crafted all required Copper Cables.")


"""
Step 7: Craft electronic circuits. We need to craft 7 electronic circuits using 21 copper cables and 7 iron plates.
"""
# Inventory at the start of step {'coal': 5, 'stone': 2, 'iron-plate': 9, 'copper-plate': 4, 'copper-cable': 22}
#Step Execution

# Check current inventory for required materials
current_inventory = inspect_inventory()
copper_cables_in_inventory = current_inventory.get(Prototype.CopperCable, 0)
iron_plates_in_inventory = current_inventory.get(Prototype.IronPlate, 0)

print(f"Current Copper Cables in Inventory: {copper_cables_in_inventory}")
print(f"Current Iron Plates in Inventory: {iron_plates_in_inventory}")

# Ensure we have enough materials
assert copper_cables_in_inventory >= 21, f"Not enough Copper Cables! Expected at least 21 but found {copper_cables_in_inventory}"
assert iron_plates_in_inventory >= 7, f"Not enough Iron Plates! Expected at least 7 but found {iron_plates_in_inventory}"

# Crafting Electronic Circuits
print("Crafting 7 Electronic Circuits...")
crafted_electronic_circuits = craft_item(Prototype.ElectronicCircuit, quantity=7)

# Log how many were crafted successfully
print(f"Crafted {crafted_electronic_circuits} Electronic Circuits")

# Verify success by checking updated inventory counts
inventory_after_crafting = inspect_inventory()
electronic_circuit_count = inventory_after_crafting.get(Prototype.ElectronicCircuit, 0)
assert electronic_circuit_count >= 7, f"Failed to craft enough Electronic Circuits; expected at least 7 but got {electronic_circuit_count}"

print("Successfully crafted all required Electronic Circuits.")


"""
Step 8: Verify success. Check the inventory to ensure we have 7 electronic circuits.

##
"""
# Inventory at the start of step {'coal': 5, 'stone': 2, 'iron-plate': 2, 'copper-plate': 4, 'copper-cable': 1, 'electronic-circuit': 7}
#Step Execution

# Step 8: Verify success

# Inspecting current inventory
current_inventory = inspect_inventory()
electronic_circuit_count = current_inventory.get(Prototype.ElectronicCircuit, 0)
print(f"Current Electronic Circuits in Inventory: {electronic_circuit_count}")

# Verify that we have at least 7 electronic circuits
assert electronic_circuit_count >= 7, f"Failed to obtain enough Electronic Circuits; expected at least 7 but got {electronic_circuit_count}"

print("Successfully verified that we have all required Electronic Circuits.")
