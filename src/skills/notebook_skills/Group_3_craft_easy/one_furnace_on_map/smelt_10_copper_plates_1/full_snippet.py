from factorio_instance import *

"""
Main Objective: We need 10 copper plates. The final success should be checked by looking if the copper plates are in inventory
"""



"""
Step 1: Gather coal
- Move to the nearest coal patch
- Manually mine at least 15 coal (10 for smelting, 5 for buffer)
OUTPUT CHECK: Verify that we have at least 15 coal in our inventory
"""
# Inventory at the start of step{}
#Step Execution

# Find the nearest coal resource
coal_position = nearest(Resource.Coal)
print(f"Nearest Coal Position: {coal_position}")

# Move to the nearest coal patch
move_to(coal_position)
print("Moved to the nearest coal patch.")

# Mine at least 15 units of coal
harvested_coal = harvest_resource(coal_position, quantity=15)
print(f"Harvested {harvested_coal} units of coal.")

# Check if we have mined enough coal
current_inventory = inspect_inventory()
coal_in_inventory = current_inventory.get(Prototype.Coal, 0)
print(f"Current Coal in Inventory: {coal_in_inventory}")

# Assert that we have at least 15 units of coal in our inventory
assert coal_in_inventory >= 15, f"Failed to gather enough coal. Expected at least 15 but got {coal_in_inventory}"

print("Successfully gathered enough coal.")


"""
Step 2: Mine copper ore
- Move to the nearest copper ore patch
- Manually mine at least 10 copper ore
OUTPUT CHECK: Verify that we have at least 10 copper ore in our inventory
"""
# Inventory at the start of step{'coal': 15}
#Step Execution

# Find the nearest copper ore resource
copper_position = nearest(Resource.CopperOre)
print(f"Nearest Copper Position: {copper_position}")

# Move to the nearest copper ore patch
move_to(copper_position)
print("Moved to the nearest copper ore patch.")

# Mine at least 10 units of copper ore
harvested_copper = harvest_resource(copper_position, quantity=10)
print(f"Harvested {harvested_copper} units of copper ore.")

# Check if we have mined enough copper ore
current_inventory = inspect_inventory()
copper_in_inventory = current_inventory.get(Prototype.CopperOre, 0)
print(f"Current Copper Ore in Inventory: {copper_in_inventory}")

# Assert that we have at least 10 units of copper ore in our inventory
assert copper_in_inventory >= 10, f"Failed to gather enough copper ore. Expected at least 10 but got {copper_in_inventory}"

print("Successfully gathered enough copper ore.")


"""
Step 3: Fuel the furnace
- Move to the stone furnace at position (-12.0, -12.0)
- Insert 10 coal into the furnace as fuel
OUTPUT CHECK: Verify that the furnace's fuel status is no longer 'no fuel'
"""
# Inventory at the start of step{'coal': 15, 'copper-ore': 10}
#Step Execution

# Step 3: Fueling the Furnace

# Get position of stone furnace
furnace_position = Position(x=-12.0, y=-12.0)
print(f"Stone Furnace Position: {furnace_position}")

# Move to the stone furnace
move_to(furnace_position)
print("Moved to the stone furnace.")

# Inspect current inventory for available coal
current_inventory = inspect_inventory()
coal_in_inventory = current_inventory.get(Prototype.Coal, 0)
print(f"Coal available in inventory: {coal_in_inventory}")

# Check if there is enough coal before proceeding
assert coal_in_inventory >= 10, f"Not enough coal in inventory to fuel the furnace."

# Insert 10 units of coal into the stone furnace
stone_furnace = get_entity(Prototype.StoneFurnace, furnace_position)
stone_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=10)
print("Inserted 10 units of coal into the stone-furnace.")

# Verify that the status is no longer 'no fuel'
assert EntityStatus.NO_FUEL not in [status.value for status in [stone_furnace.status]], "The stone-furnace still shows 'no fuel' status."
print("Successfully fueled the stove-furnace.")


"""
Step 4: Smelt copper plates
- Insert 10 copper ore into the furnace
- Wait for the smelting process to complete (approximately 10 seconds, as each copper ore takes 1 second to smelt)
- Collect the 10 copper plates from the furnace
OUTPUT CHECK: Verify that we have 10 copper plates in our inventory

##
"""
# Inventory at the start of step{'coal': 5, 'copper-ore': 10}
#Step Execution

# Get the stone furnace entity
stone_furnace = get_entity(Prototype.StoneFurnace, Position(x=-12.0, y=-12.0))

# Insert 10 copper ore into the stone furnace
stone_furnace = insert_item(Prototype.CopperOre, stone_furnace, quantity=10)
print("Inserted 10 units of copper ore into the stone-furnace.")

# Wait for smelting process to complete (approximately 1 second per unit of copper ore)
smelting_time = 10 # seconds
sleep(smelting_time)
print(f"Waited {smelting_time} seconds for smelting process to complete.")

# Extract the resulting copper plates from the furnace
copper_plates_in_furnace = inspect_inventory(stone_furnace).get(Prototype.CopperPlate, 0)
extract_item(Prototype.CopperPlate, stone_furnace.position, quantity=copper_plates_in_furnace)
print(f"Extracted {copper_plates_in_furnace} units of copper plate from the furnace.")

# Verify that we have at least 10 units of copper plates in our inventory
current_inventory = inspect_inventory()
copper_plate_count = current_inventory.get(Prototype.CopperPlate, 0)
print(f"Current Copper Plates in Inventory: {copper_plate_count}")

assert copper_plate_count >= 10, f"Failed to gather enough copper plates. Expected at least 10 but got {copper_plate_count}"

print("Successfully gathered enough copper plates.")
