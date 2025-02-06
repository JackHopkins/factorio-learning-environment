

from instance import *

"""
Step 1: Gather raw resources
- Mine 6 stone
- Mine 26 iron ore
- Mine 2 coal
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 6),
    (Resource.IronOre, 26),
    (Resource.Coal, 2)
]

# Loop over each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    print(f"Nearest {resource_type} found at: {resource_position}")
    
    # Move to the resource
    move_to(resource_position)
    print(f"Moved to {resource_type} position")
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    print(f"Harvested {harvested} {resource_type}")
    
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory after gathering resources: {final_inventory}")

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.Stone, 0) >= 6, "Not enough stone"
assert final_inventory.get(Resource.IronOre, 0) >= 26, "Not enough iron ore"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Not enough coal"

print("Successfully gathered all required resources!")

"""
Step 2: Craft and set up furnaces
- Craft 1 stone furnace
- Place the furnace
- Add coal as fuel to the furnace
"""
# Craft 1 stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 stone furnace")

# Place the furnace at the origin
furnace_position = Position(x=0, y=0)
move_to(furnace_position)
furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)
print(f"Placed stone furnace at {furnace_position}")

# Add coal as fuel to the furnace
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
assert coal_in_inventory >= 2, f"Not enough coal in inventory to fuel furnace. Expected at least 2, but got {coal_in_inventory}"

updated_furnace = insert_item(Prototype.Coal, furnace, quantity=2)
print("Inserted coal into the stone furnace")

# Verify that the furnace is fueled
furnace_inventory = updated_furnace.fuel
coal_in_furnace = furnace_inventory.get(Prototype.Coal, 0)
assert coal_in_furnace > 0, "Failed to fuel furnace with coal"
print("Stone furnace successfully placed and fueled")

"""
Step 3: Smelt iron plates
- Smelt 26 iron ore into 26 iron plates
"""
# Insert Iron Ore into Furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
assert iron_ore_in_inventory >= 26, f"Not enough iron ore in inventory. Expected at least 26, but got {iron_ore_in_inventory}"

updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=26)
print("Inserted iron ore into the stone furnace")

# Wait for smelting to complete
smelting_time_per_unit = 1.5  # Assuming it takes 1.5 seconds to smelt one iron ore into an iron plate
total_smelting_time = int(smelting_time_per_unit * 26)
sleep(total_smelting_time)

# Extract Iron Plates
max_attempts_to_extract = 5
for attempt in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=26)
    current_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
    
    if current_iron_plates >= 26:
        break
    
    sleep(10)  # Wait a bit before trying again

# Final check
final_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
assert final_iron_plates >= 26, f"Failed to smelt enough iron plates. Expected at least 26, but got {final_iron_plates}"
print(f"Successfully smelted {final_iron_plates} iron plates")

"""
Step 4: Craft intermediate products
- Craft 3 iron gear wheels
"""
# Craft 3 Iron Gear Wheels
craft_item(Prototype.IronGearWheel, quantity=3)
print("Crafted 3 iron gear wheels")

# Verify that we have crafted the iron gear wheels
iron_gear_wheel_count = inspect_inventory().get(Prototype.IronGearWheel, 0)
assert iron_gear_wheel_count >= 3, f"Failed to craft enough iron gear wheels. Expected at least 3, but got {iron_gear_wheel_count}"
print(f"Successfully crafted {iron_gear_wheel_count} iron gear wheels")

"""
Step 5: Craft final products
- Craft 1 stone furnace
- Craft 1 burner mining drill
"""
# Craft 1 Stone Furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 stone furnace")

# Verify that we have crafted the stone furnace
stone_furnace_count = inspect_inventory().get(Prototype.StoneFurnace, 0)
assert stone_furnace_count >= 1, f"Failed to craft enough stone furnaces. Expected at least 1, but got {stone_furnace_count}"
print(f"Successfully crafted {stone_furnace_count} stone furnace(s)")

# Craft 1 Burner Mining Drill
craft_item(Prototype.BurnerMiningDrill, quantity=1)
print("Crafted 1 burner mining drill")

# Verify that we have crafted the burner mining drill
burner_mining_drill_count = inspect_inventory().get(Prototype.BurnerMiningDrill, 0)
assert burner_mining_drill_count >= 1, f"Failed to craft enough burner mining drills. Expected at least 1, but got {burner_mining_drill_count}"
print(f"Successfully crafted {burner_mining_drill_count} burner mining drill(s)")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

# Assert that we have all the required items
assert final_inventory.get(Prototype.BurnerMiningDrill, 0) >= 1, "Missing Burner Mining Drill"
assert final_inventory.get(Prototype.StoneFurnace, 0) >= 1, "Missing Stone Furnace"
assert final_inventory.get(Prototype.TransportBelt, 0) >= 4, "Missing Transport Belt"
assert final_inventory.get(Prototype.BurnerInserter, 0) >= 1, "Missing Burner Inserter"
assert final_inventory.get(Prototype.FirearmMagazine, 0) >= 1, "Missing Firearm Magazine"
assert final_inventory.get(Prototype.IronPlate, 0) >= 26, "Missing Iron Plates"
assert final_inventory.get(Prototype.IronGearWheel, 0) >= 3, "Missing Iron Gear Wheels"

print("Successfully crafted all required items!")

