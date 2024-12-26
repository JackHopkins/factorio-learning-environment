

from factorio_instance import *

"""
Step 1: Print recipes for required items. We need to print the recipes for:
- stone-furnace
- transport-belt
- underground-belt
- burner-mining-drill
- iron-gear-wheel
"""

# Get recipes for required items
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
burner_mining_drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)

# Print recipes
print("stone-furnace recipe:", stone_furnace_recipe)
print("transport-belt recipe:", transport_belt_recipe)
print("underground-belt recipe:", underground_belt_recipe)
print("burner-mining-drill recipe:", burner_mining_drill_recipe)
print("iron-gear-wheel recipe:", iron_gear_wheel_recipe)

"""
Step 2: Gather raw resources. We need to gather:
- 12 stone
- 2 coal
- 25 iron ore
"""

# Define required resources and their quantities
resources_to_gather = [
    (Resource.Stone, 12),
    (Resource.Coal, 2),
    (Resource.IronOre, 25)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    # Move to the resource
    move_to(resource_position)
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather required amount of {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()

# Verify final inventory contents
assert final_inventory.get(Resource.Stone, 0) >= 12, "Not enough Stone"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Not enough Coal"
assert final_inventory.get(Resource.IronOre, 0) >= 25, "Not enough Iron Ore"

print("Successfully gathered all required resources!")
print(f"Final inventory: {final_inventory}")

"""
Step 3: Craft stone furnaces. We need to craft 2 stone furnaces.
"""

# Craft 2 stone furnaces
crafted = craft_item(Prototype.StoneFurnace, quantity=2)
# Verify that we crafted the correct number of stone furnaces
inventory_after_crafting = inspect_inventory()
stone_furnaces_in_inventory = inventory_after_crafting.get(Prototype.StoneFurnace, 0)
assert stone_furnaces_in_inventory >= 2, f"Failed to craft required number of Stone Furnaces. Expected: 2, Found: {stone_furnaces_in_inventory}"
print(f"Successfully crafted {stone_furnaces_in_inventory} stone furnaces")

# Verify that we used the correct amount of stone
stone_used = 12 - inspect_inventory().get(Resource.Stone, 0)
assert stone_used == 12, f"Incorrect amount of stone used. Expected: 12, Found: {stone_used}"
print(f"Successfully used {stone_used} stone to craft 2 stone furnaces")

# Print the current inventory state
print(f"Current inventory: {inspect_inventory()}")

"""
Step 4: Set up smelting operation. We need to:
- Place a furnace
- Add coal to the furnace as fuel
- Smelt 25 iron ore into iron plates
"""

# Move to the origin (0,0)
move_to(Position(x=0, y=0)) 
print("Moved to origin (0,0)")

# Place a stone furnace at the origin
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
print(f"Placed a stone furnace at {furnace.position}")

# Add coal to the furnace as fuel
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
furnace_with_coal = insert_item(Prototype.Coal, furnace, quantity=coal_in_inventory)
coal_inserted = coal_in_inventory - inspect_inventory().get(Prototype.Coal, 0)
print(f"Inserted {coal_inserted} coal into the furnace")

# Add iron ore to the furnace for smelting
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
furnace_with_iron = insert_item(Prototype.IronOre, furnace_with_coal, quantity=iron_ore_in_inventory)
iron_inserted = iron_ore_in_inventory - inspect_inventory().get(Prototype.IronOre, 0)
print(f"Inserted {iron_inserted} iron ore into the furnace")

# Calculate expected number of iron plates
initial_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
expected_final_iron_plate_count = initial_iron_plate_count + iron_inserted

# Wait for smelting to complete
sleep(10)

# Extract iron plates from the furnace
MAX_ATTEMPTS = 5
for attempt in range(MAX_ATTEMPTS):
    extract_item(Prototype.IronPlate, furnace_with_iron.position, quantity=iron_inserted)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= expected_final_iron_plate_count:
        break
    sleep(5)

# Verify that we have the expected number of iron plates
final_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
assert final_iron_plate_count >= expected_final_iron_plate_count, f"Failed to obtain required number of Iron Plates. Expected: {expected_final_iron_plate_count}, Found: {final_iron_plate_count}"
print(f"Successfully obtained {final_iron_plate_count} Iron Plates")

print(f"Current inventory after smelting: {inspect_inventory()}")

"""
Step 5: Craft iron gear wheels. We need to craft 10 iron gear wheels.
"""

# Craft 10 Iron Gear Wheels
crafted = craft_item(Prototype.IronGearWheel, quantity=10)
print(f"Crafted {crafted} Iron Gear Wheels")

# Verify that we crafted the correct number of Iron Gear Wheels
inventory_after_crafting = inspect_inventory()
iron_gear_wheels_in_inventory = inventory_after_crafting.get(Prototype.IronGearWheel, 0)
assert iron_gear_wheels_in_inventory >= 10, f"Failed to craft required number of Iron Gear Wheels. Expected: 10, Found: {iron_gear_wheels_in_inventory}"
print(f"Successfully crafted {iron_gear_wheels_in_inventory} Iron Gear Wheels")

# Verify that we used the correct amount of Iron Plates
iron_plates_used = 20 - inspect_inventory().get(Prototype.IronPlate, 0)
assert iron_plates_used == 20, f"Incorrect amount of Iron Plates used. Expected: 20, Found: {iron_plates_used}"
print(f"Successfully used {iron_plates_used} Iron Plates to craft 10 Iron Gear Wheels")

# Print the current inventory state
print(f"Current inventory after crafting Iron Gear Wheels: {inspect_inventory()}")

"""
Step 6: Craft transport belts. We need to craft 14 transport belts.
"""

# Craft 14 Transport Belts
crafted = craft_item(Prototype.TransportBelt, quantity=14)
print(f"Crafted {crafted} Transport Belts")

# Verify that we crafted the correct number of Transport Belts
inventory_after_crafting = inspect_inventory()
transport_belts_in_inventory = inventory_after_crafting.get(Prototype.TransportBelt, 0)
assert transport_belts_in_inventory >= 14, f"Failed to craft required number of Transport Belts. Expected: 14, Found: {transport_belts_in_inventory}"
print(f"Successfully crafted {transport_belts_in_inventory} Transport Belts")

# Verify that we used the correct amount of Iron Gear Wheels and Iron Plates
iron_gear_wheels_used = 7 - inspect_inventory().get(Prototype.IronGearWheel, 0)
iron_plates_used = 3 - inspect_inventory().get(Prototype.IronPlate, 0)
assert iron_gear_wheels_used == 7, f"Incorrect amount of Iron Gear Wheels used. Expected: 7, Found: {iron_gear_wheels_used}"
assert iron_plates_used == 7, f"Incorrect amount of Iron Plates used. Expected: 7, Found: {iron_plates_used}"
print(f"Successfully used {iron_gear_wheels_used} Iron Gear Wheels and {iron_plates_used} Iron Plates to craft 14 Transport Belts")

# Print the current inventory state
print(f"Current inventory after crafting Transport Belts: {inspect_inventory()}")

"""
Step 7: Craft underground belts. We need to craft 4 underground belts.
"""

# Craft 4 Underground Belts
crafted = craft_item(Prototype.UndergroundBelt, quantity=4)
print(f"Crafted {crafted} Underground Belts")

# Verify that we crafted the correct number of Underground Belts
inventory_after_crafting = inspect_inventory()
underground_belts_in_inventory = inventory_after_crafting.get(Prototype.UndergroundBelt, 0)
assert underground_belts_in_inventory >= 4, f"Failed to craft required number of Underground Belts. Expected: 4, Found: {underground_belts_in_inventory}"
print(f"Successfully crafted {underground_belts_in_inventory} Underground Belts")

# Verify that we used the correct amount of Iron Gear Wheels and Iron Plates
iron_gear_wheels_used = 4 - inspect_inventory().get(Prototype.IronGearWheel, 0)
iron_plates_used = 0 - inspect_inventory().get(Prototype.IronPlate, 0)
assert iron_gear_wheels_used == 4, f"Incorrect amount of Iron Gear Wheels used. Expected: 4, Found: {iron_gear_wheels_used}"
assert iron_plates_used == 4, f"Incorrect amount of Iron Plates used. Expected: 4, Found: {iron_plates_used}"
print(f"Successfully used {iron_gear_wheels_used} Iron Gear Wheels and {iron_plates_used} Iron Plates to craft 4 Underground Belts")

# Print the current inventory state
print(f"Current inventory after crafting Underground Belts: {inspect_inventory()}")

"""
Step 8: Craft burner mining drill. We need to craft 1 burner mining drill.
"""

# Craft 1 Burner Mining Drill
crafted = craft_item(Prototype.BurnerMiningDrill, quantity=1)
print(f"Crafted {crafted} Burner Mining Drill")

# Verify that we crafted the correct number of Burner Mining Drills
inventory_after_crafting = inspect_inventory()
burner_mining_drills_in_inventory = inventory_after_crafting.get(Prototype.BurnerMiningDrill, 0)
assert burner_mining_drills_in_inventory >= 1, f"Failed to craft required number of Burner Mining Drills. Expected: 1, Found: {burner_mining_drills_in_inventory}"
print(f"Successfully crafted {burner_mining_drills_in_inventory} Burner Mining Drills")

# Print the final inventory state
print(f"Final inventory after completing all steps: {inspect_inventory()}")

