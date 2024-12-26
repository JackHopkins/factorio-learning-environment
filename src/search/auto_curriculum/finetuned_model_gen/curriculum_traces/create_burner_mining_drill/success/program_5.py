
from factorio_instance import *

"""
Step 1: Print recipes. We need to craft a burner mining drill. To do this, we need to print the recipe for burner mining drill, stone furnace, and iron gear wheel.
"""
# Print recipe for burner mining drill
print("Burner Mining Drill Recipe:")
print("3 iron gear wheels")
print("1 stone furnace")
print("3 iron plates")

# Print recipe for stone furnace
print("\nStone Furnace Recipe:")
print("5 stone")

# Print recipe for iron gear wheel
print("\nIron Gear Wheel Recipe:")
print("2 iron plates")

"""
Step 2: Gather raw resources. We need to mine:
- At least 12 stone (5 for stone furnace, 7 for extra stone furnace)
- At least 21 iron ore (15 for iron gear wheels, 5 for plates, 1 for extra plate)
- At least 3 coal (for smelting)
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 12),
    (Resource.IronOre, 21),
    (Resource.Coal, 3)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    
    # Move to the resource
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    
    # Get current inventory to check how much was actually harvested
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    
    # Assert that we have harvested at least the required amount
    assert actual_quantity >= required_quantity, f"Failed to harvest enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully harvested {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final Inventory:")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")

# Assert that we have all required quantities
assert final_inventory.get(Resource.Stone, 0) >= 12, "Not enough stone"
assert final_inventory.get(Resource.IronOre, 0) >= 21, "Not enough iron ore"
assert final_inventory.get(Resource.Coal, 0) >= 3, "Not enough coal"

print("Successfully gathered all required resources!")

"""
Step 3: Craft and set up stone furnaces.
- Craft 2 stone furnaces (one for smelting, one for the drill)
- Place one stone furnace on the ground
- Add coal to the furnace as fuel
"""
# Craft 2 stone furnaces
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=2)
print(f"Crafted {crafted_furnaces} Stone Furnaces")

# Move to a suitable position for placing the furnace
move_to(Position(x=0, y=0))

# Place one of the stone furnaces
smelting_furnace = place_entity(Prototype.StoneFurnace, position=Position(x=1, y=0))
print(f"Placed a Stone Furnace at {smelting_furnace.position}")

# Insert coal into the stone furnace as fuel
updated_furnace = insert_item(Prototype.Coal, smelting_furnace, quantity=3)
print("Inserted coal into the Stone Furnace")

# Verify that the furnace has fuel
coal_in_furnace = updated_furnace.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace > 0, "Failed to fuel Stone Furnace"
print("Stone Furnace successfully fueled")

# Check current inventory
current_inventory = inspect_inventory()
print("Current Inventory after crafting and setting up furnaces:")
print(f"Stone Furnaces: {current_inventory.get(Prototype.StoneFurnace, 0)}")
print(f"Coal: {current_inventory.get(Prototype.Coal, 0)}")

# Assert that we still have at least one Stone Furnace for the drill
assert current_inventory.get(Prototype.StoneFurnace, 0) >= 1, "Not enough Stone Furnaces for crafting the drill"

print("Successfully crafted and set up Stone Furnaces!")

"""
Step 4: Smelt iron plates.
- Smelt 21 iron ore into iron plates (15 for iron gear wheels, 5 for plates, 1 for extra plate)
"""
# Check initial inventory before smelting
initial_inventory = inspect_inventory()
print("Initial Inventory before smelting:")
print(f"Iron Ore: {initial_inventory.get(Prototype.IronOre, 0)}")
print(f"Iron Plates: {initial_inventory.get(Prototype.IronPlate, 0)}")

# Get the number of iron ore in the inventory
iron_ore_in_inventory = initial_inventory.get(Prototype.IronOre, 0)

# Insert all available iron ore into the stone furnace
updated_furnace = insert_item(Prototype.IronOre, smelting_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} Iron Ore into the Stone Furnace")

# Calculate expected number of iron plates after smelting
expected_iron_plates = initial_inventory.get(Prototype.IronPlate, 0) + iron_ore_in_inventory

# Wait for smelting to complete
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_in_inventory)
sleep(total_smelting_time)

# Extract iron plates from the furnace
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, smelting_furnace.position, quantity=iron_ore_in_inventory)
    current_inventory = inspect_inventory()
    actual_iron_plates = current_inventory.get(Prototype.IronPlate, 0)
    
    if actual_iron_plates >= expected_iron_plates:
        break
    
    sleep(10)  # Allow additional time if needed

print("Final Inventory after smelting:")
print(f"Iron Plates: {actual_iron_plates}")

# Assert that we have smelted at least 21 Iron Plates
assert actual_iron_plates >= 21, f"Failed to smelt enough Iron Plates. Expected: 21, Actual: {actual_iron_plates}"

print("Successfully smelted at least 21 Iron Plates!")

"""
Step 5: Craft iron gear wheels.
- Craft 6 iron gear wheels (3 for the drill, 3 for stone furnace)
"""
# Craft 6 iron gear wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=6)
print(f"Crafted {crafted_gear_wheels} Iron Gear Wheels")

# Check current inventory
current_inventory = inspect_inventory()
iron_gear_wheels_in_inventory = current_inventory.get(Prototype.IronGearWheel, 0)

print("Current Inventory after crafting Iron Gear Wheels:")
print(f"Iron Gear Wheels: {iron_gear_wheels_in_inventory}")

# Assert that we have crafted 6 Iron Gear Wheels
assert iron_gear_wheels_in_inventory >= 6, f"Failed to craft enough Iron Gear Wheels. Expected: 6, Actual: {iron_gear_wheels_in_inventory}"

print("Successfully crafted 6 Iron Gear Wheels!")

"""
Step 6: Craft burner mining drill.
- Use 3 iron gear wheels, 1 stone furnace, 3 iron plates to craft 1 burner mining drill
"""
# Craft 1 burner mining drill
crafted_drills = craft_item(Prototype.BurnerMiningDrill, quantity=1)
print(f"Crafted {crafted_drills} Burner Mining Drill")

# Check current inventory
current_inventory = inspect_inventory()
burner_mining_drills_in_inventory = current_inventory.get(Prototype.BurnerMiningDrill, 0)

print("Current Inventory after crafting Burner Mining Drill:")
print(f"Burner Mining Drills: {burner_mining_drills_in_inventory}")

# Assert that we have crafted 1 Burner Mining Drill
assert burner_mining_drills_in_inventory >= 1, f"Failed to craft Burner Mining Drill. Expected: 1, Actual: {burner_mining_drills_in_inventory}"

print("Successfully crafted 1 Burner Mining Drill!")

"""
Step 7: Verify the crafting.
- Check the inventory to ensure we have 1 burner mining drill
"""
# Check final inventory
final_inventory = inspect_inventory()
burner_mining_drills_in_final_inventory = final_inventory.get(Prototype.BurnerMiningDrill, 0)

print("Final Inventory Check:")
print(f"Burner Mining Drills: {burner_mining_drills_in_final_inventory}")

# Assert that we have exactly 1 Burner Mining Drill
assert burner_mining_drills_in_final_inventory == 1, f"Incorrect number of Burner Mining Drills. Expected: 1, Actual: {burner_mining_drills_in_final_inventory}"

print("Successfully verified that we have crafted 1 Burner Mining Drill!")

print("Objective completed successfully!")

