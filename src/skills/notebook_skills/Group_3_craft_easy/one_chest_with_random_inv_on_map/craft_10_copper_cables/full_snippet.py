from factorio_instance import *

"""
Main Objective: We need to craft 10 copper cables. The final success should be checked by looking if the copper cables are in inventory
"""



"""
Step 1: Print recipe for copper cable
- Print the recipe for copper cable
"""
# Inventory at the start of step {}
#Step Execution

# Fetching the recipe for copper cable
copper_cable_recipe = get_prototype_recipe('copper-cable')

# Printing out the recipe details
print("Copper Cable Recipe:")
print(copper_cable_recipe)


"""
Step 2: Gather resources. We need to gather the following:
- Mine 4 additional copper ore
- Gather 5 stone to craft a stone furnace
- Take the coal and copper ore from the wooden chest on the map
"""
# Inventory at the start of step {}
#Step Execution

# Define required resources
resources_to_mine = [
    (Prototype.CopperOre, 4),
    (Prototype.Stone, 5)
]

# Loop through each resource type we need to mine
for resource_prototype, amount_needed in resources_to_mine:
    # Find nearest resource patch
    resource_position = nearest(resource_prototype)
    
    # Move towards this position
    move_to(resource_position)
    
    # Harvest specified amount
    harvested_amount = harvest_resource(resource_position, amount_needed)
    
    # Check if sufficient quantity was mined
    current_inventory_count = inspect_inventory()[resource_prototype]
    assert current_inventory_count >= amount_needed, f"Not enough {resource_prototype.value[0]}. Expected {amount_needed}, got {current_inventory_count}"
    
    print(f"Mined {harvested_amount} units of {resource_prototype.value[0]}. Current inventory: {inspect_inventory()}")

# Now handle extraction from wooden chest

# Get list of entities around us including chests
wooden_chests = get_entities({Prototype.WoodenChest})

if wooden_chests:
    wooden_chest = wooden_chests[0]
    # Move near the chest's position first 
    move_to(wooden_chest.position)

    # Extract all available coal from chest's inventory
    coal_extracted = extract_item(Prototype.Coal, wooden_chest.position, quantity=19)
    
    # Extract single unit of available copper-ore as planned earlier 
    copper_ore_extracted = extract_item(Prototype.CopperOre, wooden_chest.position, quantity=1)

    # Ensure successful extraction by checking updated inventory state
    inventory_after_extraction = inspect_inventory()
    assert inventory_after_extraction[Prototype.Coal] >= 19, f"Failed to extract enough coal. Expected at least 19, but got {inventory_after_extraction[Prototype.Coal]}"
    assert inventory_after_extraction[Prototype.CopperOre] >= 5, f"Failed to extract enough copper ore. Expected at least 5, but got {inventory_after_extraction[Prototype.CopperOre]}"

    print("Successfully extracted items from Wooden Chest.")
else:
    print("No accessible Wooden Chest found!")

final_inventory_state = inspect_inventory() 
print(f"Final Inventory after gathering resources: {final_inventory_state}")


"""
Step 3: Craft stone furnace
- Print the recipe for stone furnace
- Craft 1 stone furnace using the 5 stone gathered
"""
# Inventory at the start of step {'coal': 19, 'stone': 5, 'copper-ore': 5}
#Step Execution

# Fetching and printing the recipe for a Stone Furnace
stone_furnace_recipe = get_prototype_recipe('stone-furnace')
print("Stone Furnace Recipe:")
print(stone_furnace_recipe)

# Crafting a Stone Furnace
crafted_stone_furnaces = craft_item(Prototype.StoneFurnace, 1)
print(f"Crafted {crafted_stone_furnaces} Stone Furnace(s)")

# Verify if we successfully crafted at least one Stone Furnace
inventory_after_crafting = inspect_inventory()
assert inventory_after_crafting[Prototype.StoneFurnace] >= 1, f"Failed to craft Stone Furnace. Expected at least 1, but got {inventory_after_crafting.get(Prototype.StoneFurnace, 0)}"
print("Successfully crafted a Stone Furnace.")


"""
Step 4: Smelt copper plates. We need to smelt 5 copper ore into 5 copper plates:
- Place the stone furnace
- Fuel the stone furnace with coal from the wooden chest
- Put 5 copper ore into the furnace (1 from chest, 4 from mining)
- Wait for the smelting to complete
"""
# Inventory at the start of step {'stone-furnace': 1, 'coal': 19, 'copper-ore': 5}
#Step Execution

# Step 4 Code Implementation

# Assume that we've already got access to necessary imports and classes

# Step A: Placing Stone Furnace
print("Step A: Placing Stone Furnace")

# Let's find an optimal position near us or any resource patch
placement_position = Position(x=-10, y=-10) # Example position, adjust based on your strategy

# Move near placement location - not asserting move_to due to API limitations mentioned
move_to(placement_position)

# Place stone-furnace at chosen position
stone_furnace = place_entity(Prototype.StoneFurnace, Direction.UP, placement_position)
print(f"Placed Stone Furnace at {placement_position}")

# Step B: Fueling Stone Furnace with Coal
print("Step B: Fueling Stone Furnace")
coal_in_inventory = inspect_inventory()[Prototype.Coal]
stone_furnace = insert_item(Prototype.Coal, stone_furnace, coal_in_inventory)
print(f"Inserted {coal_in_inventory} coal into Stone Furnace")

# Step C: Inserting Copper Ore into Stone Furnace
print("Step C: Inserting Copper Ore")
copper_ore_in_inventory = inspect_inventory()[Prototype.CopperOre]
stone_furnace = insert_item(Prototype.CopperOre, stone_furnace, copper_ore_in_inventory)
print(f"Inserted {copper_ore_in_inventory} copper ore into Stone Furnace")

# Step D: Waiting for Smelting Completion
smelting_time_per_unit = 0.7 # Assuming each unit takes approximately 0.7 seconds to process
total_smelting_time = smelting_time_per_unit * copper_ore_in_inventory

sleep(total_smelting_time)
print("Smelting completed.")

inventory_after_smelting_attempts = inspect_inventory()
expected_copper_plate_count = inventory_after_smelting_attempts.get(Prototype.CopperPlate, 0) + copper_ore_in_inventory

max_check_attempts = 5 
for _ in range(max_check_attempts):
    extract_item(Prototype.CopperPlate, stone_furnace.position,copper_ore_in_inventory)
    current_copper_plate_count=inspect_inventory().get(Prototype.CopperPlate ,0)

    if current_copper_plate_count >= expected_copper_plate_count:
        break
    
    sleep(sleep_duration_between_checks)

assert current_copper_plate_count >= expected_copper_plate_count,"Failed extracting required number of plates"


"""
Step 5: Craft copper cables
- Take the 5 copper plates from the furnace
- Craft 10 copper cables using the 5 copper plates
"""
# Inventory at the start of step {'copper-plate': 5}
#Step Execution

# Step A: Verify copper plates in inventory
print("Step A: Verifying Copper Plates in Inventory")

current_inventory = inspect_inventory()
copper_plates_in_inventory = current_inventory.get(Prototype.CopperPlate, 0)

print(f"Current Inventory before crafting: {current_inventory}")
print(f"Copper Plates available: {copper_plates_in_inventory}")

# Ensure we have required number of copper plates before attempting to craft
required_copper_plates_for_cables = 5
assert copper_plates_in_inventory >= required_copper_plates_for_cables,\
    f"Insufficient Copper Plates! Expected at least {required_copper_plates_for_cables}, but got {copper_plates_in_inventory}"

# Step B: Crafting Copper Cables
print("Step B: Crafting Copper Cables")

crafted_copper_cables = craft_item(Prototype.CopperCable, quantity=10)
print(f"Crafted {crafted_copper_cables} Copper Cable(s)")

# Step C: Validate successful crafting of Copper Cables
final_inventory_after_crafting = inspect_inventory()
final_count_of_copper_cables = final_inventory_after_crafting.get(Prototype.CopperCable, 0)

assert final_count_of_copper_cables == 10,\
    f"Failed to craft sufficient Copper Cables! Expected exactly 10, but got {final_count_of_copper_cables}"

print("Successfully crafted 10 Copper Cables.")
print(f"Final Inventory after crafting: {final_inventory_after_crafting}")


"""
Step 6: Check inventory
- Check if 10 copper cables are in the inventory
##
"""
# Inventory at the start of step {'copper-cable': 10}
#Step Execution

# Step: Check Inventory for Copper Cables

# Inspecting current inventory
current_inventory = inspect_inventory()
print(f"Current Inventory: {current_inventory}")

# Get number of copper cables from inventory
copper_cable_count = current_inventory.get(Prototype.CopperCable, 0)
print(f"Copper Cables in Inventory: {copper_cable_count}")

# Assert that there are exactly 10 copper cables in the inventory
assert copper_cable_count == 10, f"Inventory check failed! Expected 10 Copper Cables, but found {copper_cable_count}"

print("Successfully verified presence of 10 Copper Cables in Inventory.")
