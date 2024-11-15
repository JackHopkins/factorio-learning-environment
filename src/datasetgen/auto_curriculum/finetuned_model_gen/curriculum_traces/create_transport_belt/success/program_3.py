

from factorio_instance import *

"""
Objective: Craft a transport-belt from scratch

Planning:
We need to craft a transport-belt. Since there are no entities on the map and our inventory is empty, we need to start from scratch.
We need to mine resources, craft intermediate products, and finally craft the transport-belt.
"""

"""
Step 1: Print recipes
We need to print the recipes for the items we need to craft
"""
# Print recipe for stone-furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print("Recipe for stone-furnace:")
print(f"Ingredients: {stone_furnace_recipe.ingredients}")

# Print recipe for transport-belt
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
print("Recipe for transport-belt:")
print(f"Ingredients: {transport_belt_recipe.ingredients}")

# Print recipe for iron-gear-wheel (needed for transport-belt)
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print("Recipe for iron-gear-wheel:")
print(f"Ingredients: {iron_gear_wheel_recipe.ingredients}")

"""
Step 2: Mine resources
We need to mine the following resources:
- 5 stone for the stone furnace
- At least 3 iron ore (for smelting into 3 iron plates)
- At least 1 coal (for fueling the furnace)
"""
# Define the resources we need to mine
resources_to_mine = [
    (Resource.Stone, 5),
    (Resource.IronOre, 3),
    (Resource.Coal, 1)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_mine:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    print(f"Nearest {resource_type} found at: {resource_position}")
    
    # Move to the resource position
    move_to(resource_position)
    print(f"Moved to {resource_type} position: {resource_position}")
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    print(f"Harvested {harvested} {resource_type}")
    
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to harvest enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully harvested {actual_quantity} {resource_type}")

# Print final inventory after mining all resources
final_inventory = inspect_inventory()
print("Final inventory after mining:")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")

# Assert that we have all required quantities in our inventory
assert final_inventory.get(Resource.Stone, 0) >= 5, "Not enough Stone"
assert final_inventory.get(Resource.IronOre, 0) >= 3, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 1, "Not enough Coal"

print("Successfully mined all required resources.")

"""
Step 3: Craft stone furnace
We need to craft 1 stone furnace using 5 stone
"""
print("\nStep 3: Crafting stone furnace")

# Get current inventory to check if we have enough stone
current_inventory = inspect_inventory()
stone_count = current_inventory.get(Resource.Stone, 0)
print(f"Current stone count in inventory: {stone_count}")

# Assert that we have enough stone before crafting
assert stone_count >= 5, f"Not enough Stone to craft a Stone Furnace. Required: 5, Available: {stone_count}"

# Craft the stone furnace
crafted_quantity = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted {crafted_quantity} Stone Furnace(s)")

# Check inventory after crafting to verify success
updated_inventory = inspect_inventory()
stone_furnaces_in_inventory = updated_inventory.get(Prototype.StoneFurnace, 0)
print(f"Stone Furnaces in inventory after crafting: {stone_furnaces_in_inventory}")

# Assert that we've successfully crafted a stone furnace
assert stone_furnaces_in_inventory >= 1, "Failed to craft a Stone Furnace"

"""
Step 4: Set up and use the furnace
- Place the stone-furnace
- Insert coal into the stone-furnace as fuel
- Insert iron ore into the stone-furnace
- Wait for the smelting process to complete
- Extract 3 iron plates from the stone-furnace
"""
print("\nStep 4: Setting up and using the furnace")

# Place the stone furnace at origin
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print("Placed Stone Furnace.")

# Insert coal into the stone-furnace as fuel
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
print(f"Coal available in inventory: {coal_in_inventory}")

assert coal_in_inventory >= 1, "Not enough Coal to fuel the Stone Furnace."

updated_furnace = insert_item(Prototype.Coal, furnace, quantity=1)
print("Inserted Coal into Stone Furnace.")

# Insert iron ore into the stone-furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
print(f"Iron Ore available in inventory: {iron_ore_in_inventory}")

assert iron_ore_in_inventory >= 3, "Not enough Iron Ore to smelt."

updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=3)
print("Inserted Iron Ore into Stone Furnace.")

# Wait for smelting process to complete
smelting_time = 3 * 0.7  # Approximately 0.7 seconds per unit of iron ore
sleep(smelting_time)

# Extract iron plates from the stone-furnace
max_attempts_to_extract = 5
for _ in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=3)
    iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
    if iron_plates_in_inventory >= 3:
        break
    sleep(5)  # Wait a bit more if not all plates are ready

print(f"Iron Plates available in inventory after extraction: {iron_plates_in_inventory}")
assert iron_plates_in_inventory >= 3, "Failed to obtain required number of Iron Plates."

print("Successfully set up and used the Stone Furnace.")

"""
Step 5: Craft iron gear wheels
We need to craft 1 iron gear wheel using 2 iron plates
"""
print("\nStep 5: Crafting iron gear wheels")

# Get current inventory to check if we have enough iron plates
current_inventory = inspect_inventory()
iron_plate_count = current_inventory.get(Prototype.IronPlate, 0)
print(f"Current iron plate count in inventory: {iron_plate_count}")

# Assert that we have enough iron plates before crafting
assert iron_plate_count >= 2, f"Not enough Iron Plates to craft an Iron Gear Wheel. Required: 2, Available: {iron_plate_count}"

# Craft the iron gear wheel
crafted_quantity = craft_item(Prototype.IronGearWheel, quantity=1)
print(f"Crafted {crafted_quantity} Iron Gear Wheel(s)")

# Check inventory after crafting to verify success
updated_inventory = inspect_inventory()
gear_wheels_in_inventory = updated_inventory.get(Prototype.IronGearWheel, 0)
print(f"Iron Gear Wheels in inventory after crafting: {gear_wheels_in_inventory}")

# Assert that we've successfully crafted an iron gear wheel
assert gear_wheels_in_inventory >= 1, "Failed to craft an Iron Gear Wheel"

"""
Step 6: Craft transport belt
We need to craft 1 transport-belt using 1 iron gear wheel and 1 iron plate
"""
print("\nStep 6: Crafting transport belt")

# Get current inventory to check if we have enough materials
current_inventory = inspect_inventory()
gear_wheel_count = current_inventory.get(Prototype.IronGearWheel, 0)
iron_plate_count = current_inventory.get(Prototype.IronPlate, 0)
print(f"Current Iron Gear Wheel count in inventory: {gear_wheel_count}")
print(f"Current Iron Plate count in inventory: {iron_plate_count}")

# Assert that we have enough materials before crafting
assert gear_wheel_count >= 1, f"Not enough Iron Gear Wheels to craft a Transport Belt. Required: 1, Available: {gear_wheel_count}"
assert iron_plate_count >= 1, f"Not enough Iron Plates to craft a Transport Belt. Required: 1, Available: {iron_plate_count}"

# Craft the transport belt
crafted_quantity = craft_item(Prototype.TransportBelt, quantity=1)
print(f"Crafted {crafted_quantity} Transport Belt(s)")

# Check inventory after crafting to verify success
updated_inventory = inspect_inventory()
transport_belts_in_inventory = updated_inventory.get(Prototype.TransportBelt, 0)
print(f"Transport Belts in inventory after crafting: {transport_belts_in_inventory}")

# Assert that we've successfully crafted a transport belt
assert transport_belts_in_inventory >= 1, "Failed to craft a Transport Belt"

print("Successfully crafted a Transport Belt.")

# Final inventory check
final_inventory = inspect_inventory()
print("\nFinal inventory:")
print(f"Transport Belts: {final_inventory.get(Prototype.TransportBelt, 0)}")
print(f"Iron Plates: {final_inventory.get(Prototype.IronPlate, 0)}")
print(f"Iron Gear Wheels: {final_inventory.get(Prototype.IronGearWheel, 0)}")
print(f"Coal: {final_inventory.get(Prototype.Coal, 0)}")
print(f"Stone: {final_inventory.get(Prototype.Stone, 0)}")

