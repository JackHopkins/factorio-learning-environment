
from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipes for fast-underground-belt, underground-belt and iron-gear-wheel
"""
# Get the recipe for fast-underground-belt
fast_underground_belt_recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)

# Print the recipe details
print("FastUndergroundBelt Recipe:")
print(f"Ingredients: {fast_underground_belt_recipe.ingredients}")

# Get the recipe for underground-belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)

# Print the recipe details
print("UndergroundBelt Recipe:")
print(f"Ingredients: {underground_belt_recipe.ingredients}")

# Get the recipe for iron-gear-wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)

# Print the recipe details
print("IronGearWheel Recipe:")
print(f"Ingredients: {iron_gear_wheel_recipe.ingredients}")

print("All recipes printed successfully")


"""
Step 2: Gather raw resources. We need to mine:
- Coal (at least 7 for fuel)
- Stone (at least 6 for one stone furnace)
- Iron ore (at least 98 for iron plates)
"""
# Define required quantities
required_coal = 7
required_stone = 6
required_iron_ore = 98

# Get positions of resource patches
coal_position = nearest(Resource.Coal)
stone_position = nearest(Resource.Stone)
iron_ore_position = nearest(Resource.IronOre)

# Move to and harvest coal
move_to(coal_position)
coal_harvested = harvest_resource(coal_position, required_coal)
print(f"Harvested {coal_harvested} coal")

# Move to and harvest stone
move_to(stone_position)
stone_harvested = harvest_resource(stone_position, required_stone)
print(f"Harvested {stone_harvested} stone")

# Move to and harvest iron ore
move_to(iron_ore_position)
iron_ore_harvested = harvest_resource(iron_ore_position, required_iron_ore)
print(f"Harvested {iron_ore_harvested} iron ore")

# Verify quantities in inventory
inventory = inspect_inventory()
assert inventory.get(Prototype.Coal, 0) >= required_coal, f"Failed to gather enough coal. Expected {required_coal}, got {inventory.get(Prototype.Coal, 0)}"
assert inventory.get(Prototype.Stone, 0) >= required_stone, f"Failed to gather enough stone. Expected {required_stone}, got {inventory.get(Prototype.Stone, 0)}"
assert inventory.get(Prototype.IronOre, 0) >= required_iron_ore, f"Failed to gather enough iron ore. Expected {required_iron_ore}, got {inventory.get(Prototype.IronOre, 0)}"

print("Successfully gathered all required resources")
print(f"Current inventory: {inventory}")


"""
Step 3: Craft and set up basic smelting operation
- Craft 1 stone furnace
- Place the furnace
- Fuel the furnace with coal
"""
# Craft a stone furnace
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted {crafted_furnaces} Stone Furnace(s)")

# Verify that we have a stone furnace in our inventory
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace, 0) >= 1, "Failed to craft Stone Furnace"

# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed Stone Furnace at {furnace.position}")

# Insert coal into the furnace as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=7)
coal_in_furnace = updated_furnace.fuel.get(Prototype.Coal, 0)
print(f"Inserted coal into Stone Furnace; Current fuel level: {coal_in_furnace}")

# Verify that the furnace has been fueled
assert coal_in_furnace > 0, "Failed to fuel Stone Furnace"

print("Successfully set up basic smelting operation")


"""
Step 4: Smelt iron plates
- Smelt 98 iron ore into iron plates (this will take some time)
"""
# Insert iron ore into the furnace
updated_furnace = insert_item(Prototype.IronOre, furnace, quantity=98)
print("Inserted Iron Ore into the Stone Furnace")

# Wait for smelting to complete
smelting_time = 98 * 0.7  # Assuming 0.7 seconds per ore
sleep(smelting_time)

# Attempt to extract iron plates multiple times
max_attempts = 5
for attempt in range(max_attempts):
    # Extract the iron plates
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=98)
    
    # Check current inventory for iron plates
    inventory = inspect_inventory()
    current_iron_plates = inventory.get(Prototype.IronPlate, 0)
    
    # If sufficient plates are gathered, break out of loop
    if current_iron_plates >= 98:
        break
    
    # Wait before trying again
    sleep(10)

print(f"Extracted Iron Plates; Current Inventory: {current_iron_plates}")

# Verify that we have enough iron plates
assert current_iron_plates >= 98, f"Failed to obtain required number of Iron Plates! Expected at least 98 but got {current_iron_plates}"

print("Successfully smelted all required Iron Plates")


"""
Step 5: Craft intermediate products
- Craft 40 iron gear wheels (requires 80 iron plates)
- Craft 1 underground belt (requires 10 iron gear wheels and 10 iron plates)
"""
# Craft Iron Gear Wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=40)
print(f"Crafted {crafted_gear_wheels} Iron Gear Wheel(s)")

# Verify that we have crafted the correct number of Iron Gear Wheels
inventory = inspect_inventory()
assert inventory.get(Prototype.IronGearWheel, 0) >= 40, f"Failed to craft enough Iron Gear Wheels. Expected at least 40 but got {inventory.get(Prototype.IronGearWheel, 0)}"

# Craft Underground Belt
crafted_underground_belt = craft_item(Prototype.UndergroundBelt, quantity=1)
print(f"Crafted {crafted_underground_belt} Underground Belt(s)")

# Verify that we have crafted an Underground Belt
inventory = inspect_inventory()
assert inventory.get(Prototype.UndergroundBelt, 0) >= 1, f"Failed to craft an Underground Belt. Expected at least 1 but got {inventory.get(Prototype.UndergroundBelt, 0)}"

print("Successfully crafted all intermediate products")


"""
Step 6: Craft fast-underground-belt
- Craft 1 fast-underground-belt (requires 20 iron gear wheels and 1 underground belt)
"""
# Craft Fast Underground Belt
crafted_fast_underground_belt = craft_item(Prototype.FastUndergroundBelt, quantity=1)
print(f"Crafted {crafted_fast_underground_belt} Fast Underground Belt(s)")

# Verify that we have crafted a Fast Underground Belt
inventory = inspect_inventory()
assert inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, f"Failed to craft a Fast Underground Belt. Expected at least 1 but got {inventory.get(Prototype.FastUndergroundBelt, 0)}"

print("Successfully crafted the Fast Underground Belt")

# Final inventory check
final_inventory = inspect_inventory()
print("Final Inventory:")
print(f"Fast Underground Belts: {final_inventory.get(Prototype.FastUndergroundBelt, 0)}")

print("Objective completed successfully!")
