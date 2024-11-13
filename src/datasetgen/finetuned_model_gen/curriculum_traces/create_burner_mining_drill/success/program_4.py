
from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipes for:
- burner-mining-drill
- stone-furnace
- iron-gear-wheel
- iron-plate
- coal
- stone
- iron-ore
"""

"""
Step 1: Print recipes
- burner-mining-drill: 3 iron gear wheels, 1 stone furnace
- stone-furnace: 5 stone
- iron-gear-wheel: 2 iron plates
- iron-plate: 1 iron ore, smelts for 0.7 seconds
- coal: mined directly
- stone: mined directly
- iron-ore: mined directly
"""
print("Recipes:")
print("burner-mining-drill: 3 iron gear wheels, 1 stone furnace")
print("stone-furnace: 5 stone")
print("iron-gear-wheel: 2 iron plates")
print("iron-plate: 1 iron ore, smelts for 0.7 seconds")
print("coal: mined directly")
print("stone: mined directly")
print("iron-ore: mined directly")

"""
Step 2: Gather resources. We need to gather:
- stone: 12 (5 for each furnace, 2 extra)
- coal: 3 (for smelting iron plates)
- iron ore: 18 (12 for iron plates, 6 extra for safety)
- iron plates: 12 (6 for iron gear wheels, 6 extra)
- iron gear wheels: 6 (4 for the drill, 2 extra)
"""

# Define resources to gather
resources_to_gather = [
    (Resource.Stone, 12),
    (Resource.Coal, 3),
    (Resource.IronOre, 36)  # Increased to ensure we have enough for iron plates
]

# Loop over each resource type and quantity
for resource_type, quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    
    # Move to the resource patch
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, quantity)
    
    # Check that we've harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= quantity, f"Failed to gather enough {resource_type}. Expected {quantity}, but got {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Verify final inventory contains all required items
final_inventory = inspect_inventory()
for resource_type, required_quantity in resources_to_gather:
    actual_quantity = final_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Final inventory check failed for {resource_type}. Expected at least {required_quantity}, but got {actual_quantity}"

print("Successfully gathered all required resources:")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")

"""
Step 3: Craft stone furnaces. We need to craft:
- stone-furnace: 2
"""

# Craft stone furnaces
crafted_stone_furnaces = craft_item(Prototype.StoneFurnace, 2)
assert crafted_stone_furnaces >= 2, f"Failed to craft 2 stone furnaces. Only crafted {crafted_stone_furnaces}"

print("Successfully crafted 2 stone furnaces")

"""
Step 4: Set up smelting operation. We need to:
- Place a stone furnace
- Add coal as fuel
- Smelt iron ore into iron plates (12 iron plates needed)
"""

# Place a stone furnace
current_position = inspect_entities().player_position
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=current_position[0], y=current_position[1]+2))
assert furnace is not None, "Failed to place stone furnace"

# Add coal as fuel
coal_in_inventory = inspect_inventory()[Prototype.Coal]
first_furnace = insert_item(Prototype.Coal, furnace, quantity=coal_in_inventory)
assert first_furnace.fuel.get(Prototype.Coal, 0) > 0, "Failed to add coal to stone furnace"

# Smelt iron ore into iron plates
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
first_furnace = insert_item(Prototype.IronOre, first_furnace, quantity=iron_ore_in_inventory)
sleep(10)  # Wait for smelting process

# Extract iron plates
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, first_furnace.position, quantity=iron_ore_in_inventory)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= 12:
        break
    sleep(5)

assert current_iron_plate_count >= 12, f"Failed to smelt required number of iron plates. Expected at least 12 but got {current_iron_plate_count}"
print(f"Successfully obtained {current_iron_plate_count} iron plates")

"""
Step 5: Craft iron gear wheels. We need to craft:
- iron-gear-wheel: 6
"""

# Craft iron gear wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, 6)
assert crafted_gear_wheels >= 6, f"Failed to craft 6 iron gear wheels. Only crafted {crafted_gear_wheels}"

print("Successfully crafted 6 iron gear wheels")

"""
Step 6: Craft burner-mining-drill. We need to craft:
- burner-mining-drill: 1
"""

# Craft burner mining drill
crafted_drill = craft_item(Prototype.BurnerMiningDrill, 1)
assert crafted_drill >= 1, f"Failed to craft 1 burner mining drill. Only crafted {crafted_drill}"

print("Successfully crafted 1 burner mining drill")

# Verify that we have the burner mining drill in our inventory
final_inventory = inspect_inventory()
burner_mining_drills = final_inventory.get(Prototype.BurnerMiningDrill, 0)
assert burner_mining_drills >= 1, f"Error: Expected to have at least 1 burner mining drill in inventory, but found {burner_mining_drills}"

print(f"Successfully completed objective! Final inventory: {final_inventory}")

