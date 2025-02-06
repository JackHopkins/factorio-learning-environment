

from instance import *

"""
Objective: Craft a burner-mining-drill from raw resources

Planning:
We need to craft a burner-mining-drill, which requires:
- 3 iron gear wheels
- 1 stone furnace
- 4 iron plates

There are no entities on the map or in our inventory, so we need to craft everything from scratch.
We'll need to gather raw resources, smelt iron plates, and then craft the necessary components.

Steps:
1. Print recipes
2. Gather raw resources
3. Craft stone furnace
4. Smelt iron plates
5. Craft iron gear wheels
6. Craft stone furnace
7. Craft burner-mining-drill
8. Verify crafting
"""

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

"""
Step 2: Gather raw resources
- Mine 25 iron ore
- Mine 12 stone (for 2 stone furnaces)
- Mine 2 coal (for fueling the furnace)
"""
resources_to_gather = [
    (Resource.IronOre, 25),
    (Resource.Stone, 12),
    (Resource.Coal, 2)
]

for resource_type, required_quantity in resources_to_gather:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

final_inventory = inspect_inventory()
print("Final inventory after gathering resources:")
print(final_inventory)

# Verify that we have gathered all resources
for resource_type, required_quantity in resources_to_gather:
    assert final_inventory.get(resource_type, 0) >= required_quantity, f"Missing required {resource_type} in inventory"

print("Successfully gathered all required resources")

"""
Step 3: Craft stone furnace
"""
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 Stone Furnace")

"""
Step 4: Smelt iron plates
"""
# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)

# Add coal to the furnace as fuel
coal_in_inventory = inspect_inventory()[Prototype.Coal]
insert_item(Prototype.Coal, furnace, quantity=coal_in_inventory)
print(f"Inserted {coal_in_inventory} coal into the furnace")

# Add iron ore to the furnace
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
insert_item(Prototype.IronOre, furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} iron ore into the furnace")

# Wait for smelting to complete
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_in_inventory)
sleep(total_smelting_time)

# Extract iron plates
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, furnace.position, quantity=iron_ore_in_inventory)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= iron_ore_in_inventory:
        break
    sleep(10)

print(f"Extracted {current_iron_plate_count} Iron Plates")

# Verify that we have enough iron plates
required_iron_plates = 25
assert current_iron_plate_count >= required_iron_plates, f"Failed to smelt enough Iron Plates. Required: {required_iron_plates}, Actual: {current_iron_plate_count}"
print(f"Successfully smelted {current_iron_plate_count} Iron Plates")

"""
Step 5: Craft iron gear wheels
"""
craft_item(Prototype.IronGearWheel, quantity=4)
print("Crafted 4 Iron Gear Wheels")

"""
Step 6: Craft stone furnace
"""
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 Stone Furnace")

"""
Step 7: Craft burner-mining-drill
"""
craft_item(Prototype.BurnerMiningDrill, quantity=1)
print("Crafted 1 Burner-Mining-Drill")

"""
Step 8: Verify crafting
"""
final_inventory = inspect_inventory()
burner_mining_drills = final_inventory.get(Prototype.BurnerMiningDrill, 0)
assert burner_mining_drills >= 1, f"Failed to craft Burner-Mining-Drill. Expected at least 1, but found {burner_mining_drills}"
print(f"Successfully crafted {burner_mining_drills} Burner-Mining-Drill(s)")

print("All steps completed successfully!")

