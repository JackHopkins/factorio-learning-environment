from factorio_instance import *

"""
Main Objective: We require one GunTurret. The final success should be checked by looking if a GunTurret is in inventory
"""



"""
Step 1: Print recipes. We need to craft a GunTurret and Iron Gear Wheels. We must print the recipes for these items.
"""
# Inventory at the start of step {}
#Step Execution

# Get and print the recipe for GunTurret
gun_turret_recipe = get_prototype_recipe(Prototype.GunTurret)
print(f"Gun Turret Recipe: {gun_turret_recipe}")

# Get and print the recipe for Iron Gear Wheels
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(f"Iron Gear Wheel Recipe: {iron_gear_wheel_recipe}")


"""
Step 2: Gather resources. We need to mine the following resources:
- 40 iron ore
- 10 copper ore
- At least 20 coal (for fueling the furnace)
OUTPUT CHECK: Verify that we have at least 40 iron ore, 10 copper ore, and 20 coal in our inventory.
"""
# Inventory at the start of step {}
#Step Execution

# Define required resources with their respective quantities
resources_needed = [
    (Resource.IronOre, 40),
    (Resource.CopperOre, 10),
    (Resource.Coal, 20)
]

# Iterate over each resource type and quantity needed
for resource_type, required_amount in resources_needed:
    # Find nearest position of the current resource
    position = nearest(resource_type)
    
    # Move to the position of the resource
    print(f"Moving to {resource_type} at {position}")
    move_to(position)
    
    # Harvesting more than needed just in case there are inefficiencies or losses
    harvest_amount = int(required_amount * 1.2)  
    harvested_quantity = harvest_resource(position=position, quantity=harvest_amount)
    
    print(f"Harvested {harvested_quantity} units of {resource_type}")

# Verify that we've gathered enough resources by checking our inventory
inventory = inspect_inventory()
iron_ore_count = inventory.get('iron-ore', 0)
copper_ore_count = inventory.get('copper-ore', 0)
coal_count = inventory.get('coal', 0)

print(f"Inventory after gathering: Iron Ore={iron_ore_count}, Copper Ore={copper_ore_count}, Coal={coal_count}")

# Assert checks for ensuring correct amounts are collected
assert iron_ore_count >= 40, f"Failed to gather enough Iron Ore. Expected >=40 but got {iron_ore_count}"
assert copper_ore_count >= 10, f"Failed to gather enough Copper Ore. Expected >=10 but got {copper_ore_count}"
assert coal_count >= 20, f"Failed to gather enough Coal. Expected >=20 but got {coal_count}"

print("Successfully gathered all necessary resources.")


"""
Step 3: Prepare the furnace. We need to fuel the existing stone furnace on the map.
- Move to the furnace at position (-12.0, -12.0)
- Add coal to the furnace
OUTPUT CHECK: Verify that the furnace status is no longer 'NO_FUEL'
"""
# Inventory at the start of step {'coal': 24, 'iron-ore': 48, 'copper-ore': 12}
#Step Execution

# Move to the stone furnace's position
furnace_position = Position(x=-12.0, y=-12.0)
print(f"Moving to stone furnace at {furnace_position}")
move_to(furnace_position)

# Get current inventory and check coal availability
inventory = inspect_inventory()
coal_in_inventory = inventory.get('coal', 0)
print(f"Coal available in inventory: {coal_in_inventory}")

# Insert all available coal into the stone furnace
stone_furnace = get_entity(Prototype.StoneFurnace, furnace_position)
stone_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=coal_in_inventory)
print(f"Inserted {coal_in_inventory} units of coal into the stone furnace")

# Inspecting entities around us again after insertion to verify status change
inspection_results = inspect_entities(position=furnace_position)
updated_stone_furnace_info = inspection_results.get_entity(Prototype.StoneFurnace)

# Verify that the status of the stone furnace is no longer 'NO_FUEL'
assert updated_stone_furnace_info.status != EntityStatus.NO_FUEL, "Failed to fuel the stone furnace."
print("Successfully fueled the stone furnace.")


"""
Step 4: Smelt iron plates. We need to smelt 40 iron ore into iron plates.
- Insert iron ore into the furnace
- Wait for the smelting process to complete
OUTPUT CHECK: Verify that we have 40 iron plates in our inventory
"""
# Inventory at the start of step {'iron-ore': 48, 'copper-ore': 12}
#Step Execution

# Get reference to existing stone furnace entity
stone_furnace = get_entity(Prototype.StoneFurnace, Position(x=-12.0, y=-12.0))

# Check how much iron ore is available in inventory
inventory = inspect_inventory()
iron_ore_in_inventory = inventory.get(Prototype.IronOre, 0)
print(f"Iron Ore available in inventory: {iron_ore_in_inventory}")

# Insert all available Iron Ore into Stone Furnace
stone_furnace = insert_item(Prototype.IronOre, stone_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} units of Iron Ore into Stone Furnace")

# Calculate expected number of Iron Plates after smelting
initial_iron_plate_count = inventory.get(Prototype.IronPlate, 0)
expected_iron_plate_count = initial_iron_plate_count + iron_ore_in_inventory
print(f"Expected Iron Plate count after smelting: {expected_iron_plate_count}")

# Wait for smelting process (approximately 3.2 seconds per iron plate)
smelting_time = iron_ore_in_inventory * 3.2
print(f"Waiting {smelting_time} seconds for smelting")
sleep(smelting_time)

# Attempt extraction multiple times if needed due to processing delays or inefficiencies
max_attempts_for_extraction = 5

for attempt in range(max_attempts_for_extraction):
    # Extract Iron Plates from Stone Furnace
    extract_item(Prototype.IronPlate, stone_furnace.position, iron_ore_in_inventory)
    
    # Check current count of Iron Plates in Inventory after extraction attempt
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    
    print(f"Attempt {attempt+1}: Current Iron Plate Count: {current_iron_plate_count}")
    
    # If we've reached or exceeded expected count of Iron Plates - break out early!
    if current_iron_plate_count >= expected_iron_plate_count:
        break
    
    sleep(10) # Additional wait before next extraction attempt

# Final verification - ensure we have at least required number of Iron Plates post-extraction 
final_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
assert final_iron_plate_count >= expected_iron_plate_count, f"Failed to smelt enough Iron Plates. Expected: {expected_iron_plate_count}, but got: {final_iron_plate_count}"
print(f"Successfully smelted {final_iron_plate_count} Iron Plates.")

# Check if we have at least 40 iron plates
assert final_iron_plate_count >= 40, f"Failed to smelt at least 40 Iron Plates. Current count: {final_iron_plate_count}"
print("Successfully smelted at least 40 Iron Plates.")


"""
Step 5: Smelt copper plates. We need to smelt 10 copper ore into copper plates.
- Insert copper ore into the furnace
- Wait for the smelting process to complete
OUTPUT CHECK: Verify that we have 10 copper plates in our inventory
"""
# Inventory at the start of step {'copper-ore': 12, 'iron-plate': 48}
#Step Execution

# Get reference to existing stone furnace entity
stone_furnace = get_entity(Prototype.StoneFurnace, Position(x=-12.0, y=-12.0))

# Check how much copper ore is available in inventory
inventory = inspect_inventory()
copper_ore_in_inventory = min(inventory.get(Prototype.CopperOre, 0), 10)
print(f"Copper Ore available in inventory: {copper_ore_in_inventory}")

# Insert available Copper Ore into Stone Furnace
stone_furnace = insert_item(Prototype.CopperOre, stone_furnace, quantity=copper_ore_in_inventory)
print(f"Inserted {copper_ore_in_inventory} units of Copper Ore into Stone Furnace")

# Calculate expected number of Copper Plates after smelting
initial_copper_plate_count = inventory.get(Prototype.CopperPlate, 0)
expected_copper_plate_count = initial_copper_plate_count + copper_ore_in_inventory
print(f"Expected Copper Plate count after smelting: {expected_copper_plate_count}")

# Wait for smelting process (approximately 3.2 seconds per copper plate)
smelting_time = copper_ore_in_inventory * 3.2
print(f"Waiting {smelting_time} seconds for smelting")
sleep(smelting_time)

# Attempt extraction multiple times if needed due to processing delays or inefficiencies
max_attempts_for_extraction = 5

for attempt in range(max_attempts_for_extraction):
    # Extract Copper Plates from Stone Furnace
    extract_item(Prototype.CopperPlate, stone_furnace.position, quantity=copper_ore_in_inventory)
    
    # Check current count of Copper Plates in Inventory after extraction attempt
    current_copper_plate_count = inspect_inventory().get(Prototype.CopperPlate, 0)
    
    print(f"Attempt {attempt+1}: Current Copper Plate Count: {current_copper_plate_count}")
    
    # If we've reached or exceeded expected count of Copper Plates - break out early!
    if current_copper_plate_count >= expected_copper_plate_count:
        break
    
    sleep(10) # Additional wait before next extraction attempt

# Final verification - ensure we have at least required number of Copper Plates post-extraction 
final_copper_plate_count = inspect_inventory().get(Prototype.CopperPlate, 0)
assert final_copper_plate_count >= expected_copper_plate_count, f"Failed to smelt enough Copper Plates. Expected: {expected_copper_plate_count}, but got: {final_copper_plate_count}"
print(f"Successfully smelted {final_copper_plate_count} Copper Plates.")

# Check if we have at least 10 copper plates or all available copper ore has been smelted
assert final_copper_plate_count >= min(10, copper_ore_in_inventory), f"Failed to smelt the required number of Copper Plates. Current count: {final_copper_plate_count}"
print(f"Successfully smelted {final_copper_plate_count} Copper Plates.")


"""
Step 6: Craft iron gear wheels. We need to craft 10 iron gear wheels.
- Use the crafting menu to create 10 iron gear wheels using 20 iron plates
OUTPUT CHECK: Verify that we have 10 iron gear wheels in our inventory
"""
# Inventory at the start of step {'copper-ore': 2, 'iron-plate': 48, 'copper-plate': 10}
#Step Execution

# Step: Craft Iron Gear Wheels

# Inspect current inventory
inventory = inspect_inventory()
iron_plates_in_inventory = inventory.get(Prototype.IronPlate, 0)
print(f"Iron Plates available in inventory: {iron_plates_in_inventory}")

# Check if we have enough Iron Plates (at least 20) to craft Iron Gear Wheels
assert iron_plates_in_inventory >= 20, f"Not enough Iron Plates to craft Iron Gear Wheels. Required: 20, Available: {iron_plates_in_inventory}"

# Crafting process - Crafting 10 Iron Gear Wheels using available resources
craft_item(Prototype.IronGearWheel, quantity=10)
print("Crafted 10 Iron Gear Wheels.")

# Verify that we have crafted at least 10 Iron Gear Wheels by checking our updated inventory
updated_inventory = inspect_inventory()
iron_gear_wheels_count = updated_inventory.get(Prototype.IronGearWheel, 0)

print(f"Inventory after crafting: {updated_inventory}")
assert iron_gear_wheels_count >= 10, f"Failed to craft enough Iron Gear Wheels. Expected: >=10 but got {iron_gear_wheels_count}"
print("Successfully crafted at least 10 Iron Gear Wheels.")


"""
Step 7: Craft the GunTurret. We now have all the materials to craft the GunTurret.
- Use the crafting menu to create 1 GunTurret using 10 copper plates, 10 iron gear wheels, and 20 iron plates
OUTPUT CHECK: Verify that we have 1 GunTurret in our inventory

##
"""
# Inventory at the start of step {'copper-ore': 2, 'iron-plate': 28, 'copper-plate': 10, 'iron-gear-wheel': 10}
#Step Execution

# Step: Craft the GunTurret

# Inspect current inventory
inventory = inspect_inventory()
iron_plates_in_inventory = inventory.get(Prototype.IronPlate, 0)
copper_plates_in_inventory = inventory.get(Prototype.CopperPlate, 0)
iron_gear_wheels_in_inventory = inventory.get(Prototype.IronGearWheel, 0)

print(f"Iron Plates available: {iron_plates_in_inventory}")
print(f"Copper Plates available: {copper_plates_in_inventory}")
print(f"Iron Gear Wheels available: {iron_gear_wheels_in_inventory}")

# Assert checks for ensuring enough materials are present before crafting
assert iron_plates_in_inventory >= 20, f"Not enough Iron Plates to craft a Gun Turret. Required: 20, Available: {iron_plates_in_inventory}"
assert copper_plates_in_inventory >= 10, f"Not enough Copper Plates to craft a Gun Turret. Required: 10, Available: {copper_plates_in_inventory}"
assert iron_gear_wheels_in_inventory >= 10, f"Not enough Iron Gear Wheels to craft a Gun Turret. Required: 10, Available: {iron_gear_wheels_in_inventory}"

# Crafting process - Crafting one Gun Turret using available resources
craft_item(Prototype.GunTurret)
print("Crafted a Gun Turret.")

# Verify that we have crafted at least one Gun Turret by checking our updated inventory
updated_inventory = inspect_inventory()
gun_turrets_count = updated_inventory.get(Prototype.GunTurret, 0)

print(f"Inventory after crafting: {updated_inventory}")
assert gun_turrets_count >= 1, f"Failed to craft a Gun Turret. Expected at least one but got {gun_turrets_count}"
print("Successfully crafted at least one Gun Turret.")
