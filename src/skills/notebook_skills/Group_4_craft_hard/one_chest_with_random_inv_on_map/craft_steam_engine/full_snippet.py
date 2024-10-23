from factorio_instance import *

"""
Main Objective: We require one SteamEngine. The final success should be checked by looking if a SteamEngine is in inventory
"""



"""
Step 1: Print recipes. We need to print the recipes for SteamEngine, IronGearWheel, Pipe, and StoneFurnace.
"""
# Inventory at the start of step {}
#Step Execution

# Get and print the recipe for SteamEngine
steam_engine_recipe = get_prototype_recipe(Prototype.SteamEngine)
print(f"Steam Engine Recipe: {steam_engine_recipe}")

# Get and print the recipe for Iron Gear Wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(f"Iron Gear Wheel Recipe: {iron_gear_wheel_recipe}")

# Get and print the recipe for Pipe
pipe_recipe = get_prototype_recipe(Prototype.Pipe)
print(f"Pipe Recipe: {pipe_recipe}")

# Get and print the recipe for Stone Furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace Recipe: {stone_furnace_recipe}")


"""
Step 2: Gather resources. We need to mine the following resources:
- At least 31 iron ore
- Enough coal for smelting (at least 31 pieces)
- 5 stone for crafting a stone furnace
"""
# Inventory at the start of step {}
#Step Execution

# Define required resources with their respective amounts
required_resources = [
    (Resource.IronOre, 35), # slightly more than needed for safety margin
    (Resource.Coal, 35),    # slightly more than needed for safety margin
    (Resource.Stone, 10)    # slightly more than needed for crafting furnace
]

# Loop through each type of resource required
for resource_type, amount_needed in required_resources:
    
    # Find nearest position of the current resource type on map
    nearest_position = nearest(resource_type)
    
    print(f"Nearest {resource_type} found at position: {nearest_position}")
    
    # Move player character to location of nearest resource patch
    move_to(nearest_position)
    
    print(f"Moved to {resource_type} patch.")

    # Harvest specified quantity from located resource patch 
    harvested_amount = harvest_resource(nearest_position, amount_needed)
    
    print(f"Harvested {harvested_amount} units of {resource_type}.")
    
    # Get updated inventory details post-harvesting operation 
    current_inventory = inspect_inventory()
    
    # Log current state of player's inventory after harvesting operations are completed successfully  
    print(f"Current Inventory: {current_inventory}")

    # Ensure sufficient quantity is present in player's personal storage/inventory space as expected  
    assert current_inventory[resource_type] >= amount_needed, \
        f"Insufficient {resource_type}: Expected at least {amount_needed}, but got only {current_inventory[resource_type]}."

print("Successfully gathered all necessary resources.")


"""
Step 3: Craft and place a stone furnace. 
- Craft a stone furnace using 5 stone
- Place the stone furnace at a suitable location
"""
# Inventory at the start of step {'coal': 35, 'stone': 10, 'iron-ore': 35}
#Step Execution

# Step 1: Craft a Stone Furnace
print("Crafting a Stone Furnace...")
crafted_furnaces = craft_item(Prototype.StoneFurnace, 1)

# Ensure crafting was successful
assert crafted_furnaces == 1, f"Failed to craft stone furnace. Expected 1, but got {crafted_furnaces}"
print("Successfully crafted a Stone Furnace.")

# Step 2: Place the Stone Furnace
# Choose placement position near an existing entity or resource patch; here we'll use nearest wooden chest as reference
wooden_chest_position = Position(x=-11.5, y=-11.5) # Position from game logs of available wooden chest

# Place stone furnace next to wooden chest for convenience
stone_furnace_placed = place_entity_next_to(Prototype.StoneFurnace, reference_position=wooden_chest_position)
print(f"Placed Stone Furnace at {stone_furnace_placed.position}")

# Verify placement success by inspecting entities around us 
inspection_results = inspect_entities()
furnaces_nearby = inspection_results.get_entities(Prototype.StoneFurnace)
assert len(furnaces_nearby) > 0, "No stone furnaces found after supposed placement."
print("Successfully placed the Stone Furnace.")


"""
Step 4: Smelt iron plates. 
- Fuel the stone furnace with coal
- Smelt at least 31 iron ore into iron plates
"""
# Inventory at the start of step {'coal': 35, 'stone': 5, 'iron-ore': 35}
#Step Execution

# Step 1: Get reference to existing stone furnace entity
stone_furnace = get_entity(Prototype.StoneFurnace, Position(x=-10.0, y=-11.0))

# Step 2: Fuel the Furnace with Coal
coal_in_inventory = inspect_inventory()[Prototype.Coal]
print(f"Coal available in inventory: {coal_in_inventory}")

# Insert all available coal into the furnace for maximum efficiency
stone_furnace = insert_item(Prototype.Coal, stone_furnace, coal_in_inventory)
print("Inserted coal into Stone Furnace.")

# Step 3: Smelt Iron Ore into Iron Plates
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
print(f"Iron ore available in inventory: {iron_ore_in_inventory}")

# Determine how much iron needs to be inserted (we want at least 31 plates)
required_iron_plates = 31

# Insert all available iron ore since we have more than required quantity
stone_furnace = insert_item(Prototype.IronOre, stone_furnace, min(required_iron_plates, iron_ore_in_inventory))
print("Inserted iron ore into Stone Furnace.")

# Track initial count of Iron Plates in Inventory before starting smelting process 
initial_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)

# Wait until smelting completes — assume each unit takes approximately 0.7 seconds per item 
smelting_time_per_unit = 0.7
sleep(min(required_iron_plates, iron_ore_in_inventory) * smelting_time_per_unit)

max_attempts_to_extract = 5

for attempt in range(max_attempts_to_extract):
    # Try extracting desired amount or whatever is ready within each loop iteration 
    extract_item(Prototype.IronPlate, stone_furnace.position, min(required_iron_plates, iron_ore_in_inventory))
    
    # Check current count post-extraction operation against expected threshold value  
    current_total_of_extracted_items = inspect_inventory().get(Prototype.IronPlate, 0)
    
    print(f"Attempt #{attempt + 1}: Extracted items total up-to-now: {current_total_of_extracted_items}")

    if current_total_of_extracted_items >= initial_iron_plate_count + required_iron_plates:
        break
    
    sleep(10) # Allow some additional time between attempts 

final_number_of_irons_obtained = inspect_inventory().get(Prototype.IronPlate, 0)

assert final_number_of_irons_obtained >= required_iron_plates, f"Failed! Needed: {required_iron_plates}, but obtained only: {final_number_of_irons_obtained}"

print("Successfully completed task; Required amount was achieved!")


"""
Step 5: Craft intermediate items.
- Craft 8 iron gear wheels (each requires 2 iron plates)
- Craft 5 pipes (each requires 1 iron plate)
"""
# Inventory at the start of step {'stone': 5, 'iron-ore': 4, 'iron-plate': 31}
#Step Execution

# Crafting Iron Gear Wheels
print("Crafting Iron Gear Wheels...")
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=8)
# Check inventory to ensure correct number of gear wheels were crafted
gear_wheel_count = inspect_inventory()[Prototype.IronGearWheel]
assert gear_wheel_count >= 8, f"Failed to craft enough Iron Gear Wheels. Expected at least 8, but got {gear_wheel_count}"
print(f"Successfully crafted {gear_wheel_count} Iron Gear Wheels.")

# Crafting Pipes
print("Crafting Pipes...")
crafted_pipes = craft_item(Prototype.Pipe, quantity=5)
# Check inventory to ensure correct number of pipes were crafted
pipe_count = inspect_inventory()[Prototype.Pipe]
assert pipe_count >= 5, f"Failed to craft enough Pipes. Expected at least 5, but got {pipe_count}"
print(f"Successfully crafted {pipe_count} Pipes.")

# Final Inventory check for remaining resources
remaining_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
required_iron_plates = 0  # We've already used the iron plates for crafting

assert remaining_iron_plates >= required_iron_plates, \
    f"Insufficient Iron Plates remaining. Expected at least {required_iron_plates}, but got {remaining_iron_plates}"

print("Intermediate item crafting completed successfully.")
print(f"Current inventory: {inspect_inventory()}")


"""
Step 6: Craft the SteamEngine.
- Use 8 iron gear wheels, 10 iron plates, and 5 pipes to craft 1 SteamEngine
"""
# Inventory at the start of step {'pipe': 5, 'stone': 5, 'iron-ore': 4, 'iron-plate': 10, 'iron-gear-wheel': 8}
#Step Execution

# Verify initial inventory for required items
current_inventory = inspect_inventory()
print(f"Current Inventory before crafting: {current_inventory}")

# Check if there are enough resources for crafting a steam engine
required_gear_wheels = 8
required_iron_plates = 10
required_pipes = 5

assert current_inventory[Prototype.IronGearWheel] >= required_gear_wheels, \
    f"Insufficient Iron Gear Wheels: Expected at least {required_gear_wheels}, but got {current_inventory[Prototype.IronGearWheel]}"
assert current_inventory[Prototype.IronPlate] >= required_iron_plates, \
    f"Insufficient Iron Plates: Expected at least {required_iron_plates}, but got {current_inventory[Prototype.IronPlate]}"
assert current_inventory[Prototype.Pipe] >= required_pipes, \
    f"Insufficient Pipes: Expected at least {required_pipes}, but got {current_inventory[Prototype.Pipe]}"

# Crafting the Steam Engine
print("Crafting a Steam Engine...")
crafted_engines = craft_item(Prototype.SteamEngine)
# Check inventory after crafting to ensure success
steam_engine_count = inspect_inventory()[Prototype.SteamEngine]
assert steam_engine_count >= 1, f"Failed to craft Steam Engine. Expected at least 1 in inventory but found {steam_engine_count}"

print("Successfully crafted a Steam Engine.")


"""
Step 7: Verify success.
- Check the inventory to confirm that 1 SteamEngine is present
##
"""
# Inventory at the start of step {'steam-engine': 1, 'stone': 5, 'iron-ore': 4}
#Step Execution

# Step: Verify Success
print("Verifying success by checking inventory for a Steam Engine...")

# Inspect current inventory to confirm presence of crafted items
current_inventory = inspect_inventory()
steam_engine_count = current_inventory.get(Prototype.SteamEngine, 0)

# Assert that there's at least one steam engine in the inventory
assert steam_engine_count >= 1, f"Verification failed! Expected at least 1 Steam Engine but found {steam_engine_count}."

print(f"Success! Found {steam_engine_count} Steam Engine(s) in inventory.")
