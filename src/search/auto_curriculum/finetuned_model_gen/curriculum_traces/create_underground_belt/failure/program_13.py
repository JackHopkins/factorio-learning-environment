

from factorio_instance import *


"""
Objective: Craft an underground belt from raw materials

Planning:
We need to craft an underground belt from scratch. There are no entities on the map and nothing in our inventory, so we need to gather all resources and craft all necessary items.
We need to print recipes, gather raw resources, craft intermediate items, and finally craft the underground belt.
"""

"""
Step 1: Print recipes.
We need to print the recipe for underground belt, transport belt, iron gear wheel, iron plate, and stone furnace.
"""
# Get the recipe for underground-belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
print("Underground Belt Recipe:")
print(underground_belt_recipe)

# Get the recipe for transport-belt
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
print("Transport Belt Recipe:")
print(transport_belt_recipe)

# Get the recipe for iron-gear-wheel
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print("Iron Gear Wheel Recipe:")
print(iron_gear_wheel_recipe)

# Get the recipe for iron-plate
iron_plate_recipe = get_prototype_recipe(Prototype.IronPlate)
print("Iron Plate Recipe:")
print(iron_plate_recipe)

# Get the recipe for stone-furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print("Stone Furnace Recipe:")
print(stone_furnace_recipe)

"""
Step 2: Gather raw resources
- Mine iron ore (at least 12)
- Mine stone (at least 5 for furnace)
- Mine coal (at least 1 for fuel)
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 12),
    (Resource.Stone, 5),
    (Resource.Coal, 1)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest position of this resource type
    resource_position = nearest(resource_type)
    
    # Move to the resource position
    move_to(resource_position)
    
    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory after gathering:")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")

# Verify that we have at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 12, "Not enough Iron Ore"
assert final_inventory.get(Resource.Stone, 0) >= 5, "Not enough Stone"
assert final_inventory.get(Resource.Coal, 0) >= 1, "Not enough Coal"

print("Successfully gathered all required resources!")

"""
Step 3: Craft and set up smelting
- Craft a stone furnace
- Place the furnace
- Add coal to the furnace as fuel
- Smelt iron plates (at least 12)
"""
# Craft a stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 Stone Furnace")

# Place the stone furnace at the origin
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed Stone Furnace at {furnace.position}")

# Add coal to the furnace as fuel
coal_in_inventory = inspect_inventory()[Prototype.Coal]
insert_item(Prototype.Coal, furnace, quantity=coal_in_inventory)
print(f"Inserted {coal_in_inventory} coal into the Stone Furnace")

# Insert all available iron ore into the furnace
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
insert_item(Prototype.IronOre, furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} iron ore into the Stone Furnace")

# Wait for smelting to complete (0.7 seconds per unit of ore)
smelting_time = int(0.7 * iron_ore_in_inventory)
sleep(smelting_time)

# Extract iron plates from the furnace
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, furnace.position, quantity=iron_ore_in_inventory)
    current_iron_plate_count = inspect_inventory()[Prototype.IronPlate]
    
    if current_iron_plate_count >= iron_ore_in_inventory:
        break
    
    sleep(10)
    print(f"Retrying extraction; current count is {current_iron_plate_count}")

print(f"Extracted Iron Plates; Current Inventory Count: {current_iron_plate_count}")

# Verify that we have at least 12 iron plates
assert current_iron_plate_count >= 12, f"Expected at least 12 Iron Plates but got {current_iron_plate_count}"
print("Successfully smelted at least 12 Iron Plates!")

"""
Step 4: Craft intermediate items
- Craft 5 iron gear wheels (10 iron plates)
"""
# Craft 5 iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=5)
print("Crafted 5 Iron Gear Wheels")

# Verify that we have crafted 5 iron gear wheels
iron_gear_wheel_count = inspect_inventory()[Prototype.IronGearWheel]
assert iron_gear_wheel_count >= 5, f"Expected at least 5 Iron Gear Wheels but got {iron_gear_wheel_count}"

print("Successfully crafted 5 Iron Gear Wheels!")

"""
Step 5: Craft transport belts
- Craft 4 transport belts (5 iron gear wheels, 2 iron plates)
"""
# Craft 4 transport belts
craft_item(Prototype.TransportBelt, quantity=4)
print("Crafted 4 Transport Belts")

# Verify that we have crafted 4 transport belts
transport_belt_count = inspect_inventory()[Prototype.TransportBelt]
assert transport_belt_count >= 4, f"Expected at least 4 Transport Belts but got {transport_belt_count}"

print("Successfully crafted 4 Transport Belts!")

"""
Step 6: Craft underground belt
- Craft 1 underground belt (5 iron plates, 10 iron gear wheels)
"""
# Craft 1 underground belt
craft_item(Prototype.UndergroundBelt, quantity=1)
print("Crafted 1 Underground Belt")

# Verify that we have crafted 1 underground belt
underground_belt_count = inspect_inventory()[Prototype.UndergroundBelt]
assert underground_belt_count >= 1, f"Expected at least 1 Underground Belt but got {underground_belt_count}"

print("Successfully crafted 1 Underground Belt!")

# Final inventory check for logging purposes
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Underground Belts: {final_inventory.get(Prototype.UndergroundBelt, 0)}")
print(f"Transport Belts: {final_inventory.get(Prototype.TransportBelt, 0)}")
print(f"Iron Gear Wheels: {final_inventory.get(Prototype.IronGearWheel, 0)}")
print(f"Iron Plates: {final_inventory.get(Prototype.IronPlate, 0)}")

print("Objective completed: Created an underground belt from scratch!")

