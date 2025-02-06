
from instance import *


"""
Step 1: Print recipes. We need to craft a burner mining drill. We need to print the recipe for:
- burner mining drill
- stone furnace
- iron gear wheel
- firearm magazine
"""
# Get and print recipe for burner mining drill
drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
print(f"burner-mining-drill recipe: {drill_recipe}")

# Get and print recipe for stone furnace
furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"stone-furnace recipe: {furnace_recipe}")

# Get and print recipe for iron gear wheel
gear_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print(f"iron-gear-wheel recipe: {gear_recipe}")

# Get and print recipe for firearm magazine
magazine_recipe = get_prototype_recipe(Prototype.FirearmMagazine)
print(f"firearm-magazine recipe: {magazine_recipe}")

"""
Step 2: Gather resources. We need to gather the following resources:
- 9 iron plates (for burner mining drill)
- 5 stone (for stone furnace)
- 2 coal (for fuel)
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 18),  # We need to gather iron ore to smelt into iron plates
    (Resource.Stone, 6),     # We need stone to craft the stone furnace
    (Resource.Coal, 2)       # We need coal for fuel
]

# Loop through each resource type and quantity
for resource_type, quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    print(f"Nearest {resource_type} found at {resource_position}")

    # Move to the resource location
    move_to(resource_position)
    print(f"Moved to {resource_type} patch at {resource_position}")

    # Harvest the resource
    harvested = harvest_resource(resource_position, quantity)
    print(f"Harvested {harvested} units of {resource_type}")

    # Check if we harvested the required amount
    inventory = inspect_inventory()
    actual_quantity = inventory.get(resource_type, 0)
    assert actual_quantity >= quantity, f"Failed to gather enough {resource_type}. Required: {quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} units of {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

# Assert statements to ensure we have gathered enough resources
assert final_inventory.get(Resource.IronOre, 0) >= 18, "Not enough Iron Ore"
assert final_inventory.get(Resource.Stone, 0) >= 6, "Not enough Stone"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Not enough Coal"

print("Successfully gathered all necessary resources.")

"""
Step 3: Craft stone furnace. We need to craft a stone furnace using 5 stone.
"""
# Craft the stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 Stone Furnace")

# Verify that we have crafted the stone furnace
inventory = inspect_inventory()
stone_furnaces = inventory.get(Prototype.StoneFurnace, 0)
assert stone_furnaces >= 1, f"Failed to craft Stone Furnace. Expected at least 1, but got {stone_furnaces}"
print(f"Successfully crafted Stone Furnace. Current inventory: {inventory}")

"""
Step 4: Smelt iron plates. We need to smelt 18 iron ore into iron plates. 
- Place the stone furnace
- Add coal as fuel
- Smelt 18 iron ore into iron plates
"""
# Place the Stone Furnace at the origin
origin = Position(x=0, y=0)
move_to(origin)
stone_furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed Stone Furnace at {stone_furnace.position}")

# Insert coal into the Stone Furnace as fuel
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
stone_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=coal_in_inventory)
print(f"Inserted {coal_in_inventory} units of Coal into the Stone Furnace")

# Insert all available Iron Ore into the Stone Furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
stone_furnace = insert_item(Prototype.IronOre, stone_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} units of Iron Ore into the Stone Furnace")

# Calculate expected number of Iron Plates after smelting
initial_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
expected_iron_plates = initial_iron_plates + min(iron_ore_in_inventory, coal_in_inventory)

# Wait for smelting to complete; each unit takes approximately 1 second
smelting_time = min(iron_ore_in_inventory, coal_in_inventory)
sleep(smelting_time)

# Extract Iron Plates from the Stone Furnace once smelting is complete
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, stone_furnace.position, quantity=smelting_time)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= expected_iron_plates:
        break
    sleep(10)  # Allow additional time if needed

print(f"Extracted Iron Plates; Current Inventory Count: {current_iron_plate_count}")

# Final assertion check to ensure successful completion of smelting process
assert current_iron_plate_count >= expected_iron_plates, f"Failed to obtain expected number of Iron Plates. Expected: {expected_iron_plates}, Actual: {current_iron_plate_count}"
print(f"Successfully obtained {current_iron_plate_count} Iron Plates in the inventory")

# Check the fuel level in the Stone Furnace
coal_in_furnace = stone_furnace.fuel.get(Prototype.Coal, 0)
print(f"Coal remaining in the Stone Furnace: {coal_in_furnace}")

# Check the remaining Iron Ore in the Stone Furnace
iron_ore_in_furnace = stone_furnace.furnace_source.get(Prototype.IronOre, 0)
print(f"Iron Ore remaining in the Stone Furnace: {iron_ore_in_furnace}")

# Extract any remaining Iron Plates from the Stone Furnace
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, stone_furnace.position, quantity=smelting_time)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= expected_iron_plates:
        break
    sleep(10)  # Allow additional time if needed

print(f"Extracted remaining Iron Plates; Final Inventory Count: {current_iron_plate_count}")

# Final assertion check to ensure successful completion of smelting process
assert current_iron_plate_count >= expected_iron_plates, f"Failed to obtain expected number of Iron Plates after extraction. Expected: {expected_iron_plates}, Actual: {current_iron_plate_count}"
print(f"Successfully obtained {current_iron_plate_count} Iron Plates in the inventory after final extraction")

"""
Step 5: Craft iron gear wheels. We need to craft 3 iron gear wheels using 6 iron plates.
"""
# Craft 3 Iron Gear Wheels using 6 Iron Plates
craft_item(Prototype.IronGearWheel, quantity=3)
print("Crafted 3 Iron Gear Wheels")

# Verify that we have crafted the Iron Gear Wheels
inventory = inspect_inventory()
iron_gear_wheels = inventory.get(Prototype.IronGearWheel, 0)
assert iron_gear_wheels >= 3, f"Failed to craft 3 Iron Gear Wheels. Expected at least 3, but got {iron_gear_wheels}"

print(f"Successfully crafted 3 Iron Gear Wheels. Current inventory: {inventory}")

"""
Step 6: Craft burner mining drill. We need to craft a burner mining drill using 3 iron gear wheels, 3 iron plates, and 1 stone furnace.
"""
# Craft the Burner Mining Drill
craft_item(Prototype.BurnerMiningDrill, quantity=1)
print("Crafted 1 Burner Mining Drill")

# Verify that we have crafted the Burner Mining Drill
inventory = inspect_inventory()
burner_mining_drills = inventory.get(Prototype.BurnerMiningDrill, 0)
assert burner_mining_drills >= 1, f"Failed to craft Burner Mining Drill. Expected at least 1, but got {burner_mining_drills}"

print(f"Successfully crafted Burner Mining Drill. Current inventory: {inventory}")

"""
Step 7: Craft firearm magazine. We need to craft 1 firearm magazine using 4 iron plates.
"""
# Craft the Firearm Magazine
craft_item(Prototype.FirearmMagazine, quantity=1)
print("Crafted 1 Firearm Magazine")

# Verify that we have crafted the Firearm Magazine
inventory = inspect_inventory()
firearm_magazines = inventory.get(Prototype.FirearmMagazine, 0)
assert firearm_magazines >= 1, f"Failed to craft Firearm Magazine. Expected at least 1, but got {firearm_magazines}"

print(f"Successfully crafted Firearm Magazine. Current inventory: {inventory}")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory after crafting: {final_inventory}")

# Assert statements to ensure we have crafted all necessary items
assert final_inventory.get(Prototype.BurnerMiningDrill, 0) >= 1, "Not enough Burner Mining Drills"
assert final_inventory.get(Prototype.FirearmMagazine, 0) >= 1, "Not enough Firearm Magazines"

print("Successfully crafted all necessary items.")

