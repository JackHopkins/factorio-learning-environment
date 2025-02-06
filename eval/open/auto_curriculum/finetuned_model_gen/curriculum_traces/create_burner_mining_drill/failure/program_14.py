

from instance import *

"""
Objective: Craft a burner mining drill from scratch

Planning:
We need to craft a burner mining drill and underground belts.
There are no entities on the map, so we need to start from scratch.
We need to gather raw resources, craft intermediate products, and then craft the final products.
We also need to craft 2 stone furnaces: one for smelting and one for the burner mining drill recipe.
"""

"""
Step 1: Print recipes
"""

# Get the recipes for the items we need to craft
burner_mining_drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)

# Print the recipes
print("Burner Mining Drill Recipe:")
print(burner_mining_drill_recipe)
print("\nStone Furnace Recipe:")
print(stone_furnace_recipe)
print("\nUnderground Belt Recipe:")
print(underground_belt_recipe)
print("\nTransport Belt Recipe:")
print(transport_belt_recipe)
print("\nIron Gear Wheel Recipe:")
print(iron_gear_wheel_recipe)

"""
Step 2: Gather raw resources
- Mine iron ore
- Mine stone
- Mine coal
"""
# Define the required resources and their quantities
resources_to_gather = [
    (Resource.IronOre, 25),  # We need at least 25 iron plates
    (Resource.Stone, 12),   # We need 12 stone for 2 furnaces
    (Resource.Coal, 10)     # We need coal for fuel
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
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

# Assert that we have at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 25, "Not enough Iron Ore"
assert final_inventory.get(Resource.Stone, 0) >= 12, "Not enough Stone"
assert final_inventory.get(Resource.Coal, 0) >= 10, "Not enough Coal"

print("Successfully gathered all required resources!")

"""
Step 3: Craft stone furnaces
- Craft 2 stone furnaces (1 for smelting, 1 for burner mining drill)
"""
# Craft 2 stone furnaces
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=2)
print(f"Crafted {crafted_furnaces} Stone Furnaces")

# Verify that we have 2 stone furnaces in our inventory
current_inventory = inspect_inventory()
stone_furnace_count = current_inventory.get(Prototype.StoneFurnace, 0)
assert stone_furnace_count >= 2, f"Failed to craft enough Stone Furnaces. Expected: 2, Actual: {stone_furnace_count}"
print(f"Successfully crafted 2 Stone Furnaces; Current Inventory Count: {stone_furnace_count}")

"""
Step 4: Set up smelting area
- Place a stone furnace
- Add coal to the furnace as fuel
- Smelt iron ore into iron plates
"""
# Place a stone furnace
origin = Position(x=0, y=0)
move_to(origin)
smelting_furnace = place_entity(Prototype.StoneFurnace, position=origin)

# Add coal to the furnace as fuel
coal_quantity = 5  # Use some of the gathered coal for initial fueling
updated_furnace = insert_item(Prototype.Coal, smelting_furnace, quantity=coal_quantity)
print("Inserted coal into the stone furnace.")

# Smelt iron ore into iron plates
iron_ore_quantity = 25
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_quantity)
print("Inserted iron ore into the stone furnace.")

# Wait for smelting to complete
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_quantity)
sleep(total_smelting_time)

# Extract iron plates
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_quantity)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= 20:
        break
    sleep(10)

print(f"Extracted Iron Plates; Current Inventory Count: {current_iron_plate_count}")
assert current_iron_plate_count >= 20, f"Failed to obtain enough Iron Plates. Expected: At least 20, Actual: {current_iron_plate_count}"

"""
Step 5: Craft intermediate products
- Craft 10 iron gear wheels
"""
# Craft 10 iron gear wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=10)
print(f"Crafted {crafted_gear_wheels} Iron Gear Wheels")

# Verify that we have 10 iron gear wheels in our inventory
current_inventory = inspect_inventory()
gear_wheel_count = current_inventory.get(Prototype.IronGearWheel, 0)
assert gear_wheel_count >= 10, f"Failed to craft enough Iron Gear Wheels. Expected: 10, Actual: {gear_wheel_count}"
print(f"Successfully crafted 10 Iron Gear Wheels; Current Inventory Count: {gear_wheel_count}")

"""
Step 6: Craft final products
- Craft 1 burner mining drill
- Craft 4 underground belts
- Craft 12 transport belts
"""
# Craft 1 burner mining drill
crafted_drill = craft_item(Prototype.BurnerMiningDrill, quantity=1)
print(f"Crafted {crafted_drill} Burner Mining Drill")

# Craft 12 transport belts
crafted_transport_belts = craft_item(Prototype.TransportBelt, quantity=12)
print(f"Crafted {crafted_transport_belts} Transport Belts")

# Craft 4 underground belts
crafted_underground_belts = craft_item(Prototype.UndergroundBelt, quantity=4)
print(f"Crafted {crafted_underground_belts} Underground Belts")

"""
Step 7: Verify crafting
"""
# Check inventory for all crafted items
final_inventory = inspect_inventory()
print("Final Inventory:")
print(f"Burner Mining Drill: {final_inventory.get(Prototype.BurnerMiningDrill, 0)}")
print(f"Transport Belts: {final_inventory.get(Prototype.TransportBelt, 0)}")
print(f"Underground Belts: {final_inventory.get(Prototype.UndergroundBelt, 0)}")

# Assert that we have crafted all required items
assert final_inventory.get(Prototype.BurnerMiningDrill, 0) >= 1, "Failed to craft Burner Mining Drill"
assert final_inventory.get(Prototype.TransportBelt, 0) >= 12, "Failed to craft enough Transport Belts"
assert final_inventory.get(Prototype.UndergroundBelt, 0) >= 4, "Failed to craft enough Underground Belts"

print("Successfully crafted all required items!")

