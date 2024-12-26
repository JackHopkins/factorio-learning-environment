
from factorio_instance import *

"""
Step 1: Print recipes
- Print recipes for burner-mining-drill
- Print recipes for intermediate components (iron gear wheels, stone furnace)
"""

# Get and print recipe for burner-mining-drill
burner_mining_drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
print("burner-mining-drill Recipe:")
print(f"Ingredients: {burner_mining_drill_recipe.ingredients}")

# Get and print recipe for iron gear wheels
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print("\nIron Gear Wheel Recipe:")
print(f"Ingredients: {iron_gear_wheel_recipe.ingredients}")

# Get and print recipe for stone furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print("\nStone Furnace Recipe:")
print(f"Ingredients: {stone_furnace_recipe.ingredients}")

"""
Step 2: Gather resources
- Mine iron ore (at least 26)
- Mine stone (at least 6)
- Mine coal (at least 2 for fuel)
"""
# Define required resources
required_resources = [
    (Resource.IronOre, 26),
    (Resource.Stone, 6),
    (Resource.Coal, 2)
]

# Loop through each required resource
for resource_type, required_quantity in required_resources:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    # Move to the resource location
    move_to(resource_position)
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to harvest enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully harvested {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 26, "Not enough Iron Ore"
assert final_inventory.get(Resource.Stone, 0) >= 6, "Not enough Stone"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Not enough Coal"

print("Successfully gathered all required resources!")

"""
Step 3: Craft and set up stone furnace
- Craft 1 stone furnace
- Place the stone furnace
- Add coal to the furnace as fuel
"""
# Craft 1 stone furnace
crafted = craft_item(Prototype.StoneFurnace, 1)
print(f"Crafted {crafted} Stone Furnace(s)")
assert crafted == 1, f"Failed to craft Stone Furnace. Expected 1, but crafted {crafted}"

# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
stone_furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed Stone Furnace at {stone_furnace.position}")

# Add coal to the furnace as fuel
coal_in_inventory = inspect_inventory()[Prototype.Coal]
updated_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=coal_in_inventory)
print(f"Inserted {coal_in_inventory} Coal into Stone Furnace")

# Verify that the furnace has fuel
furnace_coal = updated_furnace.fuel.get(Prototype.Coal, 0)
assert furnace_coal > 0, "Failed to add fuel to Stone Furnace"
print("Stone Furnace is successfully set up and fueled")

"""
Step 4: Smelt iron plates
- Smelt at least 26 iron ore into iron plates
"""
# Check initial inventory for iron ore
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
print(f"Iron Ore in Inventory: {iron_ore_in_inventory}")

# Insert all available iron ore into the furnace
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} Iron Ore into Stone Furnace")

# Calculate expected number of iron plates
initial_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
expected_iron_plate_count = initial_iron_plate_count + iron_ore_in_inventory

# Wait for smelting to complete
smelting_time_per_unit = 0.7
total_smelting_time = smelting_time_per_unit * iron_ore_in_inventory
sleep(total_smelting_time)

# Attempt to extract iron plates multiple times if necessary
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= expected_iron_plate_count:
        break
    sleep(10)  # Allow additional time for smelting if needed

print(f"Extracted Iron Plates; Current Inventory Count: {current_iron_plate_count}")
assert current_iron_plate_count >= 26, f"Failed to obtain required number of Iron Plates. Expected at least 26, but got {current_iron_plate_count}"

print("Successfully smelted required number of Iron Plates!")

"""
Step 5: Craft intermediate components
- Craft 3 iron gear wheels (requires 6 iron plates)
"""
# Craft 3 iron gear wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, 3)
print(f"Crafted {crafted_gear_wheels} Iron Gear Wheel(s)")
assert crafted_gear_wheels == 3, f"Failed to craft Iron Gear Wheels. Expected 3, but crafted {crafted_gear_wheels}"

# Verify that the iron gear wheels are in inventory
iron_gear_wheels_in_inventory = inspect_inventory()[Prototype.IronGearWheel]
print(f"Iron Gear Wheels in Inventory: {iron_gear_wheels_in_inventory}")
assert iron_gear_wheels_in_inventory >= 3, f"Insufficient Iron Gear Wheels in inventory. Expected at least 3, but found {iron_gear_wheels_in_inventory}"

print("Successfully crafted required number of Iron Gear Wheels!")

"""
Step 6: Craft burner-mining-drill
- Craft 1 burner-mining-drill (requires 3 iron gear wheels, 3 iron plates, 1 stone furnace)
"""
# Craft 1 burner-mining-drill
crafted_drill = craft_item(Prototype.BurnerMiningDrill, 1)
print(f"Crafted {crafted_drill} Burner Mining Drill(s)")
assert crafted_drill == 1, f"Failed to craft Burner Mining Drill. Expected 1, but crafted {crafted_drill}"

# Verify that the burner mining drill is in inventory
burner_mining_drill_in_inventory = inspect_inventory()[Prototype.BurnerMiningDrill]
print(f"Burner Mining Drills in Inventory: {burner_mining_drill_in_inventory}")
assert burner_mining_drill_in_inventory >= 1, f"Insufficient Burner Mining Drills in inventory. Expected at least 1, but found {burner_mining_drill_in_inventory}"

print("Successfully crafted required number of Burner Mining Drills!")

"""
Step 7: Verify crafting
- Check inventory to confirm we have 1 burner-mining-drill
"""
# Check inventory to confirm we have 1 burner-mining-drill
final_inventory_check = inspect_inventory()
burner_mining_drill_count = final_inventory_check[Prototype.BurnerMiningDrill]
print(f"Final Inventory Check - Burner Mining Drill Count: {burner_mining_drill_count}")
assert burner_mining_drill_count >= 1, f"Final check failed! Expected at least 1 Burner Mining Drill in inventory, but found {burner_mining_drill_count}"

print("Successfully verified that we have crafted the required number of Burner Mining Drills!")

