

from factorio_instance import *

"""
Planning:

To craft a burner mining drill, we need:
- 3 iron gear wheels
- 3 iron plates
- 1 stone furnace

There are no entities on the map or in our inventory, so we need to craft everything from scratch.
We'll also need some intermediate items and resources for crafting.
"""

"""
Step 1: Print recipe. We need to print the recipe for burner mining drill
"""
# Get the recipe for burner mining drill
recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)

# Print the recipe details
print("Recipe for Burner Mining Drill:")
print(f"Ingredients:")
for ingredient in recipe.ingredients:
    print(f"- {ingredient.count} {ingredient.name}")

"""
Step 2: Gather raw resources
- Mine at least 25 iron ore
- Mine at least 10 stone
- Mine at least 10 coal
"""
resources_to_gather = [
    (Resource.IronOre, 25),
    (Resource.Stone, 10),
    (Resource.Coal, 10)
]

for resource_type, required_quantity in resources_to_gather:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    
    # Verify that we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

print("Final inventory after gathering:")
print(inspect_inventory())

"""
Step 3: Craft stone furnaces
- Craft 2 stone furnaces (one for smelting, one for the drill recipe)
"""
craft_item(Prototype.StoneFurnace, quantity=2)
print("Crafted 2 Stone Furnaces")

# Verify that we have 2 stone furnaces
stone_furnaces = inspect_inventory().get(Prototype.StoneFurnace, 0)
assert stone_furnaces >= 2, f"Failed to craft enough Stone Furnaces. Expected at least 2 but got {stone_furnaces}"

"""
Step 4: Set up smelting
- Place a stone furnace
- Fuel it with coal
- Insert 25 iron ore to smelt 25 iron plates
"""
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print("Placed a Stone Furnace")

# Add coal as fuel
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
assert coal_in_inventory >= 5, f"Not enough coal in inventory to fuel the furnace. Expected at least 5 but got {coal_in_inventory}"
fueled_furnace = insert_item(Prototype.Coal, furnace, quantity=5)
print("Inserted 5 units of coal into the Stone Furnace")

# Insert iron ore
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
assert iron_ore_in_inventory >= 25, f"Not enough iron ore in inventory to smelt. Expected at least 25 but got {iron_ore_in_inventory}"
updated_furnace = insert_item(Prototype.IronOre, fueled_furnace, quantity=25)
print("Inserted 25 units of Iron Ore into the Stone Furnace")

sleep(30)

# Extract iron plates
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=25)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= 25:
        break
    sleep(5)

print(f"Extracted Iron Plates; Current Inventory Count: {current_iron_plate_count}")
assert current_iron_plate_count >= 25, f"Failed to obtain required number of Iron Plates! Expected: 25, Got: {current_iron_plate_count}"

"""
Step 5: Craft intermediate items
- Craft 4 iron gear wheels
"""
craft_item(Prototype.IronGearWheel, quantity=4)
print("Crafted 4 Iron Gear Wheels")

# Verify that we have 4 iron gear wheels
iron_gear_wheels = inspect_inventory().get(Prototype.IronGearWheel, 0)
assert iron_gear_wheels >= 4, f"Failed to craft enough Iron Gear Wheels. Expected at least 4 but got {iron_gear_wheels}"

"""
Step 6: Craft burner mining drill
- Use 3 iron gear wheels, 3 iron plates, and 1 stone furnace to craft the burner mining drill
"""
craft_item(Prototype.BurnerMiningDrill, quantity=1)
print("Crafted 1 Burner Mining Drill")

# Verify that we have 1 burner mining drill
burner_mining_drills = inspect_inventory().get(Prototype.BurnerMiningDrill, 0)
assert burner_mining_drills >= 1, f"Failed to craft Burner Mining Drill. Expected at least 1 but got {burner_mining_drills}"

"""
Step 7: Craft transport belts and underground belts
- Craft 14 transport belts
- Craft 4 underground belts
"""
# Craft transport belts
craft_item(Prototype.TransportBelt, quantity=14)
print("Crafted 14 Transport Belts")

# Verify that we have 14 transport belts
transport_belts = inspect_inventory().get(Prototype.TransportBelt, 0)
assert transport_belts >= 14, f"Failed to craft enough Transport Belts. Expected at least 14 but got {transport_belts}"

# Craft underground belts
craft_item(Prototype.UndergroundBelt, quantity=4)
print("Crafted 4 Underground Belts")

# Verify that we have 4 underground belts
underground_belts = inspect_inventory().get(Prototype.UndergroundBelt, 0)
assert underground_belts >= 4, f"Failed to craft enough Underground Belts. Expected at least 4 but got {underground_belts}"

print("Successfully crafted and verified all required items!")

