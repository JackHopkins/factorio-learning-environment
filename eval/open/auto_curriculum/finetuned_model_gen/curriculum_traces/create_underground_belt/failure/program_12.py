

from instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- transport-belt
- underground-belt
"""
# Get and print the recipe for transport-belt
recipe_transport_belt = get_prototype_recipe(Prototype.TransportBelt)
print("Transport Belt Recipe:")
print(f"Ingredients: {recipe_transport_belt.ingredients}")

# Get and print the recipe for underground-belt
recipe_underground_belt = get_prototype_recipe(Prototype.UndergroundBelt)
print("Underground Belt Recipe:")
print(f"Ingredients: {recipe_underground_belt.ingredients}")

"""
Step 2: Gather raw resources. We need to mine the following resources:
- 26 iron ore
- 12 stone
- 2 coal
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 26),
    (Resource.Stone, 12),
    (Resource.Coal, 2)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    print(f"Nearest {resource_type} found at {resource_position}")

    # Move to the resource patch
    move_to(resource_position)
    print(f"Moved to {resource_type} patch")

    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    print(f"Harvested {harvested} units of {resource_type}")

    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} units of {resource_type}")

# Log final inventory after gathering all resources
final_inventory = inspect_inventory()
print("Final inventory after gathering resources:")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")

# Assert that we have gathered at least the required quantities
assert final_inventory.get(Resource.IronOre, 0) >= 26, "Insufficient Iron Ore"
assert final_inventory.get(Resource.Stone, 0) >= 12, "Insufficient Stone"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Insufficient Coal"

print("Successfully completed Step 2: Gathered all required raw resources")


"""
Step 3: Craft stone furnaces. We need to craft 2 stone furnaces. Each stone furnace requires 5 stone, so we need 10 stone in total.
"""
# Check current inventory for available stone
current_inventory = inspect_inventory()
stone_available = current_inventory.get(Resource.Stone, 0)

# Verify that we have enough stone to craft 2 furnaces
assert stone_available >= 10, f"Insufficient Stone! Expected at least 10 but found {stone_available}"
print(f"Stone available: {stone_available}")

# Craft two Stone Furnaces
furnaces_to_craft = 2
crafted_furnaces = craft_item(Prototype.StoneFurnace, furnaces_to_craft)
print(f"Crafted {crafted_furnaces} Stone Furnaces")

# Verify that we crafted the correct number of furnaces
assert crafted_furnaces == furnaces_to_craft, f"Failed to craft required number of Stone Furnaces! Expected: {furnaces_to_craft}, Actual: {crafted_furnaces}"
print("Successfully crafted required number of Stone Furnaces")

# Log final inventory after crafting
final_inventory = inspect_inventory()
print("Final inventory after crafting Stone Furnaces:")
print(f"Stone Furnaces: {final_inventory.get(Prototype.StoneFurnace, 0)}")

# Assert that we have crafted exactly two Stone Furnaces
assert final_inventory.get(Prototype.StoneFurnace, 0) >= 2, "Failed to craft required number of Stone Furnaces"
print("Successfully completed Step 3: Crafted two Stone Furnaces")


"""
Step 4: Set up smelting operation. We need to:
- Place the two stone furnaces
- Add coal to the furnaces
- Smelt 26 iron ore into 26 iron plates
"""
# Place two stone furnaces next to each other
origin = Position(x=0, y=0)
move_to(origin)
furnace1 = place_entity(Prototype.StoneFurnace, position=origin)
furnace2 = place_entity(Prototype.StoneFurnace, position=Position(x=1, y=0))

# Check if furnaces were placed correctly by inspecting entities around us
entities_nearby = inspect_entities(position=origin, radius=2)
placed_furnaces = [e for e in entities_nearby.entities if e.name == Prototype.StoneFurnace.value[0]]
assert len(placed_furnaces) == 2, f"Failed to place two Stone Furnaces! Found {len(placed_furnaces)}"

print("Successfully placed two Stone Furnaces")

# Insert coal into both furnaces as fuel
coal_quantity = 1  # Use one piece of coal per furnace

for furnace in placed_furnaces:
    insert_item(Prototype.Coal, target=furnace, quantity=coal_quantity)
    print(f"Inserted {coal_quantity} unit(s) of coal into Furnace at position {furnace.position}")

# Smelt iron ore into iron plates
iron_ore_quantity = 26
for furnace in placed_furnaces:
    insert_item(Resource.IronOre, target=furnace, quantity=iron_ore_quantity//2)
    print(f"Inserted {iron_ore_quantity//2} unit(s) of Iron Ore into Furnace at position {furnace.position}")

# Wait for smelting to complete (approximately 0.7 seconds per piece)
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_quantity)
sleep(total_smelting_time)

# Extract iron plates from both furnaces
for furnace in placed_furnaces:
    extract_item(Prototype.IronPlate, position=furnace.position, quantity=iron_ore_quantity//2)
    print(f"Extracted Iron Plates from Furnace at position {furnace.position}")

# Verify that we have enough iron plates
final_inventory = inspect_inventory()
iron_plates = final_inventory.get(Prototype.IronPlate, 0)
assert iron_plates >= 26, f"Failed to smelt required number of Iron Plates! Expected at least 26, but found {iron_plates}"
print(f"Successfully smelted {iron_plates} Iron Plates")


"""
Step 5: Craft iron gear wheels. We need to craft 8 iron gear wheels. Each iron gear wheel requires 2 iron plates, so we need 16 iron plates in total.
"""
# Check current inventory for available iron plates
current_inventory = inspect_inventory()
iron_plates_available = current_inventory.get(Prototype.IronPlate, 0)

# Verify that we have enough iron plates to craft 8 iron gear wheels
required_iron_plates = 16
assert iron_plates_available >= required_iron_plates, f"Insufficient Iron Plates! Expected at least {required_iron_plates} but found {iron_plates_available}"
print(f"Iron Plates available: {iron_plates_available}")

# Craft eight Iron Gear Wheels
gear_wheels_to_craft = 8
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, gear_wheels_to_craft)
print(f"Crafted {crafted_gear_wheels} Iron Gear Wheels")

# Verify that we crafted the correct number of gear wheels
assert crafted_gear_wheels == gear_wheels_to_craft, f"Failed to craft required number of Iron Gear Wheels! Expected: {gear_wheels_to_craft}, Actual: {crafted_gear_wheels}"
print("Successfully crafted required number of Iron Gear Wheels")

# Log final inventory after crafting
final_inventory = inspect_inventory()
print("Final inventory after crafting Iron Gear Wheels:")
print(f"Iron Gear Wheels: {final_inventory.get(Prototype.IronGearWheel, 0)}")

# Assert that we have crafted exactly eight Iron Gear Wheels
assert final_inventory.get(Prototype.IronGearWheel, 0) >= 8, "Failed to craft required number of Iron Gear Wheels"
print("Successfully completed Step 5: Crafted eight Iron Gear Wheels")


"""
Step 6: Craft transport-belt. We need to craft 1 transport-belt. 
Each transport-belt requires 1 iron gear wheel and 1 iron plate, so we need 1 iron gear wheel and 1 iron plate in total.
"""
# Check current inventory for available iron gear wheels and iron plates
current_inventory = inspect_inventory()
iron_gear_wheels_available = current_inventory.get(Prototype.IronGearWheel, 0)
iron_plates_available = current_inventory.get(Prototype.IronPlate, 0)

# Verify that we have enough iron gear wheels and iron plates to craft one transport-belt
required_iron_gear_wheels = 1
required_iron_plates = 1
assert iron_gear_wheels_available >= required_iron_gear_wheels, f"Insufficient Iron Gear Wheels! Expected at least {required_iron_gear_wheels} but found {iron_gear_wheels_available}"
assert iron_plates_available >= required_iron_plates, f"Insufficient Iron Plates! Expected at least {required_iron_plates} but found {iron_plates_available}"
print(f"Iron Gear Wheels available: {iron_gear_wheels_available}")
print(f"Iron Plates available: {iron_plates_available}")

# Craft one Transport Belt
transport_belts_to_craft = 1
crafted_transport_belts = craft_item(Prototype.TransportBelt, transport_belts_to_craft)
print(f"Crafted {crafted_transport_belts} Transport Belt(s)")

# Verify that we crafted the correct number of transport belts
assert crafted_transport_belts == transport_belts_to_craft, f"Failed to craft required number of Transport Belts! Expected: {transport_belts_to_craft}, Actual: {crafted_transport_belts}"
print("Successfully crafted required number of Transport Belts")

# Log final inventory after crafting
final_inventory = inspect_inventory()
print("Final inventory after crafting Transport Belts:")
print(f"Transport Belts: {final_inventory.get(Prototype.TransportBelt, 0)}")

# Assert that we have crafted exactly one Transport Belt
assert final_inventory.get(Prototype.TransportBelt, 0) >= 1, "Failed to craft required number of Transport Belts"
print("Successfully completed Step 6: Crafted one Transport Belt")


"""
Step 7: Craft underground-belt. We need to craft 1 underground-belt. 
Each underground-belt requires 5 iron gear wheels, 10 iron plates, and 2 transport-belts, so we need 5 iron gear wheels, 10 iron plates, and 2 transport-belts in total.
"""
# Check current inventory for available iron gear wheels, iron plates, and transport-belts
current_inventory = inspect_inventory()
iron_gear_wheels_available = current_inventory.get(Prototype.IronGearWheel, 0)
iron_plates_available = current_inventory.get(Prototype.IronPlate, 0)
transport_belts_available = current_inventory.get(Prototype.TransportBelt, 0)

# Verify that we have enough resources to craft one underground-belt
required_iron_gear_wheels = 5
required_iron_plates = 10
required_transport_belts = 2
assert iron_gear_wheels_available >= required_iron_gear_wheels, f"Insufficient Iron Gear Wheels! Expected at least {required_iron_gear_wheels} but found {iron_gear_wheels_available}"
assert iron_plates_available >= required_iron_plates, f"Insufficient Iron Plates! Expected at least {required_iron_plates} but found {iron_plates_available}"
assert transport_belts_available >= required_transport_belts, f"Insufficient Transport Belts! Expected at least {required_transport_belts} but found {transport_belts_available}"
print(f"Iron Gear Wheels available: {iron_gear_wheels_available}")
print(f"Iron Plates available: {iron_plates_available}")
print(f"Transport Belts available: {transport_belts_available}")

# Craft one Underground Belt
underground_belts_to_craft = 1
crafted_underground_belts = craft_item(Prototype.UndergroundBelt, underground_belts_to_craft)
print(f"Crafted {crafted_underground_belts} Underground Belt(s)")

# Verify that we crafted the correct number of underground belts
assert crafted_underground_belts == underground_belts_to_craft, f"Failed to craft required number of Underground Belts! Expected: {underground_belts_to_craft}, Actual: {crafted_underground_belts}"
print("Successfully crafted required number of Underground Belts")

# Log final inventory after crafting
final_inventory = inspect_inventory()
print("Final inventory after crafting Underground Belts:")
print(f"Underground Belts: {final_inventory.get(Prototype.UndergroundBelt, 0)}")

# Assert that we have crafted exactly one Underground Belt
assert final_inventory.get(Prototype.UndergroundBelt, 0) >= 1, "Failed to craft required number of Underground Belts"
print("Successfully completed Step 7: Crafted one Underground Belt")


