
from instance import *

"""
Step 1: Print recipes. We need to print the recipes for fast-underground-belt and underground-belt. This will help us understand what intermediate products we need to craft.
"""
# Print recipes for fast-underground-belt and underground-belt
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)

print("FastUndergroundBelt Recipe:")
print(fast_underground_belt_recipe)

print("\nUndergroundBelt Recipe:")
print(underground_belt_recipe)

"""
Step 2: Gather resources. We need to mine the following resources:
- Coal: 7
- Stone: 6
- Iron ore: 98
"""
# Define resources to gather
resources_to_gather = [
    (Resource.Coal, 7),
    (Resource.Stone, 6),
    (Resource.IronOre, 98)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find nearest position of current resource type
    resource_position = nearest(resource_type)
    
    # Move towards the found position
    move_to(resource_position)
    
    # Harvesting specified amount of current resource type
    harvested_amount = harvest_resource(resource_position, required_quantity)
    
    # Logging harvested amount for debugging purposes
    print(f"Harvested {harvested_amount} of {resource_type}")
    
    # Asserting if we have harvested at least as much as required or more
    assert inspect_inventory()[resource_type] >= required_quantity, f"Failed to gather enough {resource_type}"

# Final log statement showing contents of player inventory after gathering all specified resources
print("Final player inventory after gathering all specified resources:")
print(inspect_inventory())

# Verify if all gathered quantities meet expectations
final_inventory = inspect_inventory()
assert final_inventory[Resource.Coal] >= 7, "Not enough coal gathered!"
assert final_inventory[Resource.Stone] >= 6, "Not enough stone gathered!"
assert final_inventory[Resource.IronOre] >= 98, "Not enough iron ore gathered!"

print("Successfully gathered all required resources.")

"""
Step 3: Craft stone furnace. We need to craft 1 stone furnace using 5 stone.
"""
# Check current inventory
current_inventory = inspect_inventory()

# Verify if we have enough stone
assert current_inventory[Resource.Stone] >= 5, f"Not enough stone! Required: 5, Available: {current_inventory[Resource.Stone]}"

# Craft stone furnace
crafted_furnaces = craft_item(Prototype.StoneFurnace, 1)

print(f"Crafted {crafted_furnaces} Stone Furnace(s)")

# Update inventory after crafting
updated_inventory = inspect_inventory()
furnaces_in_inventory = updated_inventory.get(Prototype.StoneFurnace, 0)

# Verify if crafting was successful
assert furnaces_in_inventory >= 1, f"Failed to craft Stone Furnace! Expected at least 1 but got {furnaces_in_inventory}"

print("Successfully crafted a Stone Furnace.")

"""
Step 4: Smelt iron plates. We need to smelt 98 iron ore into 98 iron plates. 
- Place the stone furnace and add coal as fuel
- Smelt the iron ore in batches if necessary
"""
# Check initial inventory for required items
initial_inventory = inspect_inventory()
print("Initial inventory:", initial_inventory)

# Verify we have enough materials before proceeding
assert initial_inventory[Resource.Coal] >= 7, f"Not enough coal! Required: 7, Available: {initial_inventory[Resource.Coal]}"
assert initial_inventory[Resource.IronOre] >= 98, f"Not enough iron ore! Required: 98, Available: {initial_inventory[Resource.IronOre]}"
assert initial_inventory[Prototype.StoneFurnace] >= 1, f"No stone furnace available!"

# Place stone furnace at current position
current_position = inspect_entities().player_position
move_to(Position(x=current_position[0], y=current_position[1]))
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=current_position[0], y=current_position[1]+2))
print(f"Placed stone furnace at {furnace.position}")

# Insert all available coal into the furnace as fuel
coal_to_insert = min(initial_inventory[Resource.Coal], 7)
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=coal_to_insert)
print(f"Inserted {coal_to_insert} units of coal into the stone furnace")

# Determine how many full batches we'll need to smelt and any remainder
total_batches = 98 // 20
remainder = 98 % 20

# Smelt in full batches
for _ in range(total_batches):
    updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=20)
    sleep(10)  # Allow time for smelting
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=20)

# Smelt any remaining ore
if remainder > 0:
    updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=remainder)
    sleep(5)  # Allow time for smelting
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=remainder)

# Verify final inventory
final_inventory = inspect_inventory()
print("Final inventory after smelting:", final_inventory)
assert final_inventory[Prototype.IronPlate] >= 98, f"Failed to produce enough iron plates! Expected: 98, Actual: {final_inventory[Prototype.IronPlate]}"

print("Successfully completed the smelting process and produced required amount of iron plates.")

"""
Step 5: Craft intermediate products. We need to craft the following items:
- Iron gear wheels: Craft 40 iron gear wheels using 80 iron plates
- Underground belts: Craft 2 underground belts using 20 iron plates and 10 iron gear wheels
"""
# Check initial inventory for required items
initial_inventory = inspect_inventory()
print("Initial inventory:", initial_inventory)

# Verify we have enough iron plates before proceeding
assert initial_inventory[Prototype.IronPlate] >= 80, f"Not enough iron plates! Required: 80, Available: {initial_inventory[Prototype.IronPlate]}"

# Crafting Iron Gear Wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=40)
print(f"Crafted {crafted_gear_wheels} Iron Gear Wheel(s)")

# Update inventory after crafting gear wheels
updated_inventory = inspect_inventory()
gear_wheels_in_inventory = updated_inventory.get(Prototype.IronGearWheel, 0)
print("Inventory after crafting Iron Gear Wheels:", updated_inventory)

# Verify if crafting was successful for gear wheels
assert gear_wheels_in_inventory >= 40, f"Failed to craft enough Iron Gear Wheels! Expected at least 40 but got {gear_wheels_in_inventory}"

# Verify we have enough materials before crafting underground belts
assert updated_inventory[Prototype.IronPlate] >= 20, f"Not enough iron plates for Underground Belts! Required: 20, Available: {updated_inventory[Prototype.IronPlate]}"
assert updated_inventory[Prototype.IronGearWheel] >= 10, f"Not enough Iron Gear Wheels for Underground Belts! Required: 10, Available: {updated_inventory[Prototype.IronGearWheel]}"

# Crafting Underground Belts
crafted_underground_belts = craft_item(Prototype.UndergroundBelt, quantity=2)
print(f"Crafted {crafted_underground_belts} Underground Belt(s)")

# Update inventory after crafting underground belts
final_inventory = inspect_inventory()
underground_belts_in_inventory = final_inventory.get(Prototype.UndergroundBelt, 0)
print("Final inventory after crafting Underground Belts:", final_inventory)

# Verify if crafting was successful for underground belts
assert underground_belts_in_inventory >= 2, f"Failed to craft enough Underground Belts! Expected at least 2 but got {underground_belts_in_inventory}"

print("Successfully crafted all intermediate products.")

"""
Step 6: Craft fast-underground-belt. Use the crafted underground belts and iron gear wheels to craft 1 fast-underground-belt.
"""
# Check initial inventory for required items
initial_inventory = inspect_inventory()
print("Initial inventory:", initial_inventory)

# Verify we have enough materials before proceeding
assert initial_inventory[Prototype.UndergroundBelt] >= 2, f"Not enough Underground Belts! Required: 2, Available: {initial_inventory[Prototype.UndergroundBelt]}"
assert initial_inventory[Prototype.IronGearWheel] >= 40, f"Not enough Iron Gear Wheels! Required: 40, Available: {initial_inventory[Prototype.IronGearWheel]}"

# Crafting Fast Underground Belt
crafted_fast_underground_belts = craft_item(Prototype.FastUndergroundBelt, quantity=1)
print(f"Crafted {crafted_fast_underground_belts} Fast Underground Belt(s)")

# Update inventory after crafting
final_inventory = inspect_inventory()
fast_underground_belts_in_inventory = final_inventory.get(Prototype.FastUndergroundBelt, 0)
print("Final inventory after crafting Fast Underground Belts:", final_inventory)

# Verify if crafting was successful for fast underground belts
assert fast_underground_belts_in_inventory >= 1, f"Failed to craft enough Fast Underground Belts! Expected at least 1 but got {fast_underground_belts_in_inventory}"

print("Successfully crafted Fast Underground Belt.")

