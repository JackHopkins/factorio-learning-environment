from factorio_instance import *

"""
Main Objective: We require one SteamEngine. The final success should be checked by looking if a SteamEngine is in inventory
"""



"""
Step 1: Gather resources
- Mine at least 31 iron ore
- Mine at least 10 coal (for fueling the furnace)
OUTPUT CHECK: Verify that we have at least 31 iron ore and 10 coal in our inventory
"""
# Inventory at the start of step {}
#Step Execution

# Define the resources needed
resources_needed = [(Resource.IronOre, 31), (Resource.Coal, 10)]

# Loop through each resource type we need to gather
for resource_type, quantity_required in resources_needed:
    # Find the nearest location for this resource
    resource_location = nearest(resource_type)
    
    # Move to that location to start mining
    move_to(resource_location)
    
    # Harvest the specified amount of this resource
    harvested_quantity = harvest_resource(resource_location, quantity_required)
    
    # Log how much was harvested for verification purposes
    print(f"Harvested {harvested_quantity} of {resource_type[0]}.")
    
    # Verify if enough has been mined by checking current inventory state
    current_inventory = inspect_inventory()
    actual_quantity_in_inventory = current_inventory[resource_type]
   
    assert actual_quantity_in_inventory >= quantity_required,\
        f"Failed to gather enough {resource_type[0]}. Expected at least {quantity_required}, but got {actual_quantity_in_inventory}"
        
print("Successfully gathered all necessary resources.")
final_inventory_state = inspect_inventory()
print(f"Final Inventory State: {final_inventory_state}")

# Final assertion to ensure we have the required resources
assert final_inventory_state[Resource.IronOre] >= 31, f"Not enough iron ore. Expected at least 31, but got {final_inventory_state[Resource.IronOre]}"
assert final_inventory_state[Resource.Coal] >= 10, f"Not enough coal. Expected at least 10, but got {final_inventory_state[Resource.Coal]}"


"""
Step 2: Prepare the furnace
- Move to the existing stone furnace at position (-12.0, -12.0)
- Add coal to the furnace as fuel
OUTPUT CHECK: Verify that the furnace status changes from NO_FUEL to IDLE
"""
# Inventory at the start of step {'coal': 10, 'iron-ore': 31}
#Step Execution

# Step 2: Prepare the Furnace

# Identify and move to the stone furnace position
furnace_position = Position(x=-12.0, y=-12.0)
move_to(furnace_position)
print(f"Moved to stone furnace at {furnace_position}")

# Inspect inventory for available coal
coal_in_inventory = inspect_inventory()[Prototype.Coal]
print(f"Coal in inventory before fueling: {coal_in_inventory}")

# Retrieve stone furnace entity from map entities
stone_furnaces = get_entities({Prototype.StoneFurnace})
stone_furnace = next((furnace for furnace in stone_furnaces if furnace.position.is_close(furnace_position)), None)

if not stone_furnace:
    raise Exception("Stone Furnace not found at expected position.")

# Add coal to the stone furnace as fuel
stone_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=coal_in_inventory)
print(f"Inserted {coal_in_inventory} units of coal into the stone-furnace")

# Sleep briefly to allow game state update (if necessary)
sleep(1)

# Re-inspect entities around us including our target - Stone Furnace
inspection_results = inspect_entities(radius=10)
updated_stone_furnace_status = next(
    (entity.status for entity in inspection_results.entities if entity.name == 'stone-furnace' and entity.position.is_close(furnace_position)),
    None
)

assert updated_stone_furnace_status != EntityStatus.NO_FUEL, "Failed: Furnace is still out of fuel."
print("Successfully fueled the Stone Furnace; it is no longer out of fuel.")


"""
Step 3: Smelt iron plates
- Add iron ore to the furnace
- Wait for the smelting process to complete (31 cycles)
OUTPUT CHECK: Verify that we have at least 31 iron plates in our inventory
"""
# Inventory at the start of step {'iron-ore': 31}
#Step Execution

# Get the stone furnace entity again (in case it has changed)
stone_furnaces = get_entities({Prototype.StoneFurnace})
stone_furnace = next((furnace for furnace in stone_furnaces if furnace.position.is_close(Position(x=-12.0, y=-12.0))), None)

if not stone_furnace:
    raise Exception("Stone Furnace not found at expected position.")

# Check how much iron ore we have in inventory
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
print(f"Iron ore available: {iron_ore_in_inventory}")

# Insert all available iron ore into the stone furnace
stone_furnace = insert_item(Prototype.IronOre, stone_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} units of iron ore into the stone-furnace")

# Wait for smelting process to complete; each cycle takes about 0.7 seconds per unit
sleep(iron_ore_in_inventory * 0.7)

# Attempt to extract all possible resulting iron plates from the furnace
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, stone_furnace.position, quantity=iron_ore_in_inventory)
    
    # Check number of extracted items by inspecting current inventory state
    current_iron_plate_count = inspect_inventory()[Prototype.IronPlate]
    
    # If enough plates are present, break out of loop early
    if current_iron_plate_count >= 31:
        break
    
    sleep(10)  # Allow more time if needed

print(f"Extracted {current_iron_plate_count} units of Iron Plates")
final_inventory_state_after_smelting = inspect_inventory()
print(f"Final Inventory State after Smelting: {final_inventory_state_after_smelting}")

# Assert final condition - ensure there are at least 31 Iron Plates now available post-smelting 
assert final_inventory_state_after_smelting[Prototype.IronPlate] >= 31,\
       f"Failed to produce enough Iron Plates! Expected at least 31 but got {final_inventory_state_after_smelting[Prototype.IronPlate]}"

print("Successfully completed smelting and verified required amount of Iron Plates.")


"""
Step 4: Craft iron gear wheels
- Craft 8 iron gear wheels (each requires 2 iron plates)
OUTPUT CHECK: Verify that we have 8 iron gear wheels in our inventory
"""
# Inventory at the start of step {'iron-plate': 31}
#Step Execution

# Step: Craft Iron Gear Wheels

# Check how many iron plates are available before crafting
iron_plates_before_crafting = inspect_inventory()[Prototype.IronPlate]
print(f"Iron Plates available before crafting: {iron_plates_before_crafting}")

# Calculate how many Iron Gear Wheels can be crafted (each needs 2 Iron Plates)
gear_wheels_needed = 8
required_plates_for_gears = gear_wheels_needed * 2

assert iron_plates_before_crafting >= required_plates_for_gears,\
    f"Not enough Iron Plates to craft {gear_wheels_needed} Iron Gear Wheels! Needed {required_plates_for_gears}, but only have {iron_plates_before_crafting}"

# Crafting the Iron Gear Wheels
crafted_count = craft_item(Prototype.IronGearWheel, quantity=gear_wheels_needed)
print(f"Crafted {crafted_count} Iron Gear Wheels.")

# Inspect Inventory again to verify successful crafting
inventory_after_crafting = inspect_inventory()
iron_gear_wheels_in_inventory = inventory_after_crafting[Prototype.IronGearWheel]

print(f"Iron Gear Wheels in Inventory after crafting: {iron_gear_wheels_in_inventory}")

# Assert that we now have at least as many Iron Gear Wheels as needed
assert iron_gear_wheels_in_inventory >= gear_wheels_needed,\
    f"Failed to craft enough Iron Gear Wheels! Expected at least {gear_wheels_needed}, but got {iron_gear_wheels_in_inventory}"

print("Successfully crafted and verified required amount of Iron Gear Wheels.")


"""
Step 5: Craft pipes
- Craft 5 pipes (each requires 1 iron plate)
OUTPUT CHECK: Verify that we have 5 pipes in our inventory
"""
# Inventory at the start of step {'iron-plate': 15, 'iron-gear-wheel': 8}
#Step Execution

# Step: Craft Pipes

# Check how many iron plates are available before crafting
iron_plates_before_crafting = inspect_inventory()[Prototype.IronPlate]
print(f"Iron Plates available before crafting: {iron_plates_before_crafting}")

# Calculate how many Pipes can be crafted (each needs 1 Iron Plate)
pipes_needed = 5

assert iron_plates_before_crafting >= pipes_needed,\
    f"Not enough Iron Plates to craft {pipes_needed} Pipes! Needed {pipes_needed}, but only have {iron_plates_before_crafting}"

# Crafting the Pipes
crafted_pipes_count = craft_item(Prototype.Pipe, quantity=pipes_needed)
print(f"Crafted {crafted_pipes_count} Pipes.")

# Inspect Inventory again to verify successful crafting
inventory_after_crafting = inspect_inventory()
pipes_in_inventory = inventory_after_crafting[Prototype.Pipe]

print(f"Pipes in Inventory after crafting: {pipes_in_inventory}")

# Assert that we now have at least as many Pipes as needed
assert pipes_in_inventory >= pipes_needed,\
    f"Failed to craft enough Pipes! Expected at least {pipes_needed}, but got {pipes_in_inventory}"

print("Successfully crafted and verified required amount of Pipes.")


"""
Step 6: Craft the SteamEngine
- Use 8 iron gear wheels, 10 iron plates, and 5 pipes to craft 1 SteamEngine
OUTPUT CHECK: Verify that we have 1 SteamEngine in our inventory

##
"""
# Inventory at the start of step {'pipe': 5, 'iron-plate': 10, 'iron-gear-wheel': 8}
#Step Execution

# Step: Craft the Steam Engine

# Check how many iron gear wheels, iron plates, and pipes are available before crafting
inventory_before_crafting = inspect_inventory()
iron_gear_wheels_available = inventory_before_crafting[Prototype.IronGearWheel]
iron_plates_available = inventory_before_crafting[Prototype.IronPlate]
pipes_available = inventory_before_crafting[Prototype.Pipe]

print(f"Iron Gear Wheels available before crafting: {iron_gear_wheels_available}")
print(f"Iron Plates available before crafting: {iron_plates_available}")
print(f"Pipes available before crafting: {pipes_available}")

# Ensure there are enough resources to craft a steam engine
assert iron_gear_wheels_available >= 8,\
    f"Not enough Iron Gear Wheels to craft a Steam Engine! Needed 8, but only have {iron_gear_wheels_available}"
assert iron_plates_available >= 10,\
    f"Not enough Iron Plates to craft a Steam Engine! Needed 10, but only have {iron_plates_available}"
assert pipes_available >= 5,\
    f"Not enough Pipes to craft a Steam Engine! Needed 5, but only have {pipes_available}"

# Crafting the Steam Engine
crafted_count = craft_item(Prototype.SteamEngine, quantity=1)
print(f"Crafted {crafted_count} Steam Engine.")

# Inspect Inventory again to verify successful crafting
inventory_after_crafting = inspect_inventory()
steam_engines_in_inventory = inventory_after_crafting[Prototype.SteamEngine]

print(f"Steam Engines in Inventory after crafting: {steam_engines_in_inventory}")

# Assert that we now have at least one Steam Engine as needed
assert steam_engines_in_inventory >= 1,\
    f"Failed to craft a Steam Engine! Expected at least 1, but got {steam_engines_in_inventory}"

print("Successfully crafted and verified required amount of Steam Engines.")
