
from instance import *

"""
Step 1: Print recipes. We need to print the recipes for the items we need to craft
"""
# Get the recipe for burner mining drill
burner_mining_drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)

# Get the recipe for transport belt
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)

# Get the recipe for underground belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)

# Get the recipe for stone furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)

# Get the recipe for iron gear wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)

# Print the recipes
print("Burner Mining Drill Recipe:", burner_mining_drill_recipe)
print("Transport Belt Recipe:", transport_belt_recipe)
print("Underground Belt Recipe:", underground_belt_recipe)
print("Stone Furnace Recipe:", stone_furnace_recipe)
print("Iron Gear Wheel Recipe:", iron_gear_wheel_recipe)

print("Recipes printed successfully")

"""
Step 2: Gather resources. We need to mine the following resources:
- 25 iron ore 
- 2 coal 
- 12 stone
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 25),
    (Resource.Coal, 2),
    (Resource.Stone, 12)
]

# Loop through each resource and gather it
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    patch = get_resource_patch(resource_type, nearest(resource_type))
    print(f"Found {resource_type} patch at {patch.bounding_box}")

    # Move to the resource
    move_to(patch.bounding_box.center)
    print(f"Moved to {resource_type} patch")

    # Harvest the resource
    harvested = harvest_resource(patch.bounding_box.center, required_quantity)
    print(f"Harvested {harvested} units of {resource_type}")

    # Verify that we have harvested enough
    inventory = inspect_inventory()
    actual_quantity = inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} units of {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:", final_inventory)

# Assert that we have gathered at least the required amount for each resource
assert final_inventory.get(Resource.IronOre, 0) >= 25, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Not enough Coal"
assert final_inventory.get(Resource.Stone, 0) >= 12, "Not enough Stone"

print("Successfully gathered all required resources")

"""
Step 3: Craft stone furnaces. We need to craft 2 stone furnaces, one for smelting and one for the burner mining drill.
- Craft 2 stone furnaces (each requires 5 stone)
"""
# Craft 2 stone furnaces
furnaces_crafted = craft_item(Prototype.StoneFurnace, quantity=2)
print(f"Crafted {furnaces_crafted} stone furnaces")

# Verify that we have 2 stone furnaces in our inventory
inventory = inspect_inventory()
stone_furnaces_in_inventory = inventory.get(Prototype.StoneFurnace, 0)
assert stone_furnaces_in_inventory >= 2, f"Failed to craft 2 stone furnaces. Actual: {stone_furnaces_in_inventory}"
print(f"Successfully crafted 2 stone furnaces. Current inventory: {inventory}")

"""
Step 4: Set up smelting area. We need to place a stone furnace and smelt iron ore into iron plates.
- Place a stone furnace
- Fuel the furnace with coal
- Smelt 25 iron ore into iron plates
"""
# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed stone furnace at {furnace.position}")

# Insert coal into the furnace as fuel
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
if coal_in_inventory > 0:
    updated_furnace = insert_item(Prototype.Coal, furnace, quantity=1)
    print("Inserted coal into the furnace")
else:
    print("No coal available to fuel the furnace")

# Insert iron ore into the furnace for smelting
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
if iron_ore_in_inventory > 0:
    updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
    print("Inserted iron ore into the furnace")
else:
    print("No iron ore available to smelt")

# Wait for smelting to complete
sleep(10)

# Extract iron plates from the furnace
iron_plates_needed = 25
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_plates_needed)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= iron_plates_needed:
        break
    sleep(5)

print(f"Extracted iron plates; Current inventory count: {current_iron_plate_count}")
assert current_iron_plate_count >= iron_plates_needed, f"Failed to obtain required number of Iron Plates! Expected: {iron_plates_needed}, Found: {current_iron_plate_count}"

print(f"Successfully completed setup of smelting area with {current_iron_plate_count} Iron Plates")

"""
Step 5: Craft iron gear wheels. We need to craft 10 iron gear wheels.
- Craft 10 iron gear wheels (each requires 2 iron plates)
"""
# Craft 10 iron gear wheels
gear_wheels_crafted = craft_item(Prototype.IronGearWheel, quantity=10)
print(f"Crafted {gear_wheels_crafted} iron gear wheels")

# Verify that we have 10 iron gear wheels in our inventory
inventory = inspect_inventory()
iron_gear_wheels_in_inventory = inventory.get(Prototype.IronGearWheel, 0)
assert iron_gear_wheels_in_inventory >= 10, f"Failed to craft 10 iron gear wheels. Actual: {iron_gear_wheels_in_inventory}"
print(f"Successfully crafted 10 iron gear wheels. Current inventory: {inventory}")

"""
Step 6: Craft burner mining drill. We need to craft one burner mining drill.
- Craft 1 burner mining drill (requires 3 iron gear wheels, 1 stone furnace, 3 iron plates)
"""
# Craft 1 burner mining drill
drills_crafted = craft_item(Prototype.BurnerMiningDrill, quantity=1)
print(f"Crafted {drills_crafted} burner mining drill")

# Verify that we have at least 1 burner mining drill in our inventory
inventory = inspect_inventory()
burner_mining_drills_in_inventory = inventory.get(Prototype.BurnerMiningDrill, 0)
assert burner_mining_drills_in_inventory >= 1, f"Failed to craft a burner mining drill. Actual: {burner_mining_drills_in_inventory}"
print(f"Successfully crafted a burner mining drill. Current inventory: {inventory}")

"""
Step 7: Craft transport belts and underground belts. We need to craft 14 transport belts and 4 underground belts.
- Craft 14 transport belts (each requires 1 iron gear wheel and 1 iron plate for 2 belts)
- Craft 4 underground belts (each requires 5 iron gear wheels and 10 iron plates for 2 belts)
"""
# Craft 14 transport belts
transport_belts_crafted = craft_item(Prototype.TransportBelt, quantity=14)
print(f"Crafted {transport_belts_crafted} transport belts")

# Verify that we have at least 14 transport belts in our inventory
inventory = inspect_inventory()
transport_belts_in_inventory = inventory.get(Prototype.TransportBelt, 0)
assert transport_belts_in_inventory >= 14, f"Failed to craft 14 transport belts. Actual: {transport_belts_in_inventory}"
print(f"Successfully crafted 14 transport belts. Current inventory: {inventory}")

# Craft 4 underground belts
underground_belts_crafted = craft_item(Prototype.UndergroundBelt, quantity=4)
print(f"Crafted {underground_belts_crafted} underground belts")

# Verify that we have at least 4 underground belts in our inventory
inventory = inspect_inventory()
underground_belts_in_inventory = inventory.get(Prototype.UndergroundBelt, 0)
assert underground_belts_in_inventory >= 4, f"Failed to craft 4 underground belts. Actual: {underground_belts_in_inventory}"
print(f"Successfully crafted 4 underground belts. Current inventory: {inventory}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:", final_inventory)

print("Successfully completed crafting of transport belts and underground belts")

