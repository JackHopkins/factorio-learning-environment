
from instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- burner-mining-drill
- transport-belt
- underground-belt
- stone-furnace
- iron-gear-wheel

OUTPUT: Printed recipes
"""
# List of items to print recipes for
items_to_print = [Prototype.BurnerMiningDrill, Prototype.TransportBelt, Prototype.UndergroundBelt, Prototype.StoneFurnace, Prototype.IronGearWheel]

# Loop through each item and print its recipe
for item in items_to_print:
    recipe = get_prototype_recipe(item)
    print(f"Recipe for {item}:")
    print(f"Ingredients: {recipe.ingredients}")
    print(f"Products: {recipe.products if recipe.products else 'N/A'}")
    print(f"Energy required: {recipe.energy}")
    print("-" * 40)


"""
Step 2: Gather resources. We need to gather the following resources:
- 12 stone (for 2 stone furnaces)
- 25 iron ore (for 25 iron plates)
- 2 coal (for fueling the furnaces)

OUTPUT: Gathered resources in the inventory
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 12),
    (Resource.IronOre, 25),
    (Resource.Coal, 2)
]

# Loop through each resource and gather it
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
print("Final inventory:")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")


"""
Step 3: Craft stone furnaces. We need to craft 2 stone furnaces.
"""
# Craft two stone furnaces
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=2)
assert crafted_furnaces == 2, f"Failed to craft 2 Stone Furnaces. Only crafted {crafted_furnaces}"

# Verify that we have crafted the stone furnaces
current_inventory = inspect_inventory()
stone_furnaces_in_inventory = current_inventory.get(Prototype.StoneFurnace, 0)
assert stone_furnaces_in_inventory >= 2, f"Inventory does not show 2 Stone Furnaces. Current inventory count: {stone_furnaces_in_inventory}"

print(f"Successfully crafted 2 Stone Furnaces. Current inventory count: {stone_furnaces_in_inventory}")


"""
Step 4: Set up smelting operation. We need to:
- Place a stone furnace
- Fuel the furnace with coal
- Smelt 25 iron ore into iron plates

OUTPUT: 25 iron plates in the inventory
"""
# Place the first stone furnace
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))

# Move to the furnace position
move_to(furnace.position)

# Add coal to the furnace as fuel
fueled_furnace = insert_item(Prototype.Coal, furnace, quantity=2)
print("Inserted coal into the stone furnace.")

# Add iron ore to the furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
fueled_furnace = insert_item(Prototype.IronOre, fueled_furnace, quantity=iron_ore_in_inventory)
print("Inserted iron ore into the stone furnace.")

# Wait for smelting to complete
sleep(10)

# Extract iron plates from the furnace
max_attempts = 5
for _ in range(max_attempts):
    extract_item(Prototype.IronPlate, fueled_furnace.position, quantity=iron_ore_in_inventory)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= 25:
        break
    sleep(5)

final_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
assert final_iron_plate_count >= 25, f"Failed to smelt enough Iron Plates. Expected at least 25, but got {final_iron_plate_count}"

print(f"Successfully crafted {final_iron_plate_count} Iron Plates. Current inventory count: {final_iron_plate_count}")


"""
Step 5: Craft iron gear wheels. We need to craft 10 iron gear wheels.
"""
# Craft 10 iron gear wheels
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=10)
assert crafted_gear_wheels == 10, f"Failed to craft 10 Iron Gear Wheels. Only crafted {crafted_gear_wheels}"

# Verify that we have crafted the iron gear wheels
current_inventory = inspect_inventory()
gear_wheels_in_inventory = current_inventory.get(Prototype.IronGearWheel, 0)
assert gear_wheels_in_inventory >= 10, f"Inventory does not show 10 Iron Gear Wheels. Current inventory count: {gear_wheels_in_inventory}"

print(f"Successfully crafted 10 Iron Gear Wheels. Current inventory count: {gear_wheels_in_inventory}")


"""
Step 6: Craft transport belts. We need to craft 12 transport belts.
"""
# Craft 12 transport belts
crafted_transport_belts = craft_item(Prototype.TransportBelt, quantity=12)
assert crafted_transport_belts == 12, f"Failed to craft 12 Transport Belts. Only crafted {crafted_transport_belts}"

# Verify that we have crafted the transport belts
current_inventory = inspect_inventory()
transport_belts_in_inventory = current_inventory.get(Prototype.TransportBelt, 0)
assert transport_belts_in_inventory >= 12, f"Inventory does not show 12 Transport Belts. Current inventory count: {transport_belts_in_inventory}"

print(f"Successfully crafted 12 Transport Belts. Current inventory count: {transport_belts_in_inventory}")


"""
Step 7: Craft underground belts. We need to craft 4 underground belts.
"""
# Craft 4 underground belts
crafted_underground_belts = craft_item(Prototype.UndergroundBelt, quantity=4)
assert crafted_underground_belts == 4, f"Failed to craft 4 Underground Belts. Only crafted {crafted_underground_belts}"

# Verify that we have crafted the underground belts
current_inventory = inspect_inventory()
underground_belts_in_inventory = current_inventory.get(Prototype.UndergroundBelt, 0)
assert underground_belts_in_inventory >= 4, f"Inventory does not show 4 Underground Belts. Current inventory count: {underground_belts_in_inventory}"

print(f"Successfully crafted 4 Underground Belts. Current inventory count: {underground_belts_in_inventory}")

"""
Step 8: Craft burner mining drill. We need to craft 1 burner mining drill.
"""
# Craft 1 burner mining drill
crafted_burner_mining_drill = craft_item(Prototype.BurnerMiningDrill, quantity=1)
assert crafted_burner_mining_drill == 1, f"Failed to craft 1 Burner Mining Drill. Only crafted {crafted_burner_mining_drill}"

# Verify that we have crafted the burner mining drill
current_inventory = inspect_inventory()
burner_mining_drill_in_inventory = current_inventory.get(Prototype.BurnerMiningDrill, 0)
assert burner_mining_drill_in_inventory >= 1, f"Inventory does not show 1 Burner Mining Drill. Current inventory count: {burner_mining_drill_in_inventory}"

print(f"Successfully crafted 1 Burner Mining Drill. Current inventory count: {burner_mining_drill_in_inventory}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Burner Mining Drill: {final_inventory.get(Prototype.BurnerMiningDrill, 0)}")
print(f"Underground Belts: {final_inventory.get(Prototype.UndergroundBelt, 0)}")
print(f"Transport Belts: {final_inventory.get(Prototype.TransportBelt, 0)}")
print(f"Iron Gear Wheels: {final_inventory.get(Prototype.IronGearWheel, 0)}")
print(f"Iron Plates: {final_inventory.get(Prototype.IronPlate, 0)}")

# Assert that all required items are present in the final inventory
assert final_inventory.get(Prototype.BurnerMiningDrill, 0) >= 1, "Missing Burner Mining Drill"
assert final_inventory.get(Prototype.UndergroundBelt, 0) >= 4, "Missing Underground Belts"
assert final_inventory.get(Prototype.TransportBelt, 0) >= 12, "Missing Transport Belts"
assert final_inventory.get(Prototype.IronGearWheel, 0) >= 4, "Missing Iron Gear Wheels"
assert final_inventory.get(Prototype.IronPlate, 0) >= 25, "Missing Iron Plates"

print("Successfully completed all tasks. All required items are present in the final inventory.")

