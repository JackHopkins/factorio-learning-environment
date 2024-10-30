from factorio_instance import *

"""
Main Objective: We require one BurnerInserter. The final success should be checked by looking if a BurnerInserter is in inventory
"""



"""
Step 1: Mine resources
- Move to the nearest coal patch and mine at least 5 coal
- Move to the nearest iron ore patch and mine at least 3 iron ore
OUTPUT CHECK: Check if we have at least 5 coal and 3 iron ore in the inventory
"""
# Inventory at the start of step {}
#Step Execution

# Step 1: Mine resources

# Identify resource locations
coal_position = nearest(Resource.Coal)
iron_ore_position = nearest(Resource.IronOre)

# Move to Coal Patch
print(f"Moving to nearest coal patch at {coal_position}")
move_to(coal_position)

# Mine Coal
print("Mining coal...")
harvested_coal = harvest_resource(coal_position, quantity=5)
print(f"Mined {harvested_coal} units of coal")

# Verify Coal Quantity
current_inventory = inspect_inventory()
coal_in_inventory = current_inventory.get('coal', 0)
assert coal_in_inventory >= 5, f"Failed mining enough coal! Expected at least 5 but got {coal_in_inventory}"
print(f"Current Inventory after mining coal: {current_inventory}")

# Move to Iron Ore Patch
print(f"Moving to nearest iron ore patch at {iron_ore_position}")
move_to(iron_ore_position)

# Mine Iron Ore
print("Mining iron ore...")
harvested_iron_ore = harvest_resource(iron_ore_position, quantity=3)
print(f"Mined {harvested_iron_ore} units of iron ore")

# Verify Iron Ore Quantity
current_inventory = inspect_inventory()
iron_ore_in_inventory = current_inventory.get('iron-ore', 0)
assert iron_ore_in_inventory >= 3, f"Failed mining enough iron ore! Expected at least 3 but got {iron_ore_in_inventory}"
print(f"Current Inventory after mining iron ore: {current_inventory}")

final_coal_count = inspect_inventory().get('coal', 0)
final_iron_count = inspect_inventory().get('iron-ore', 0)

assert final_coal_count >= 5 and final_iron_count >= 3, "Resource gathering failed!"
print("Successfully gathered required resources!")


"""
Step 2: Prepare the furnace
- Move to the existing stone furnace at position (-12.0, -12.0)
- Add coal to the furnace as fuel
OUTPUT CHECK: Check if the furnace status changes from NO_FUEL to IDLE
"""
# Inventory at the start of step {'coal': 5, 'iron-ore': 3}
#Step Execution

# Step 2: Prepare the furnace

# Move to the existing stone furnace location
furnace_position = Position(x=-12.0, y=-12.0)
print(f"Moving to stone furnace at {furnace_position}")
move_to(furnace_position)

# Get reference to stone furnace entity
stone_furnaces = get_entities({Prototype.StoneFurnace})
stone_furnace = next((f for f in stone_furnaces if f.position.is_close(furnace_position)), None)

if not stone_furnace:
    raise Exception("Stone furnace not found!")

# Check initial status of the furnace
initial_status = stone_furnace.status
print(f"Initial status of the furnace: {initial_status}")

# Add coal as fuel to the stone furnace
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
if coal_in_inventory > 0:
    print(f"Inserting {coal_in_inventory} units of coal into the furnace")
    stone_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=coal_in_inventory)
else:
    raise Exception("No coal available in inventory!")

# Wait for the furnace to process the fuel and reach a valid state
print("Waiting for furnace to process fuel...")
max_attempts = 10
for _ in range(max_attempts):
    sleep(2)
    updated_stone_furnaces = get_entities({Prototype.StoneFurnace})
    updated_stone_furnace = next((f for f in updated_stone_furnaces if f.position.is_close(furnace_position)), None)
    
    if not updated_stone_furnace:
        raise Exception("Updated state of Stone Furnace could not be retrieved!")
    
    updated_status = updated_stone_furnace.status
    print(f"Current status of the furnace: {updated_status}")
    
    if updated_status in [EntityStatus.NORMAL, EntityStatus.NO_INGREDIENTS]:
        print("Successfully prepared and fueled up the Stone Furnace!")
        break
else:
    raise Exception(f"Furnace did not reach expected state after {max_attempts} attempts. Last status: {updated_status}")

assert updated_status != EntityStatus.NO_FUEL, "Failed! The Stone Furnace is still out of fuel."
assert updated_status in [EntityStatus.NORMAL, EntityStatus.NO_INGREDIENTS], \
       f"Unexpected status after fueling! Status: {updated_status}"

print(f"Final status of the furnace after fueling: {updated_status}")


"""
Step 3: Smelt iron plates
- Add iron ore to the furnace
- Wait for the smelting process to complete (3 seconds for 3 iron ore)
OUTPUT CHECK: Check if we have at least 3 iron plates in the inventory
"""
# Inventory at the start of step {'iron-ore': 3}
#Step Execution

# Step 3: Smelt Iron Plates

# Get reference to stone furnace entity again
stone_furnaces = get_entities({Prototype.StoneFurnace})
stone_furnace = next((f for f in stone_furnaces if f.position.is_close(Position(x=-12.0, y=-12.0))), None)

if not stone_furnace:
    raise Exception("Stone furnace not found!")

# Check initial status of the furnace
initial_status = stone_furnace.status
print(f"Initial status of the furnace before adding iron ore: {initial_status}")

# Add all available iron ore to the stone furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
if iron_ore_in_inventory > 0:
    print(f"Inserting {iron_ore_in_inventory} units of iron ore into the furnace")
    stone_furnace = insert_item(Prototype.IronOre, stone_furnace, quantity=iron_ore_in_inventory)
else:
    raise Exception("No iron ore available in inventory!")

# Wait for smelting process to complete (assuming it takes about 1 second per unit)
smelting_time_seconds = 3 * 1 # For each unit of Iron Ore
print(f"Waiting {smelting_time_seconds} seconds for smelting process...")
sleep(smelting_time_seconds)

# Attempt to extract produced Iron Plates from Furnace
max_attempts = 5
for _ in range(max_attempts):
    # Try extracting expected number of items or more than needed 
    extract_item(Prototype.IronPlate, stone_furnace.position, quantity=iron_ore_in_inventory)
    
    # Check current inventory count after extraction attempt 
    current_iron_plate_count = inspect_inventory().get('iron-plate', 0)
    
    # If enough plates have been extracted successfully then break out loop early  
    if current_iron_plate_count >= 3:
        break
    
    sleep(10) # Additional waiting period between attempts 

print(f"Extracted up-to-date Iron Plates; Current Inventory: {inspect_inventory()}")

# Assert final condition - Ensure minimum required output achieved 
assert current_iron_plate_count >= 3 , "Failed! Not enough Iron Plates were obtained."
print("Successfully completed smelting step!")


"""
Step 4: Craft iron gear wheel
- Craft 1 iron gear wheel using 2 iron plates
OUTPUT CHECK: Check if we have 1 iron gear wheel in the inventory
"""
# Inventory at the start of step {'iron-plate': 3}
#Step Execution

# Step 4: Craft Iron Gear Wheel

# Check current inventory for available resources
current_inventory = inspect_inventory()
iron_plate_count = current_inventory.get('iron-plate', 0)
print(f"Current Inventory before crafting Iron Gear Wheel: {current_inventory}")

# Ensure we have enough iron plates to craft an Iron Gear Wheel
assert iron_plate_count >= 2, f"Not enough Iron Plates! Required: 2, Available: {iron_plate_count}"

# Crafting Iron Gear Wheel
craft_item(Prototype.IronGearWheel, quantity=1)
print("Crafted 1 Iron Gear Wheel")

# Verify that we have crafted at least one Iron Gear Wheel
gear_wheel_count = inspect_inventory().get('iron-gear-wheel', 0)
assert gear_wheel_count >= 1, f"Failed to craft Iron Gear Wheel! Expected at least 1 but got {gear_wheel_count}"
print(f"Successfully crafted an Iron Gear Wheel! Current Inventory: {inspect_inventory()}")


"""
Step 5: Craft BurnerInserter
- Craft 1 BurnerInserter using 1 iron gear wheel and 1 iron plate
OUTPUT CHECK: Check if we have 1 BurnerInserter in the inventory

##
"""
# Inventory at the start of step {'iron-plate': 1, 'iron-gear-wheel': 1}
#Step Execution

# Step 5: Craft Burner Inserter

# Check current inventory for required resources
current_inventory = inspect_inventory()
iron_plate_count = current_inventory.get('iron-plate', 0)
gear_wheel_count = current_inventory.get('iron-gear-wheel', 0)

print(f"Current Inventory before crafting Burner Inserter: {current_inventory}")

# Ensure we have enough materials to craft a Burner Inserter
assert iron_plate_count >= 1, f"Not enough Iron Plates! Required: 1, Available: {iron_plate_count}"
assert gear_wheel_count >= 1, f"Not enough Iron Gear Wheels! Required: 1, Available: {gear_wheel_count}"

# Crafting the Burner Inserter
craft_item(Prototype.BurnerInserter, quantity=1)
print("Crafted 1 Burner Inserter")

# Verify that we have crafted at least one Burner Inserter
burner_inserter_count = inspect_inventory().get('burner-inserter', 0)
assert burner_inserter_count >= 1, f"Failed to craft a Burner Inserter! Expected at least 1 but got {burner_inserter_count}"

print(f"Successfully crafted a Burner Inserter! Current Inventory: {inspect_inventory()}")
