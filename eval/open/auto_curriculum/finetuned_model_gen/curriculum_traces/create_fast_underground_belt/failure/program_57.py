

from instance import *

"""
Step 1: Print recipe for fast-underground-belt
"""
# Get the recipe for fast-underground-belt
recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)

# Print the recipe details
print("fast-underground-belt Recipe:")
print(f"Ingredients: {recipe.ingredients}")

"""
Step 2: Print recipes for intermediate items
"""
# Get and print recipe for iron-gear-wheel
gear_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print("\nIron Gear Wheel Recipe:")
print(f"Ingredients: {gear_recipe.ingredients}")

# Get and print recipe for underground-belt
belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print("\nUnderground Belt Recipe:")
print(f"Ingredients: {belt_recipe.ingredients}")

"""
Step 3: Gather raw resources
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 50),  # 40 for iron plates, 10 extra for safety
    (Resource.Coal, 10)     # For fueling the furnace
]

# Loop through each resource and gather it
for resource_type, required_quantity in resources_to_gather:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    harvested = harvest_resource(resource_position, required_quantity)
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Print final inventory after gathering
final_inventory = inspect_inventory()
print("Final inventory after gathering:")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")

"""
Step 4: Smelt iron plates
"""
# Move to origin to place the furnace
origin = Position(x=0, y=0)
move_to(origin)

# Craft and place the stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
furnace = place_entity(Prototype.StoneFurnace, position=origin)

# Insert coal as fuel into the furnace
coal_in_inventory = inspect_inventory()[Prototype.Coal]
insert_item(Prototype.Coal, furnace, quantity=coal_in_inventory)

# Insert iron ore into the furnace to produce iron plates
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
insert_item(Prototype.IronOre, furnace, quantity=iron_ore_in_inventory)

# Wait for smelting to complete
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_in_inventory)
sleep(total_smelting_time)

# Extract iron plates from the furnace
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, furnace.position, quantity=iron_ore_in_inventory)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= iron_ore_in_inventory:
        break
    sleep(10)

print(f"Extracted Iron Plates; Current Inventory Count: {current_iron_plate_count}")

# Verify that we have enough iron plates
assert current_iron_plate_count >= 40, f"Failed to smelt enough Iron Plates; Expected at least 40 but got {current_iron_plate_count}"

"""
Step 5: Craft intermediate items
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=40)

# Craft underground belts
craft_item(Prototype.UndergroundBelt, quantity=2)

"""
Step 6: Craft fast-underground-belt
"""
# Craft the fast-underground-belt
craft_item(Prototype.FastUndergroundBelt, quantity=1)

# Verify that we have crafted the fast-underground-belt
final_inventory = inspect_inventory()
assert final_inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, "Failed to craft fast-underground-belt"

print("Successfully crafted a fast-underground-belt!")

