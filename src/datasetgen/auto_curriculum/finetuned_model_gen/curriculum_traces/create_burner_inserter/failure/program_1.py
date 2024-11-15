

from factorio_instance import *

"""
Main policy to carry out the objective of crafting a burner-inserter from scratch.
"""

"""
Step 1: Print recipes
"""
print("Recipes:")
print("Burner-Inserter: 1 iron gear wheel, 1 transport belt")
print("Iron Gear Wheel: 2 iron plates")
print("Transport Belt: 1 iron gear wheel, 1 iron plate")
print("Stone Furnace: 5 stone")
print("Smelting: 1 iron ore -> 1 iron plate")

"""
Step 2: Gather raw resources
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 9),
    (Resource.Coal, 2),
    (Resource.Stone, 6)
]

# Gather the resources
for resource_type, required_quantity in resources_to_gather:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

"""
Step 3: Craft intermediate products
"""
# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 Stone Furnace")

# Place the stone furnace
origin = Position(x=0, y=0)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed Stone Furnace at {furnace.position}")

# Insert coal into the furnace as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=2)
print("Inserted 2 Coal into the Stone Furnace")

# Insert iron ore into the furnace to smelt iron plates
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} Iron Ore into the Stone Furnace")

# Wait for smelting to complete
smelting_time = 0.7 * iron_ore_in_inventory  # Assuming 0.7 seconds per iron plate
sleep(smelting_time)

# Extract iron plates
iron_plates_before = inspect_inventory().get(Prototype.IronPlate, 0)
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    iron_plates_after = inspect_inventory().get(Prototype.IronPlate, 0)
    if iron_plates_after >= iron_plates_before + iron_ore_in_inventory:
        break
    sleep(5)

print(f"Extracted Iron Plates; Current Inventory Count: {iron_plates_after}")

# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=2)
print("Crafted 2 Iron Gear Wheels")

"""
Step 4: Craft transport belt
"""
craft_item(Prototype.TransportBelt, quantity=1)
print("Crafted 1 Transport Belt")

"""
Step 5: Craft burner-inserter
"""
craft_item(Prototype.BurnerInserter, quantity=1)
print("Crafted 1 Burner-Inserter")

"""
Step 6: Verify crafting
"""
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.BurnerInserter, 0) >= 1, "Failed to craft Burner-Inserter"
assert final_inventory.get(Prototype.IronPlate, 0) >= 1, "Missing extra Iron Plate"
assert final_inventory.get(Prototype.Stone, 0) >= 1, "Missing extra Stone"
print("Successfully crafted Burner-Inserter and verified all required items")

