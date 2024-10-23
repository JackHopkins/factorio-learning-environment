from factorio_instance import *

"""
Main Objective: We require one Radar. The final success should be checked by looking if a Radar is in inventory
"""



"""
Step 1: Print recipes. We need to craft a Radar, which requires intermediate components. Print out the recipes for:
- Radar
- Electronic Circuit
- Iron Gear Wheel
"""
# Inventory at the start of step {}
#Step Execution

# Get and print the recipe for Radar
radar_recipe = get_prototype_recipe(Prototype.Radar)
print(f"Radar Recipe: {radar_recipe}")

# Get and print the recipe for Electronic Circuit
electronic_circuit_recipe = get_prototype_recipe(Prototype.ElectronicCircuit)
print(f"Electronic Circuit Recipe: {electronic_circuit_recipe}")

# Get and print the recipe for Iron Gear Wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(f"Iron Gear Wheel Recipe: {iron_gear_wheel_recipe}")


"""
Step 2: Gather resources. We need to mine the following resources:
- Iron Ore (at least 50)
- Copper Ore (at least 20)
- Coal (at least 20)
- Stone (at least 5, in case we need another furnace)
OUTPUT CHECK: Verify that we have the required amounts of each resource in our inventory.
"""
# Inventory at the start of step {}
#Step Execution

# Define the resources needed with their minimum required quantities
resources_needed = {
    Resource.IronOre: 50,
    Resource.CopperOre: 20,
    Resource.Coal: 20,
    Resource.Stone: 5
}

# Iterate over each resource type and collect them
for resource_type, required_amount in resources_needed.items():
    print(f"Starting to gather {resource_type}...")
    
    # Find nearest position of current resource type
    nearest_resource_position = nearest(resource_type)
    
    # Move to that position
    move_to(nearest_resource_position)
    
    # Harvest enough quantity of that resource
    harvest_resource(nearest_resource_position, required_amount + 10) # Adding buffer
    
    # Check if we have gathered enough by inspecting inventory
    current_inventory_count = inspect_inventory().get(resource_type, 0)
    
    assert current_inventory_count >= required_amount, f"Failed to gather enough {resource_type}. Expected at least {required_amount}, but got {current_inventory_count}"
    
    print(f"Successfully gathered {current_inventory_count} units of {resource_type}")

# Final output check for all resources after gathering process is complete
final_inventory = inspect_inventory()
print(f"Final Inventory after gathering: {final_inventory}")

assert final_inventory.get(Resource.IronOre, 0) >= resources_needed[Resource.IronOre], "Not enough Iron Ore!"
assert final_inventory.get(Resource.CopperOre, 0) >= resources_needed[Resource.CopperOre], "Not enough Copper Ore!"
assert final_inventory.get(Resource.Coal, 0) >= resources_needed[Resource.Coal], "Not enough Coal!"
assert final_inventory.get(Resource.Stone, 0) >= resources_needed[Resource.Stone], "Not enough Stone!"

print("Successfully completed gathering all necessary resources.")


"""
Step 3: Fuel and prepare the furnace. We need to:
- Move to the existing stone furnace at position (-12.0, -12.0)
- Add coal to the furnace as fuel
OUTPUT CHECK: Verify that the furnace status changes from NO_FUEL to IDLE.
"""
# Inventory at the start of step {'coal': 30, 'stone': 15, 'iron-ore': 60, 'copper-ore': 30}
#Step Execution

# Identify and move to the existing stone furnace
furnace_position = Position(x=-12.0, y=-12.0)
print(f"Moving to the stone furnace at {furnace_position}")
move_to(furnace_position)

# Get reference to the stone furnace entity
stone_furnaces = get_entities({Prototype.StoneFurnace})
stone_furnace = next((f for f in stone_furnaces if f.position.is_close(furnace_position)), None)

assert stone_furnace is not None, "Failed to find the stone furnace at expected position."

# Add coal as fuel into the furnace
coal_in_inventory = inspect_inventory()[Prototype.Coal]
print(f"Inserting {coal_in_inventory} units of coal into the furnace.")
insert_item(Prototype.Coal, stone_furnace, quantity=coal_in_inventory)

# Verify that the status of the furnace changes from NO_FUEL to IDLE (or WORKING)
updated_stone_furnace = get_entity(Prototype.StoneFurnace, position=furnace_position)
assert updated_stone_furnace.status != EntityStatus.NO_FUEL, "Furnace still has no fuel!"
print("Successfully fueled the stove! Furnace status is now:", updated_stone_furnace.status.name)


"""
Step 4: Smelt iron plates. We need to:
- Add iron ore to the furnace
- Wait for the smelting process to complete
- Collect the iron plates
OUTPUT CHECK: Verify that we have at least 30 iron plates in our inventory.
"""
# Inventory at the start of step {'stone': 15, 'iron-ore': 60, 'copper-ore': 30}
#Step Execution

# Get reference to the stone furnace entity
stone_furnaces = get_entities({Prototype.StoneFurnace})
stone_furnace = next((f for f in stone_furnaces if f.position.is_close(Position(x=-12.0, y=-12.0))), None)

assert stone_furnace is not None, "Failed to find an active stone furnace."

# Check how much Iron Ore we have in inventory
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
print(f"Iron Ore available: {iron_ore_in_inventory}")

# Insert Iron Ore into Stone Furnace in batches of 30 (typical furnace capacity)
batch_size = 30
remaining_ore = iron_ore_in_inventory

while remaining_ore > 0:
    insert_amount = min(batch_size, remaining_ore)
    stone_furnace = insert_item(Prototype.IronOre, stone_furnace, quantity=insert_amount)
    print(f"Inserted {insert_amount} units of Iron Ore into Stone Furnace.")
    remaining_ore -= insert_amount

    # Calculate expected number of Iron Plates after smelting this batch
    expected_iron_plates = insert_amount

    # Wait for smelting process; assume each unit takes 3.2 seconds
    smelting_time_per_unit = 3.2
    total_smelting_time = int(smelting_time_per_unit * insert_amount)
    sleep(total_smelting_time)

    # Extract Iron Plates from Furnace
    max_attempts = 5
    for attempt in range(max_attempts):
        extract_item(Prototype.IronPlate, position=stone_furnace.position, quantity=expected_iron_plates)
        current_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
        print(f"Attempt {attempt + 1}: Extracted Iron Plates. Current count: {current_iron_plates}")
        
        if current_iron_plates >= expected_iron_plates:
            break
        sleep(5)  # Wait a bit more if not all plates are ready

# Check final count of Iron Plates in Inventory
final_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
print(f"Final count of Iron Plates: {final_iron_plates}")

# Assert that we have at least 30 iron plates
assert final_iron_plates >= 30, f"Failed to smelt enough iron plates. Expected at least 30, but got {final_iron_plates}"

print("Successfully smelted iron plates.")


"""
Step 5: Smelt copper plates. We need to:
- Add copper ore to the furnace
- Wait for the smelting process to complete
- Collect the copper plates
OUTPUT CHECK: Verify that we have at least 10 copper plates in our inventory.
"""
# Placeholder 5

"""
Step 6: Craft iron gear wheels. We need to:
- Craft 5 iron gear wheels (each requires 2 iron plates)
OUTPUT CHECK: Verify that we have 5 iron gear wheels in our inventory.
"""
# Placeholder 6

"""
Step 7: Craft electronic circuits. We need to:
- Craft 10 copper cables (each copper plate produces 2 copper cables)
- Craft 5 electronic circuits (each requires 3 copper cables and 1 iron plate)
OUTPUT CHECK: Verify that we have 5 electronic circuits in our inventory.
"""
# Placeholder 7

"""
Step 8: Craft the Radar. We need to:
- Use 5 electronic circuits, 5 iron gear wheels, and 10 iron plates to craft 1 Radar
OUTPUT CHECK: Verify that we have 1 Radar in our inventory.

##
"""
# Placeholder 8