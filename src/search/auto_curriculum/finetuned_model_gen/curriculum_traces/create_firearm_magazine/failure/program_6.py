

from factorio_instance import *

"""
Step 1: Print the recipe for firearm magazine
"""
# Get the recipe for firearm magazine
recipe = get_prototype_recipe(Prototype.FirearmMagazine)

# Print the recipe details
print("firearm-magazine Recipe:")
print(f"Ingredients: {recipe.ingredients}")


"""
Step 1: Gather raw resources
- Mine iron ore (at least 3)
- Mine coal (at least 1 for fuel)
- Mine stone (at least 5 for the furnace)
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.IronOre, 3),
    (Resource.Coal, 1),
    (Resource.Stone, 5)
]

# Loop through each resource type and quantity needed
for resource_type, quantity_needed in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    print(f"Nearest {resource_type} found at {resource_position}")

    # Move to the resource location
    move_to(resource_position)
    print(f"Moved to {resource_type} position")

    # Harvest the resource
    harvested_amount = harvest_resource(resource_position, quantity_needed)
    print(f"Harvested {harvested_amount} {resource_type}")

    # Check if we gathered enough of this particular resource
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= quantity_needed, f"Failed to gather enough {resource_type}. Required: {quantity_needed}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")

# Assert that we've met or exceeded the required quantities for each resource type
assert final_inventory.get(Resource.IronOre, 0) >= 3, "Not enough Iron Ore!"
assert final_inventory.get(Resource.Coal, 0) >= 1, "Not enough Coal!"
assert final_inventory.get(Resource.Stone, 0) >= 5, "Not enough Stone!"

print("Successfully gathered all required resources!")

"""
Step 2: Craft stone furnace
- Craft one stone furnace using 5 stone
"""
# Crafting a stone furnace
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted {crafted_furnaces} Stone Furnace(s)")

# Verify that we've crafted exactly one Stone Furnace
current_inventory = inspect_inventory()
actual_furnaces = current_inventory.get(Prototype.StoneFurnace, 0)
assert actual_furnaces >= 1, f"Failed to craft enough Stone Furnaces. Expected at least 1, but found {actual_furnaces}"
print("Successfully crafted the required number of Stone Furnaces")

"""
Step 3: Set up smelting operation
- Place down the stone furnace
- Add coal as fuel to the furnace
"""
# Place the stone furnace at the origin
furnace_position = Position(x=0, y=0)
move_to(furnace_position)
furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)
print(f"Placed Stone Furnace at {furnace_position}")

# Insert coal into the stone furnace as fuel
coal_in_inventory = inspect_inventory()[Prototype.Coal]
coal_to_insert = min(coal_in_inventory, 5)  # Insert up to 5 coal or whatever is available
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=coal_to_insert)
print(f"Inserted {coal_to_insert} Coal into the Stone Furnace")

# Verify that the furnace has fuel
furnace_coal = updated_furnace.fuel.get(Prototype.Coal, 0)
assert furnace_coal > 0, "Failed to add coal to the Stone Furnace as fuel"
print("Successfully set up smelting operation with a fueled Stone Furnace")

"""
Step 4: Smelt iron plates
- Smelt at least 3 iron ore into iron plates
"""
# Get current inventory count for Iron Ore
iron_ore_in_inventory = inspect_inventory()[Prototype.IronOre]
print(f"Iron Ore available in inventory: {iron_ore_in_inventory}")

# Insert all available Iron Ore into the Stone Furnace
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} Iron Ore into the Stone Furnace")

# Calculate expected number of Iron Plates after smelting
initial_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
expected_iron_plate_count = initial_iron_plate_count + iron_ore_in_inventory

# Wait for smelting process to complete; assuming each unit takes about 1 second
sleep(iron_ore_in_inventory)

# Extract resulting Iron Plates from the Stone Furnace
max_attempts = 5
for attempt in range(max_attempts):
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plate_count >= expected_iron_plate_count:
        break
    sleep(2)

print(f"Extracted {current_iron_plate_count - initial_iron_plate_count} Iron Plates")
print(f"Current inventory count for Iron Plates: {current_iron_plate_count}")

# Assert that we've met or exceeded required quantity of Iron Plates
required_iron_plates = 3
assert current_iron_plate_count >= required_iron_plates, f"Failed to smelt enough Iron Plates! Required: {required_iron_plates}, Actual: {current_iron_plate_count}"
print("Successfully smelted required number of Iron Plates!")

"""
Step 5: Craft intermediate products
- Craft 2 iron gear wheels (requires 4 iron plates)
"""
# Get current inventory count for Iron Plates
iron_plates_in_inventory = inspect_inventory()[Prototype.IronPlate]
print(f"Iron Plates available in inventory: {iron_plates_in_inventory}")

# Ensure we have enough Iron Plates to craft Iron Gear Wheels
required_iron_plates_for_gears = 4
assert iron_plates_in_inventory >= required_iron_plates_for_gears, f"Not enough Iron Plates! Required: {required_iron_plates_for_gears}, Available: {iron_plates_in_inventory}"

# Crafting two Iron Gear Wheels
crafted_gears = craft_item(Prototype.IronGearWheel, quantity=2)
print(f"Crafted {crafted_gears} Iron Gear Wheel(s)")

# Verify that we've crafted exactly two Iron Gear Wheels
current_inventory = inspect_inventory()
actual_gears = current_inventory.get(Prototype.IronGearWheel, 0)
assert actual_gears >= 2, f"Failed to craft enough Iron Gear Wheels. Expected at least 2, but found {actual_gears}"
print("Successfully crafted the required number of Iron Gear Wheels")

"""
Step 6: Craft firearm magazine
- Craft 1 firearm magazine (requires 4 iron plates)
"""
# Print current inventory
print(f"Current inventory before crafting: {inspect_inventory()}")

# Get current inventory count for Iron Plates
iron_plates_in_inventory = inspect_inventory()[Prototype.IronPlate]
print(f"Iron Plates available in inventory: {iron_plates_in_inventory}")

# Ensure we have enough Iron Plates to craft Firearm Magazine
required_iron_plates_for_magazine = 4
assert iron_plates_in_inventory >= required_iron_plates_for_magazine, f"Not enough Iron Plates! Required: {required_iron_plates_for_magazine}, Available: {iron_plates_in_inventory}"

# Crafting one Firearm Magazine
crafted_magazines = craft_item(Prototype.FirearmMagazine, quantity=1)
print(f"Crafted {crafted_magazines} Firearm Magazine(s)")

# Verify that we've crafted exactly one Firearm Magazine
current_inventory = inspect_inventory()
actual_magazines = current_inventory.get(Prototype.FirearmMagazine, 0)
assert actual_magazines >= 1, f"Failed to craft a Firearm Magazine. Expected at least 1, but found {actual_magazines}"
print("Successfully crafted the required number of Firearm Magazines")

# Print final inventory
print(f"Final inventory after crafting: {inspect_inventory()}")

