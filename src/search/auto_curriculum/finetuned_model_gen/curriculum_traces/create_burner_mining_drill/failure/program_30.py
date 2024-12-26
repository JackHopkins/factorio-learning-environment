
from factorio_instance import *

"""
Step 1: Print recipes. We need to craft a burner mining drill from scratch.
We need to print the recipes for the following items:
- burner mining drill
"""
# Get and print recipes for the required items
recipes_to_print = [Prototype.BurnerMiningDrill, Prototype.StoneFurnace, Prototype.IronGearWheel, Prototype.TransportBelt]
for recipe in recipes_to_print:
    print(f"Recipe for {recipe}: {get_prototype_recipe(recipe)}")
    
"""
Step 2: Gather resources. We need to gather the following resources:
- 10 stone (5 for the stone furnace, 5 for the burner mining drill)
- 16 iron ore (9 for the burner mining drill, 1 for the stone furnace, 4 for the transport belt)
- 2 coal (1 for the stone furnace, 1 for the burner mining drill)
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 10),
    (Resource.IronOre, 16),
    (Resource.Coal, 2)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    print(f"Nearest {resource_type} found at position: {resource_position}")

    # Move to the resource position
    move_to(resource_position)
    print(f"Moved to {resource_type} at position: {resource_position}")

    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    print(f"Harvested {harvested} units of {resource_type}")

    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} units of {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory after gathering resources: {final_inventory}")

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.Stone, 0) >= 10, "Not enough Stone in final inventory"
assert final_inventory.get(Resource.IronOre, 0) >= 16, "Not enough Iron Ore in final inventory"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Not enough Coal in final inventory"

print("Successfully gathered all necessary resources!")

"""
Step 3: Craft stone furnace. We need to craft a stone furnace using 5 stone.
"""
# Craft a stone furnace
crafted_stone_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted {crafted_stone_furnaces} Stone Furnace(s)")

# Check if the stone furnace was crafted successfully
stone_furnaces_in_inventory = inspect_inventory().get(Prototype.StoneFurnace, 0)
assert stone_furnaces_in_inventory >= 1, f"Failed to craft Stone Furnace. Expected at least 1, but found {stone_furnaces_in_inventory}"

"""
Step 4: Smelt iron plates. We need to smelt 16 iron ore into 16 iron plates.
- Place the stone furnace
- Fuel the stone furnace with 1 coal
- Smelt the iron ore into iron plates
"""
# Get the current position of the player
current_position = inspect_entities().player_position

# Place the stone furnace at the current position
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=current_position[0], y=current_position[1]+2))
print(f"Placed Stone Furnace at position: {furnace.position}")

# Insert coal into the stone furnace as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=1)
print("Inserted 1 unit of coal into the Stone Furnace")

# Insert iron ore into the stone furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} units of Iron Ore into the Stone Furnace")

# Calculate expected number of iron plates
initial_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
expected_iron_plates = initial_iron_plates + iron_ore_in_inventory

# Wait for smelting to complete (assuming 0.7 seconds per unit)
smelting_time_per_unit = 0.7
total_smelting_time = smelting_time_per_unit * iron_ore_in_inventory
sleep(total_smelting_time)

# Extract iron plates from the stone furnace
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    current_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plates >= expected_iron_plates:
        break
    sleep(10)  # Allow additional time if needed

print(f"Extracted Iron Plates; Current Inventory Count: {current_iron_plates}")
print(f"Inventory after extracting Iron Plates: {inspect_inventory()}")

# Verify that we have the expected number of iron plates
assert current_iron_plates >= expected_iron_plates, f"Failed to obtain required number of Iron Plates. Expected: {expected_iron_plates}, Actual: {current_iron_plates}"

print("Successfully obtained required number of Iron Plates!")

"""
Step 5: Craft iron gear wheels. We need to craft 3 iron gear wheels using 6 iron plates.
"""
# Craft iron gear wheels
crafted_iron_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=3)
print(f"Crafted {crafted_iron_gear_wheels} Iron Gear Wheel(s)")

# Check if the iron gear wheels were crafted successfully
iron_gear_wheels_in_inventory = inspect_inventory().get(Prototype.IronGearWheel, 0)
assert iron_gear_wheels_in_inventory >= 3, f"Failed to craft Iron Gear Wheels. Expected at least 3, but found {iron_gear_wheels_in_inventory}"

"""
Step 6: Craft burner mining drill. We need to craft the burner mining drill using:
- 3 iron gear wheels
- 1 stone furnace
- 3 iron plates
"""
# Craft burner mining drill
crafted_burner_mining_drills = craft_item(Prototype.BurnerMiningDrill, quantity=1)
print(f"Crafted {crafted_burner_mining_drills} Burner Mining Drill(s)")

# Check if the burner mining drill was crafted successfully
burner_mining_drills_in_inventory = inspect_inventory().get(Prototype.BurnerMiningDrill, 0)
assert burner_mining_drills_in_inventory >= 1, f"Failed to craft Burner Mining Drill. Expected at least 1, but found {burner_mining_drills_in_inventory}"

"""
Step 7: Craft transport belt. We need to craft 4 transport belts using 4 iron plates.
"""
# Craft transport belts
crafted_transport_belts = craft_item(Prototype.TransportBelt, quantity=4)
print(f"Crafted {crafted_transport_belts} Transport Belt(s)")

# Check if the transport belts were crafted successfully
transport_belts_in_inventory = inspect_inventory().get(Prototype.TransportBelt, 0)
assert transport_belts_in_inventory >= 4, f"Failed to craft Transport Belts. Expected at least 4, but found {transport_belts_in_inventory}"

"""
Step 8: Verify the crafted items. We need to check if we have crafted all the required items:
- 1 burner mining drill
- 4 transport belts
"""
# Verify final inventory
final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

# Assert that we have at least the required quantities
assert final_inventory.get(Prototype.BurnerMiningDrill, 0) >= 1, "Not enough Burner Mining Drills in final inventory"
assert final_inventory.get(Prototype.TransportBelt, 0) >= 4, "Not enough Transport Belts in final inventory"

print("Successfully crafted all required items!")

