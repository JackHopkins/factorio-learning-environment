

from instance import *

"""
Step 1: Print recipes to console
"""
# Print recipes for all items
print("Recipes:")
print("Burner Mining Drill: 3 iron gear wheels, 1 stone furnace, 3 iron plates")
print("Iron Gear Wheel: 2 iron plates")
print("Stone Furnace: 5 stone")
print("Transport Belt: 1 iron gear wheel, 1 iron plate (produces 2)")
print("Underground Belt: 5 iron gear wheels, 10 iron plates (produces 2)")

"""
Step 2: Gather initial resources
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 25), 
    (Resource.Stone, 12), 
    (Resource.Coal, 2)
]

# Loop over each resource type and quantity
for resource_type, quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    
    # Move to the resource
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, quantity=quantity)
    
    # Check if we successfully harvested the desired amount
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    
    assert actual_quantity >= quantity, f"Failed to gather enough {resource_type}. Required: {quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Print final inventory after gathering all resources
final_inventory = inspect_inventory()
print("Final inventory after gathering resources:", final_inventory)

# Assert that we have at least the minimum required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 25, "Not enough Iron Ore"
assert final_inventory.get(Resource.Stone, 0) >= 12, "Not enough Stone"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Not enough Coal"

print("Successfully gathered all required resources!")

"""
Step 3: Craft stone furnaces
"""
# Craft 2 stone furnaces
craft_item(Prototype.StoneFurnace, quantity=2)

# Verify crafting success
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace, 0) >= 2, f"Failed to craft stone furnaces. Expected at least 2, got {inventory.get(Prototype.StoneFurnace, 0)}"
print(f"Crafted {inventory.get(Prototype.StoneFurnace, 0)} stone furnaces.")

"""
Step 4: Smelt iron plates
"""
# Place a furnace at the origin
furnace_position = Position(x=0, y=0)
move_to(furnace_position)
furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)

# Insert coal into the furnace for fuel
insert_item(Prototype.Coal, furnace, quantity=2)
print("Inserted coal into the furnace.")

# Insert iron ore into the furnace
insert_item(Prototype.IronOre, furnace, quantity=25)
print("Inserted iron ore into the furnace.")

# Wait for smelting to complete
sleep(15)
print("Smelting complete.")

# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, furnace.position, quantity=25)
    inventory = inspect_inventory()
    if inventory.get(Prototype.IronPlate, 0) >= 25:
        break
    sleep(1)

# Verify that we have at least 25 iron plates
assert inventory.get(Prototype.IronPlate, 0) >= 25, f"Failed to obtain required number of iron plates. Expected at least 25, got {inventory.get(Prototype.IronPlate, 0)}"
print(f"Obtained {inventory.get(Prototype.IronPlate, 0)} iron plates.")

"""
Step 5: Craft iron gear wheels
"""
# Craft 10 iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=10)

# Verify crafting success
inventory = inspect_inventory()
assert inventory.get(Prototype.IronGearWheel, 0) >= 10, f"Failed to craft iron gear wheels. Expected at least 10, got {inventory.get(Prototype.IronGearWheel, 0)}"
print(f"Crafted {inventory.get(Prototype.IronGearWheel, 0)} iron gear wheels.")

"""
Step 6: Craft burner mining drill
"""
# Craft 1 burner mining drill
craft_item(Prototype.BurnerMiningDrill, quantity=1)

# Verify crafting success
inventory = inspect_inventory()
assert inventory.get(Prototype.BurnerMiningDrill, 0) >= 1, f"Failed to craft burner mining drill. Expected at least 1, got {inventory.get(Prototype.BurnerMiningDrill, 0)}"
print(f"Crafted {inventory.get(Prototype.BurnerMiningDrill, 0)} burner mining drill.")

"""
Step 7: Craft transport belts
"""
# Craft 14 transport belts
craft_item(Prototype.TransportBelt, quantity=14)

# Verify crafting success
inventory = inspect_inventory()
assert inventory.get(Prototype.TransportBelt, 0) >= 14, f"Failed to craft transport belts. Expected at least 14, got {inventory.get(Prototype.TransportBelt, 0)}"
print(f"Crafted {inventory.get(Prototype.TransportBelt, 0)} transport belts.")

"""
Step 8: Craft underground belts
"""
# Craft 4 underground belts
craft_item(Prototype.UndergroundBelt, quantity=4)

# Verify crafting success
inventory = inspect_inventory()
assert inventory.get(Prototype.UndergroundBelt, 0) >= 4, f"Failed to craft underground belts. Expected at least 4, got {inventory.get(Prototype.UndergroundBelt, 0)}"
print(f"Crafted {inventory.get(Prototype.UndergroundBelt, 0)} underground belts.")

"""
Final verification
"""
# Check final inventory
final_inventory = inspect_inventory()
print("Final inventory:", final_inventory)

# Assert that we have all the required items
assert final_inventory.get(Prototype.BurnerMiningDrill, 0) >= 1, "Missing Burner Mining Drill"
assert final_inventory.get(Prototype.TransportBelt, 0) >= 14, "Missing Transport Belts"
assert final_inventory.get(Prototype.UndergroundBelt, 0) >= 4, "Missing Underground Belts"

print("Successfully completed all tasks and crafted the required items!")

