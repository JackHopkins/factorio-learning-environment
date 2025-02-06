

from instance import *

"""
Objective: Create a burner mining drill from scratch

Planning:
We need to create a burner mining drill from scratch. There are no entities on the map, so we need to gather all the resources ourselves.
We need to craft a stone furnace and then use it to smelt iron plates. Finally, we can craft the burner mining drill.
The final success will be checked by looking if we have a burner mining drill in inventory
"""

"""
Step 1: Print recipes
"""
print("Recipes for the task:")
print("Burner Mining Drill recipe: 3 iron gear wheels, 1 stone furnace, 3 iron plates")
print("Stone Furnace recipe: 5 stone")

"""
Step 2: Gather raw resources
- Mine stone for the furnace
- Mine iron ore for plates and gear wheels
- Mine coal for fueling the furnace
"""
# Define resources to gather
resources_to_gather = [
    (Resource.Stone, 6),  # 5 for furnace, 1 extra for safety
    (Resource.IronOre, 7),  # 3 for plates, 4 for gear wheels
    (Resource.Coal, 1)  # 1 for fueling the furnace
]

# Gather each resource
for resource_type, required_quantity in resources_to_gather:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    inventory = inspect_inventory()
    
    # Verify we harvested enough
    assert inventory.get(resource_type) >= required_quantity, f"Failed to gather enough {resource_type}"

print("Successfully gathered all raw resources")

"""
Step 3: Craft the Stone Furnace
"""
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 Stone Furnace")

"""
Step 4: Set up smelting operation
"""
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
move_to(furnace.position)

# Insert coal into the furnace as fuel
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
assert coal_in_inventory >= 1, "Not enough coal in inventory"
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=1)
print("Inserted coal into the furnace")

"""
Step 5: Smelt iron plates
"""
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
assert iron_ore_in_inventory >= 7, "Not enough iron ore in inventory"
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=7)
print("Inserted iron ore into the furnace")

# Wait for smelting to complete
smelting_time = 7 * 0.6  # 0.6 seconds per iron plate
sleep(smelting_time)

# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=7)
    current_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plates >= 7:
        break
    sleep(1)

assert current_iron_plates >= 7, "Failed to smelt enough Iron Plates"
print(f"Smelted {current_iron_plates} Iron Plates")

"""
Step 6: Craft intermediate items
"""
craft_item(Prototype.IronGearWheel, quantity=3)
print("Crafted 3 Iron Gear Wheels")

"""
Step 7: Craft the Burner Mining Drill
"""
craft_item(Prototype.BurnerMiningDrill, quantity=1)
print("Crafted 1 Burner Mining Drill")

"""
Step 8: Verify success
"""
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.BurnerMiningDrill, 0) >= 1, "Failed to craft the Burner Mining Drill"
print("Successfully crafted the Burner Mining Drill")

