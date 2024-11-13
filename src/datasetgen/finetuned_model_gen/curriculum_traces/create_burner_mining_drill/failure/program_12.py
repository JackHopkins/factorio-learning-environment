
from factorio_instance import *

"""
Step 1: Print recipes
"""
# Get the recipe for burner-mining-drill
recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)

# Print the recipe details
print("burner-mining-drill Recipe:")
print(f"Ingredients:")
for ingredient in recipe.ingredients:
    print(f"- {ingredient.count} {ingredient.name}")

print("\ntransport-belt Recipe:")
# Get the recipe for transport-belt
recipe = get_prototype_recipe(Prototype.TransportBelt)
print("transport-belt Recipe:")
print(f"Ingredients:")
for ingredient in recipe.ingredients:
    print(f"- {ingredient.count} {ingredient.name}")

print("\nunderground-belt Recipe:")
# Get the recipe for underground-belt
recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print("underground-belt Recipe:")
print(f"Ingredients:")
for ingredient in recipe.ingredients:
    print(f"- {ingredient.count} {ingredient.name}")

"""
Step 2: Gather resources
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 12),
    (Resource.IronOre, 25),
    (Resource.Coal, 2)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    
    # Move to the resource location
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    
    # Assert that we have at least as much as required
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:", final_inventory)

# Verify that all required resources are present in sufficient quantities
for resource_type, required_quantity in resources_to_gather:
    assert final_inventory.get(resource_type, 0) >= required_quantity, f"Insufficient {resource_type} in final inventory"

print("Successfully gathered all required resources")

"""
Step 3: Craft stone furnaces
"""
# Craft 2 stone furnaces
craft_item(Prototype.StoneFurnace, quantity=2)

# Check inventory for stone furnaces
inventory = inspect_inventory()
stone_furnaces = inventory.get(Prototype.StoneFurnace, 0)
assert stone_furnaces >= 2, f"Failed to craft stone furnaces. Expected at least 2, but got {stone_furnaces}"
print(f"Successfully crafted {stone_furnaces} stone furnaces")

# Place one stone furnace for smelting
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)

"""
Step 4: Smelt iron plates
"""
# Insert coal into the furnace as fuel
insert_item(Prototype.Coal, furnace, quantity=2)

# Insert iron ore into the furnace
insert_item(Prototype.IronOre, furnace, quantity=25)

# Wait for smelting to complete (assuming 0.7 seconds per unit * 25 units)
sleep(25 * 0.7)

# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, furnace.position, quantity=25)
    inventory = inspect_inventory()
    if inventory.get(Prototype.IronPlate, 0) >= 25:
        break
    sleep(5)

# Final check for iron plates
iron_plates = inventory.get(Prototype.IronPlate, 0)
assert iron_plates >= 25, f"Failed to obtain enough Iron Plates. Expected at least 25 but got {iron_plates}"
print(f"Successfully obtained {iron_plates} Iron Plates")

"""
Step 5: Craft iron gear wheels
"""
# Craft 4 iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=4)

# Check inventory for iron gear wheels
inventory = inspect_inventory()
iron_gear_wheels = inventory.get(Prototype.IronGearWheel, 0)
assert iron_gear_wheels >= 4, f"Failed to craft iron gear wheels. Expected at least 4, but got {iron_gear_wheels}"
print(f"Successfully crafted {iron_gear_wheels} iron gear wheels")

"""
Step 6: Craft burner-mining-drill
"""
# Craft 1 burner-mining-drill
craft_item(Prototype.BurnerMiningDrill, quantity=1)

# Check inventory for burner-mining-drill
inventory = inspect_inventory()
burner_mining_drills = inventory.get(Prototype.BurnerMiningDrill, 0)
assert burner_mining_drills >= 1, f"Failed to craft burner-mining-drill. Expected at least 1, but got {burner_mining_drills}"
print(f"Successfully crafted {burner_mining_drills} burner-mining-drill")

"""
Step 7: Craft transport belts
"""
# Craft 14 transport belts
craft_item(Prototype.TransportBelt, quantity=14)

# Check inventory for transport belts
inventory = inspect_inventory()
transport_belts = inventory.get(Prototype.TransportBelt, 0)
assert transport_belts >= 14, f"Failed to craft transport belts. Expected at least 14, but got {transport_belts}"
print(f"Successfully crafted {transport_belts} transport belts")

"""
Step 8: Craft underground belts
"""
# Craft 4 underground belts
craft_item(Prototype.UndergroundBelt, quantity=4)

# Check inventory for underground belts
inventory = inspect_inventory()
underground_belts = inventory.get(Prototype.UndergroundBelt, 0)
assert underground_belts >= 4, f"Failed to craft underground belts. Expected at least 4, but got {underground_belts}"
print(f"Successfully crafted {underground_belts} underground belts")

"""
Final Inventory Check
"""
final_inventory = inspect_inventory()
print("Final inventory after crafting:")
print(f"Burner-Mining-Drills: {final_inventory.get(Prototype.BurnerMiningDrill, 0)}")
print(f"Transport Belts: {final_inventory.get(Prototype.TransportBelt, 0)}")
print(f"Underground Belts: {final_inventory.get(Prototype.UndergroundBelt, 0)}")
print(f"Stone Furnaces: {final_inventory.get(Prototype.StoneFurnace, 0)}")
