

from instance import *

"""
Objective: Set up initial iron plate production

Planning:
1. Print recipes for stone furnace and iron plate
2. Gather raw resources (stone, coal, iron ore)
3. Craft a stone furnace
4. Place the furnace and add fuel
5. Smelt iron ore into iron plates
6. Verify iron plate production
"""

"""
Step 1: Print recipes
"""
print("Recipes:")
print("Stone Furnace: 5 stone")
print("Iron Plate: Smelt 1 iron ore for 1 iron plate")

"""
Step 2: Gather raw resources
- Mine 5 stone for furnace
- Mine at least 5 coal for fuel
- Mine at least 10 iron ore
"""
resources_to_gather = [
    (Resource.Stone, 5),
    (Resource.Coal, 5),
    (Resource.IronOre, 10)
]

for resource, amount in resources_to_gather:
    resource_position = nearest(resource)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, amount)
    current_inventory = inspect_inventory()
    assert current_inventory.get(resource) >= amount, f"Failed to gather enough {resource}. Required: {amount}, Found: {current_inventory.get(resource)}"
    print(f"Successfully gathered {harvested} {resource}")

"""
Step 3: Craft a stone furnace
"""
print("Crafting a stone furnace...")
craft_item(Prototype.StoneFurnace, 1)
print("Stone furnace crafted.")

"""
Step 4: Place the furnace and add fuel
"""
# Move to a suitable position
move_to(Position(x=0, y=0))  # Adjust this position if needed

# Place the stone furnace
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
print(f"Stone furnace placed at {furnace.position}")

# Insert coal as fuel
coal_in_inventory = inspect_inventory()[Prototype.Coal]
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=coal_in_inventory)
print(f"Inserted {coal_in_inventory} coal into the stone furnace")

"""
Step 5: Smelt iron ore into iron plates
"""
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} iron ore into the stone furnace")

# Wait for smelting to complete
smelting_time = 0.7 * iron_ore_in_inventory  # 0.7 seconds per iron ore
sleep(smelting_time)

# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    current_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plates >= 10:
        break
    sleep(5)

print(f"Extracted iron plates. Current inventory: {inspect_inventory()}")

"""
Step 6: Verify iron plate production
"""
final_inventory = inspect_inventory()
iron_plates = final_inventory.get(Prototype.IronPlate, 0)
assert iron_plates >= 10, f"Failed to produce enough iron plates. Required: 10, Found: {iron_plates}"
print(f"Successfully produced {iron_plates} iron plates. Objective completed!")

