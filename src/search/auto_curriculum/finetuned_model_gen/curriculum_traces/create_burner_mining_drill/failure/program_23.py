

from factorio_instance import *

"""
Planning:
We need to create a burner mining drill from scratch. 
There are no entities on the map and our inventory is empty.
We need to craft the following items:
- 1 burner mining drill (requires 3 iron gear wheels and 1 stone furnace)
- 1 stone furnace (requires 5 stone)
- 7 iron gear wheels (requires 14 iron plates)
- 9 iron plates (for gear wheels and drill)

We'll need to mine the following resources:
- 5 stone (for furnace)
- 9 iron ore (for plates and gear wheels)
- 2 coal (for fuel)

Steps:
1. Print out recipes
2. Mine resources (stone, iron ore, coal)
3. Craft stone furnace
4. Place furnace and smelt iron plates
5. Craft iron gear wheels
6. Craft burner mining drill
"""

# Step 1: Print out recipes
print("Recipes:")
print("Burner Mining Drill: 3 iron gear wheels, 1 stone furnace")
print("Stone Furnace: 5 stone")
print("Iron Gear Wheel: 2 iron plates each")

# Step 2: Mine resources
resources_to_mine = [
    (Resource.Stone, 5),
    (Resource.IronOre, 18),  # 14 for gear wheels, 9 for plates
    (Resource.Coal, 2)
]

for resource_type, quantity in resources_to_mine:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, quantity=quantity)
    current_inventory = inspect_inventory()
    assert current_inventory.get(resource_type, 0) >= quantity, f"Failed to gather enough {resource_type}. Required: {quantity}, Current: {current_inventory.get(resource_type, 0)}"
    print(f"Successfully gathered {harvested} {resource_type}")

# Step 3: Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 Stone Furnace")

# Step 4: Place furnace and smelt iron plates
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
move_to(furnace.position)

# Insert coal into furnace as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=2)

# Insert iron ore into the furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)

# Wait for smelting to complete
smelting_time = 0.7 * iron_ore_in_inventory
sleep(smelting_time)

# Extract iron plates
for _ in range(5):  # Attempt to extract multiple times if needed
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= 9:
        break
    sleep(2)

print(f"Extracted Iron Plates. Current Inventory: {inspect_inventory()}")

# Step 5: Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=7)
print("Crafted 7 Iron Gear Wheels")

# Step 6: Craft burner mining drill
craft_item(Prototype.BurnerMiningDrill, quantity=1)
print("Crafted 1 Burner Mining Drill")

final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.BurnerMiningDrill, 0) >= 1, "Burner Mining Drill crafting failed"
print(f"Successfully crafted Burner Mining Drill. Current Inventory: {final_inventory}")

