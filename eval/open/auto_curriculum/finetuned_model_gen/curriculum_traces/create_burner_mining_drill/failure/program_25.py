

from instance import *

"""
Step 1: Gather raw resources
- Mine iron ore (at least 9 for plates, 6 for gear wheels)
- Mine stone (at least 5 for the furnace)
- Mine coal (at least 2 for fueling the furnace)
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 15),
    (Resource.Stone, 7),
    (Resource.Coal, 4)
]

# Loop through each resource and gather it
for resource_type, required_quantity in resources_to_gather:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
for resource_type, required_quantity in resources_to_gather:
    actual_quantity = final_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Final check failed for {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"

print("Successfully gathered all required resources")
print(f"Final inventory: {final_inventory}")

"""
Step 2: Craft and set up the stone furnace
- Craft 1 stone furnace
- Place the stone furnace
- Insert coal as fuel
"""

# Craft the stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 stone furnace")

# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed stone furnace at {furnace.position}")

# Insert coal as fuel
coal_in_inventory = inspect_inventory()[Prototype.Coal]
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=coal_in_inventory)
print(f"Inserted {coal_in_inventory} coal into the stone furnace")

"""
Step 3: Smelt iron plates
- Smelt 9 iron ore into iron plates
"""

# Insert iron ore into the stone furnace
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} iron ore into the stone furnace")

# Wait for smelting to complete (approximately 0.7 seconds per ore)
smelting_time = iron_ore_in_inventory * 0.7
sleep(smelting_time)

# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    iron_plates_in_inventory = inspect_inventory()[Prototype.IronPlate]
    if iron_plates_in_inventory >= 15:
        break
    sleep(5)

print(f"Extracted {iron_plates_in_inventory} iron plates from the stone furnace")

"""
Step 4: Craft iron gear wheels
- Craft 3 iron gear wheels (requires 6 iron plates)
"""

# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=3)
print("Crafted 3 iron gear wheels")

"""
Step 5: Craft the burner mining drill
- Craft 1 burner mining drill
"""

# Craft the burner mining drill
craft_item(Prototype.BurnerMiningDrill, quantity=1)
print("Crafted 1 burner mining drill")

# Verify that we have crafted the burner mining drill
burner_mining_drill_count = inspect_inventory()[Prototype.BurnerMiningDrill]
assert burner_mining_drill_count >= 1, f"Failed to craft burner mining drill. Expected: 1, Actual: {burner_mining_drill_count}"

print("Successfully crafted a burner mining drill")
print(f"Final inventory: {inspect_inventory()}")

