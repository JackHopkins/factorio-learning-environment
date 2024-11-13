
from factorio_instance import *

"""
Main objective: Create a fast-transport-belt from scratch

Planning:
We need to create a fast transport belt from scratch. This requires iron gear wheels, which in turn require iron plates.
We need to mine iron ore, smelt it into iron plates, craft iron gear wheels, and then craft the fast transport belt.
We need to create a stone furnace for smelting, a burner mining drill for automated mining, and gather coal for fuel.
"""

"""
Step 1: Print recipes. We need to print the recipes for the items we need to craft, namely stone furnace, burner mining drill, iron gear wheel, and fast transport belt
"""
# Get and print recipes for all required items
recipes_to_print = [Prototype.StoneFurnace, Prototype.BurnerMiningDrill, Prototype.IronGearWheel, Prototype.FastTransportBelt]
for recipe in recipes_to_print:
    recipe_details = get_prototype_recipe(recipe)
    print(f"{recipe}: {recipe_details}")

"""
Step 2: Gather resources
- Mine stone for stone furnace
- Mine iron ore
- Mine coal for fuel
"""
# Define resources to gather
resources_to_gather = [
    (Resource.Stone, 5),  # For stone furnace
    (Resource.IronOre, 20),  # For iron plates and gear wheels
    (Resource.Coal, 10)  # For fueling the furnace and drill
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    print(f"Gathering {required_quantity} of {resource_type}")
    
    # Find nearest patch of the specified resource
    resource_position = nearest(resource_type)
    
    # Move to the location where the resource is available
    move_to(resource_position)
    
    # Harvest the specified amount of this resource
    harvested_amount = harvest_resource(resource_position, required_quantity)
    
    # Verify that we have harvested enough of this resource
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Expected: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} of {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final Inventory: {final_inventory}")

# Ensure all necessary resources are present in sufficient quantities
assert final_inventory.get(Resource.Stone, 0) >= 5, "Insufficient Stone"
assert final_inventory.get(Resource.IronOre, 0) >= 20, "Insufficient Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 10, "Insufficient Coal"

print("Successfully gathered all required resources!")

"""
Step 3: Craft and place stone furnace
- Craft a stone furnace
- Place the stone furnace
"""
# Craft a stone furnace
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
assert crafted_furnaces == 1, "Failed to craft stone furnace"
print("Successfully crafted a stone furnace")

# Place the stone furnace at origin position
origin_position = Position(x=0, y=0)
move_to(origin_position)  # Move to where we want to place it
furnace = place_entity(Prototype.StoneFurnace, position=origin_position)
assert furnace is not None, "Failed to place stone furnace"
print(f"Placed stone furnace at {furnace.position}")

# Check current inventory after placing
current_inventory = inspect_inventory()
remaining_furnaces = current_inventory.get(Prototype.StoneFurnace, 0)
print(f"Remaining Stone Furnaces in Inventory: {remaining_furnaces}")

# Verify successful setup of smelting area
print("Stone Furnace successfully set up")

"""
Step 4: Create smelting setup
- Craft a burner mining drill (requires iron gear wheels and stone furnace)
- Place the burner mining drill on iron ore patch
- Fuel the burner mining drill with coal
"""
# Craft a burner mining drill
# First, we need to craft iron gear wheels for the drill
crafted_gears = craft_item(Prototype.IronGearWheel, quantity=3)
assert crafted_gears == 3, "Failed to craft iron gear wheels"

# Now craft the burner mining drill
crafted_drill = craft_item(Prototype.BurnerMiningDrill, quantity=1)
assert crafted_drill == 1, "Failed to craft burner mining drill"
print("Successfully crafted a burner mining drill")

# Find and move to nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)

# Place the burner mining drill on the iron ore patch
drill = place_entity(Prototype.BurnerMiningDrill, position=iron_ore_position)
assert drill is not None, "Failed to place burner mining drill"
print(f"Placed burner mining drill at {drill.position}")

# Fuel the burner mining drill with coal
coal_in_inventory = inspect_inventory()[Prototype.Coal]
coal_to_insert = min(coal_in_inventory, 5)  # Insert up to 5 pieces of coal

updated_drill = insert_item(Prototype.Coal, drill, quantity=coal_to_insert)
print("Inserted coal into the burner mining drill.")

# Verify that the drill has fuel
assert updated_drill.fuel.get(Prototype.Coal, 0) > 0, "Failed to fuel burner mining drill"

print("Burner Mining Drill successfully set up and fueled")

"""
Step 5: Smelt iron plates
- Fuel the stone furnace with coal
- Smelt iron ore into iron plates
"""
# Insert coal into the stone furnace
coal_in_inventory = inspect_inventory()[Prototype.Coal]
coal_to_insert = min(coal_in_inventory, 5)  # Insert up to 5 pieces of coal

updated_furnace = insert_item(Prototype.Coal, furnace, quantity=coal_to_insert)
print("Inserted coal into the stone furnace.")

# Wait for the burner mining drill to produce some iron ore
sleep(10)

# Extract iron ore from burner mining drill's output position
iron_ore_from_drill = extract_item(Prototype.IronOre, updated_furnace.position, quantity=15)
print(f"Extracted {iron_ore_from_drill} pieces of iron ore from drill")

# Insert extracted iron ore into the stone furnace
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_from_drill)
print(f"Inserted {iron_ore_from_drill} pieces of iron ore into the stone furnace")

# Wait for smelting to complete
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_from_drill)
sleep(total_smelting_time)

# Extract iron plates
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=15)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= 15:
        break
    sleep(10)

print(f"Extracted Iron Plates; Current Inventory Count: {current_iron_plate_count}")

# Verify that we have enough iron plates
assert current_iron_plate_count >= 15, f"Failed to obtain required number of Iron Plates. Expected at least 15, but got {current_iron_plate_count}"

print("Successfully smelted and extracted required number of Iron Plates")

"""
Step 6: Craft iron gear wheels
- Craft iron gear wheels (requires iron plates)
"""
# Craft iron gear wheels
crafted_gears = craft_item(Prototype.IronGearWheel, quantity=4)
assert crafted_gears == 4, "Failed to craft iron gear wheels"
print("Successfully crafted iron gear wheels")

# Check current inventory after crafting
current_inventory = inspect_inventory()
remaining_gears = current_inventory.get(Prototype.IronGearWheel, 0)
print(f"Remaining Iron Gear Wheels in Inventory: {remaining_gears}")

# Verify that we have enough iron gear wheels
assert remaining_gears >= 4, f"Failed to obtain required number of Iron Gear Wheels. Expected at least 4, but got {remaining_gears}"

print("Successfully crafted and verified required number of Iron Gear Wheels")

"""
Step 7: Craft fast transport belt
- Craft fast transport belt (requires iron gear wheel)
"""
# Craft a fast transport belt
crafted_belts = craft_item(Prototype.FastTransportBelt, quantity=1)
assert crafted_belts == 1, "Failed to craft fast transport belt"
print("Successfully crafted a fast transport belt")

# Check current inventory after crafting
current_inventory = inspect_inventory()
remaining_belts = current_inventory.get(Prototype.FastTransportBelt, 0)
print(f"Remaining Fast Transport Belts in Inventory: {remaining_belts}")

# Verify that we have the fast transport belt
assert remaining_belts >= 1, f"Failed to obtain required number of Fast Transport Belts. Expected at least 1, but got {remaining_belts}"

print("Successfully crafted and verified required number of Fast Transport Belts")

print("Objective completed: Created a fast-transport-belt from scratch")

