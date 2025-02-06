
from instance import *

"""
Step 1: Print recipes. We need to print the recipe for fast-underground-belt
"""
# Print recipe for fast-underground-belt
recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
print("fast-underground-belt recipe:")
print(f"Ingredients: {recipe.ingredients}")

"""
Step 2: Gather raw resources. We need to gather at least 40 iron ore and 5 stone
"""
# Define required resources
required_resources = [
    (Resource.IronOre, 40),
    (Resource.Stone, 5)
]

# Gather required resources
for resource_type, required_amount in required_resources:
    resource_position = nearest(resource_type)
    move_to(resource_position)
    gathered = harvest_resource(resource_position, required_amount)
    current_inventory = inspect_inventory()
    
    # Verify that the required amount has been gathered
    assert current_inventory.get(resource_type, 0) >= required_amount, \
        f"Failed to gather enough {resource_type}. Required: {required_amount}, Gathered: {current_inventory.get(resource_type, 0)}"
    
    print(f"Successfully gathered {current_inventory.get(resource_type, 0)} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

# Assert that all required resources are present in the inventory
assert final_inventory.get(Resource.IronOre, 0) >= 40, "Not enough Iron Ore"
assert final_inventory.get(Resource.Stone, 0) >= 5, "Not enough Stone"

print("Successfully gathered all required resources")

"""
Step 3: Craft and set up a basic smelting operation
- Craft a stone furnace
- Place the furnace
- Smelt iron ore into iron plates
"""
# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 Stone Furnace")

# Place stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed Stone Furnace at {furnace.position}")

# Insert iron ore into the furnace
iron_ore_in_inventory = inspect_inventory()[Resource.IronOre]
insert_item(Resource.IronOre, furnace, iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} Iron Ore into the Furnace")

# Insert coal to fuel the furnace
coal_in_inventory = inspect_inventory()[Prototype.Coal]
insert_item(Prototype.Coal, furnace, coal_in_inventory)
print(f"Inserted {coal_in_inventory} Coal into the Furnace")

# Wait for smelting to complete
sleep(iron_ore_in_inventory * 0.7)
print("Smelting complete")

# Extract iron plates
expected_iron_plates = iron_ore_in_inventory
for _ in range(5):  # Try up to 5 times to extract all plates
    extract_item(Prototype.IronPlate, furnace.position, expected_iron_plates)
    current_iron_plates = inspect_inventory()[Prototype.IronPlate]
    
    if current_iron_plates >= expected_iron_plates:
        break
    sleep(10)

print(f"Extracted Iron Plates; Current Inventory Count: {current_iron_plates}")

# Assert that enough iron plates have been produced
assert current_iron_plates >= expected_iron_plates, \
    f"Failed to produce enough Iron Plates. Expected: {expected_iron_plates}, Actual: {current_iron_plates}"

print("Successfully completed step 3")

"""
Step 4: Craft iron gear wheels. We need to craft 40 iron gear wheels
"""
# Print the recipe for iron gear wheel
recipe = get_prototype_recipe(Prototype.IronGearWheel)
print("Iron Gear Wheel Recipe:")
print(f"Ingredients: {recipe.ingredients}")

# Calculate required iron plates
required_iron_plates = 40 * 2  # 2 iron plates per gear wheel

# Verify that we have enough iron plates
current_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
assert current_iron_plates >= required_iron_plates, \
    f"Insufficient Iron Plates! Required: {required_iron_plates}, but only {current_iron_plates} available."

# Craft Iron Gear Wheels
craft_item(Prototype.IronGearWheel, quantity=40)
print(f"Crafted 40 Iron Gear Wheels")

# Verify that the iron gear wheels were crafted successfully
iron_gear_wheels_in_inventory = inspect_inventory().get(Prototype.IronGearWheel, 0)
assert iron_gear_wheels_in_inventory >= 40, \
    f"Failed to craft enough Iron Gear Wheels! Expected: 40, but got {iron_gear_wheels_in_inventory}"

print("Successfully crafted 40 Iron Gear Wheels")

"""
Step 5: Craft underground belts. We need to craft 2 underground belts
"""
# Print the recipe for underground belt
recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print("Underground Belt Recipe:")
print(f"Ingredients: {recipe.ingredients}")

# Calculate required iron plates and gear wheels
required_iron_plates = 2 * 5  # 5 iron plates per underground belt
required_gear_wheels = 2 * 5  # 5 iron gear wheels per underground belt

# Verify that we have enough resources
current_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
current_gear_wheels = inspect_inventory().get(Prototype.IronGearWheel, 0)

assert current_iron_plates >= required_iron_plates, \
    f"Insufficient Iron Plates! Required: {required_iron_plates}, but only {current_iron_plates} available."
assert current_gear_wheels >= required_gear_wheels, \
    f"Insufficient Iron Gear Wheels! Required: {required_gear_wheels}, but only {current_gear_wheels} available."

# Craft Underground Belts
craft_item(Prototype.UndergroundBelt, quantity=2)
print(f"Crafted 2 Underground Belts")

# Verify that the underground belts were crafted successfully
underground_belts_in_inventory = inspect_inventory().get(Prototype.UndergroundBelt, 0)
assert underground_belts_in_inventory >= 2, \
    f"Failed to craft enough Underground Belts! Expected: 2, but got {underground_belts_in_inventory}"

print("Successfully crafted 2 Underground Belts")

"""
Step 6: Craft fast-underground-belt
"""
# Print the recipe for fast underground belt
recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)
print("Fast Underground Belt Recipe:")
print(f"Ingredients: {recipe.ingredients}")

# Verify that we have enough underground belts
current_underground_belts = inspect_inventory().get(Prototype.UndergroundBelt, 0)
assert current_underground_belts >= 2, \
    f"Insufficient Underground Belts! Required: 2, but only {current_underground_belts} available."

# Craft Fast Underground Belt
craft_item(Prototype.FastUndergroundBelt, quantity=1)
print(f"Crafted 1 Fast Underground Belt")

# Verify that the fast underground belt was crafted successfully
fast_underground_belt_in_inventory = inspect_inventory().get(Prototype.FastUndergroundBelt, 0)
assert fast_underground_belt_in_inventory >= 1, \
    f"Failed to craft Fast Underground Belt! Expected: 1, but got {fast_underground_belt_in_inventory}"

print("Successfully crafted 1 Fast Underground Belt")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

print("Successfully completed all steps and crafted a Fast Underground Belt")

