

from factorio_instance import *

"""
Step 1: Print recipes
"""
print("Recipes for items we need to craft:")
print("Transport Belt: 1 iron gear wheel, 1 iron plate")
print("Fast Transport Belt: 1 transport belt, 1 iron gear wheel")
print("Underground Belt: 5 iron plates, 5 transport belts")
print("Iron Gear Wheel: 2 iron plates")
print("Stone Furnace: 5 stone")
print("Iron Plate: 1 iron ore")
print("Steel Plate: 5 iron plates")
print("Electronic Circuit: 3 copper cables, 1 iron plate")
print("Copper Cable: 1 copper plate")
print("Pipe: 1 iron plate")

"""
Step 2: Gather initial resources
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 21),
    (Resource.Coal, 2),
    (Resource.Stone, 12),
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
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Print the final inventory
final_inventory = inspect_inventory()
print("Final inventory after gathering resources:")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")

# Verify that we have at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 21, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Not enough Coal"
assert final_inventory.get(Resource.Stone, 0) >= 12, "Not enough Stone"

print("Successfully gathered all required resources!")

"""
Step 3: Craft stone furnaces
"""
# Craft 2 stone furnaces
craft_item(Prototype.StoneFurnace, quantity=2)

# Verify that we have crafted the stone furnaces
inventory_after_crafting_furnaces = inspect_inventory()
stone_furnaces_count = inventory_after_crafting_furnaces.get(Prototype.StoneFurnace, 0)
assert stone_furnaces_count >= 2, f"Failed to craft enough Stone Furnaces. Expected: 2, Actual: {stone_furnaces_count}"
print(f"Successfully crafted {stone_furnaces_count} Stone Furnaces")

"""
Step 4: Set up smelting operation
"""
# Place first furnace and smelt iron plates
iron_ore_position = nearest(Resource.IronOre)
furnace1 = place_entity(Prototype.StoneFurnace, position=iron_ore_position)
move_to(furnace1.position)
insert_item(Prototype.Coal, furnace1, quantity=1)
insert_item(Prototype.IronOre, furnace1, quantity=21)
print("Inserted Iron Ore and Coal into the first Stone Furnace")

# Place second furnace and smelt steel plates
furnace2 = place_entity(Prototype.StoneFurnace, position=Position(x=furnace1.position.x + 2, y=furnace1.position.y))
move_to(furnace2.position)
insert_item(Prototype.Coal, furnace2, quantity=1)
# We need 5 iron plates for each steel plate, so insert 10 iron plates for 2 steel plates
insert_item(Prototype.IronPlate, furnace2, quantity=10)
print("Inserted Iron Plates and Coal into the second Stone Furnace")

# Wait for smelting to complete
smelting_time = max(21 * 0.7, 10 * 3.5)  # 0.7 seconds per iron plate, 3.5 seconds per steel plate
sleep(smelting_time)

# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, furnace1.position, quantity=21)
    # Check inventory
    current_inventory = inspect_inventory()
    if current_inventory.get(Prototype.IronPlate, 0) >= 21:
        break
    sleep(5)
print("Extracted Iron Plates from the first Stone Furnace")

# Extract steel plates
for _ in range(max_attempts):
    extract_item(Prototype.SteelPlate, furnace2.position, quantity=2)
    # Check inventory
    current_inventory = inspect_inventory()
    if current_inventory.get(Prototype.SteelPlate, 0) >= 2:
        break
    sleep(5)
print("Extracted Steel Plates from the second Stone Furnace")

# Verify that we have enough iron plates and steel plates
inventory_after_smelting = inspect_inventory()
assert inventory_after_smelting.get(Prototype.IronPlate, 0) >= 21, f"Failed to smelt enough Iron Plates. Expected: 21, Actual: {inventory_after_smelting.get(Prototype.IronPlate, 0)}"
assert inventory_after_smelting.get(Prototype.SteelPlate, 0) >= 2, f"Failed to smelt enough Steel Plates. Expected: 2, Actual: {inventory_after_smelting.get(Prototype.SteelPlate, 0)}"
print(f"Successfully smelted {inventory_after_smelting.get(Prototype.IronPlate, 0)} Iron Plates and {inventory_after_smelting.get(Prototype.SteelPlate, 0)} Steel Plates")

"""
Step 5: Craft intermediate items
"""
# Craft Iron Gear Wheels
craft_item(Prototype.IronGearWheel, quantity=7)
print("Crafted 7 Iron Gear Wheels")

# Craft Pipes
craft_item(Prototype.Pipe, quantity=2)
print("Crafted 2 Pipes")

# Craft Electronic Circuits
craft_item(Prototype.ElectronicCircuit, quantity=2)
print("Crafted 2 Electronic Circuits")

"""
Step 6: Craft final items
"""
# Craft Transport Belts
craft_item(Prototype.TransportBelt, quantity=4)
print("Crafted 4 Transport Belts")

# Craft Fast Transport Belts
craft_item(Prototype.FastTransportBelt, quantity=1)
print("Crafted 1 Fast Transport Belt")

# Craft Underground Belt
craft_item(Prototype.UndergroundBelt, quantity=1)
print("Crafted 1 Underground Belt")

"""
Step 7: Verify final inventory
"""
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.UndergroundBelt, 0) >= 1, "Failed to craft Underground Belt"
print("Successfully crafted Underground Belt!")
print(f"Final inventory: {final_inventory}")

