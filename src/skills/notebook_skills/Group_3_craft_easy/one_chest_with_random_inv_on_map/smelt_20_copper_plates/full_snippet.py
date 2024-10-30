from factorio_instance import *

"""
Main Objective: We need to craft 18 copper plates. The final success should be checked by looking if the copper plates are in inventory
"""



"""
Step 1: Craft a stone furnace. We need to:
- Move to the wooden chest
- Take 5 stone from the chest
- Craft a stone furnace
"""
# Inventory at the start of step {}
#Step Execution

# Step 1: Move to the wooden chest
chest_position = Position(x=-11.5, y=-11.5)
move_to(chest_position)
print(f"Moved to wooden chest at position {chest_position}")

# Step 2: Take 5 stone from the chest
stone_needed = 5
extract_item(Prototype.Stone, chest_position, quantity=stone_needed)
print(f"Extracted {stone_needed} stone from wooden chest")

# Verify extraction by checking inventory
inventory_after_extraction = inspect_inventory()
assert inventory_after_extraction[Prototype.Stone] >= stone_needed, f"Failed to extract {stone_needed} stones"

# Step 3: Craft a stone furnace
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted {crafted_furnaces} Stone Furnace(s)")

# Assert that exactly one Stone Furnace was crafted successfully
assert crafted_furnaces == 1, "Stone Furnace crafting failed"
print("Successfully completed step - Crafted a Stone Furnace")


"""
Step 2: Mine copper ore. We need to:
- Find the nearest copper ore patch
- Mine 18 copper ore by hand
"""
# Inventory at the start of step {'stone-furnace': 1}
#Step Execution

# Find the nearest copper ore patch
copper_ore_position = nearest(Resource.CopperOre)
print(f"Nearest Copper Ore found at position {copper_ore_position}")

# Move to the copper ore patch
move_to(copper_ore_position)
print(f"Moved to Copper Ore patch at position {copper_ore_position}")

# Define amount of copper ore needed
copper_ore_needed = 18

# Harvest required amount of copper ore
harvested_copper_ore = harvest_resource(copper_ore_position, quantity=copper_ore_needed)
print(f"Harvested {harvested_copper_ore} Copper Ore")

# Verify harvesting by checking inventory
inventory_after_harvesting = inspect_inventory()
actual_copper_in_inventory = inventory_after_harvesting[Prototype.CopperOre]
assert actual_copper_in_inventory >= copper_ore_needed, f"Failed to harvest enough Copper Ore. Expected: {copper_ore_needed}, but got: {actual_copper_in_inventory}"

print("Successfully completed step - Mined required Copper Ore")


"""
Step 3: Set up the smelting process. We need to:
- Move back to the wooden chest
- Take 7 coal from the chest
- Place the stone furnace near the chest
- Add coal to the furnace for fuel
"""
# Inventory at the start of step {'stone-furnace': 1, 'copper-ore': 18}
#Step Execution

# Step 1: Move back to the wooden chest
chest_position = Position(x=-11.5, y=-11.5)
move_to(chest_position)
print(f"Moved back to wooden chest at position {chest_position}")

# Step 2: Take 7 coal from the chest
coal_needed = 7
extract_item(Prototype.Coal, chest_position, quantity=coal_needed)
print(f"Extracted {coal_needed} coal from wooden chest")

# Verify extraction by checking inventory
inventory_after_coal_extraction = inspect_inventory()
assert inventory_after_coal_extraction[Prototype.Coal] >= coal_needed, f"Failed to extract {coal_needed} coals"

# Step 3: Place stone furnace near the chest
furnace_position = Position(x=chest_position.x + 1, y=chest_position.y) # Placing it right next to or nearby on x-axis
stone_furnace_entity = place_entity(Prototype.StoneFurnace, Direction.UP, furnace_position)
print(f"Placed Stone Furnace at position {furnace_position}")

# Step 4: Add coal to stone furnace as fuel
stone_furnace_entity = insert_item(Prototype.Coal, stone_furnace_entity, quantity=coal_needed)
print(f"Inserted {coal_needed} coal into Stone Furnace")


"""
Step 4: Smelt copper ore into copper plates. We need to:
- Add copper ore to the furnace
- Wait for the smelting process to complete (18 seconds, as each ore takes 1 second to smelt)
- Collect the copper plates from the furnace
"""
# Inventory at the start of step {'copper-ore': 18}
#Step Execution

# Step 1: Add copper ore to the stone furnace

# Get the stone furnace entity
stone_furnace = get_entity(Prototype.StoneFurnace, Position(x=-10.5, y=-11.5))

# Insert all available copper ore into the stone furnace
copper_ore_in_inventory = inspect_inventory()[Prototype.CopperOre]
print(f"Copper ore in inventory before insertion: {copper_ore_in_inventory}")

stone_furnace = insert_item(Prototype.CopperOre, stone_furnace, quantity=copper_ore_in_inventory)
print(f"Inserted {copper_ore_in_inventory} copper ore into Stone Furnace")

# Step 2: Wait for smelting process to complete
smelting_time_per_ore = 1 # second per unit
total_smelting_time = smelting_time_per_ore * copper_ore_in_inventory
sleep(total_smelting_time)
print(f"Waited {total_smelting_time} seconds for smelting")

# Step 3: Collect the resulting copper plates from the furnace

# Attempt extraction of expected number of copper plates after smelting
expected_copper_plate_count = copper_ore_in_inventory

max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.CopperPlate, stone_furnace.position, expected_copper_plate_count)

    # Check current inventory for extracted plates count
    current_copper_plate_count = inspect_inventory()[Prototype.CopperPlate]

    if current_copper_plate_count >= expected_copper_plate_count:
        break
    
    sleep(10) # Wait a bit more if not all plates are ready yet

print(f"Extracted {current_copper_plate_count} Copper Plates from Stone Furnace")
print(f"Inventory after extracting Copper Plates: {inspect_inventory()}")

assert current_copper_plate_count >= expected_copper_plate_count, f"Failed to extract enough Copper Plates. Expected at least {expected_copper_plate_count}, but got {current_copper_plate_count}"

print("Successfully completed step - Smelted Copper Ore into Copper Plates")


"""
Step 5: Verify the crafting process. We need to:
- Check the inventory to confirm we have 18 copper plates
##
"""
# Inventory at the start of step {'copper-plate': 18}
#Step Execution

# Step: Verify the crafting process

# Check current inventory for number of copper plates
current_inventory = inspect_inventory()
copper_plate_count = current_inventory[Prototype.CopperPlate]
print(f"Current Copper Plate count in inventory: {copper_plate_count}")

# Assert that there are at least 18 copper plates in the inventory
assert copper_plate_count >= 18, f"Verification failed! Expected at least 18 Copper Plates but found {copper_plate_count}"

print("Successfully verified crafting process - Inventory contains at least 18 Copper Plates")
