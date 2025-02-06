
from instance import *

"""
Step 1: Print recipes. We need to craft a transport-belt, which requires 1 iron gear wheel and 1 iron plate. This is
the main objective of the task. We also need to craft a stone-furnace, burner-inserter, and firearm-magazine.
"""
# Print recipes for the items we need to craft
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
iron_gear_wheel_recipe = get_prototype_recipe(Prototype.IronGearWheel)
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
burner_inserter_recipe = get_prototype_recipe(Prototype.BurnerInserter)
firearm_magazine_recipe = get_prototype_recipe(Prototype.FirearmMagazine)

print("Recipes:")
print(f"Transport Belt: {transport_belt_recipe}")
print(f"Iron Gear Wheel: {iron_gear_wheel_recipe}")
print(f"Stone Furnace: {stone_furnace_recipe}")
print(f"Burner Inserter: {burner_inserter_recipe}")
print(f"Firearm Magazine: {firearm_magazine_recipe}")

"""
Step 2: Gather raw resources. We need to mine coal, stone, and iron ore. We need at least 2 coal for fuel, 6 stone
for crafting a stone furnace, and 22 iron ore for crafting the necessary items.
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.Coal, 5),
    (Resource.Stone, 10),
    (Resource.IronOre, 30)
]

# Loop through each resource type and gather the specified amount
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    # Move to the resource position
    move_to(resource_position)
    # Harvest the required amount of this resource
    harvested = harvest_resource(resource_position, required_quantity)
    # Print out how much we harvested
    print(f"Harvested {harvested} units of {resource_type}")
    # Check if we gathered enough by inspecting our inventory
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"

print("Successfully gathered all required raw resources.")

"""
Step 3: Craft and set up stone furnace. We need to craft a stone furnace using 5 stone, place it on the map, and
add coal as fuel.
"""
# Craft a stone furnace
print("Crafting a stone furnace...")
crafted = craft_item(Prototype.StoneFurnace, quantity=1)
assert crafted == 1, "Failed to craft stone furnace"
print("Successfully crafted a stone furnace.")

# Place the stone furnace at the origin
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed stone furnace at {furnace.position}")

# Add coal as fuel to the stone furnace
coal_quantity = 5  # Use 5 coal for initial fueling
insert_item(Prototype.Coal, furnace, quantity=coal_quantity)
print(f"Inserted {coal_quantity} units of coal into the stone furnace.")

# Verify that the stone furnace has been fueled
fueled_furnace = get_entity(Prototype.StoneFurnace, position=furnace.position)
coal_in_furnace = fueled_furnace.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace > 0, "Stone furnace is not fueled"
print("Successfully set up and fueled the stone furnace.")

"""
Step 4: Smelt iron plates. We need to smelt 22 iron ore into iron plates. This will take some time, so we need to
wait for the smelting process to complete.
"""
# Move to the furnace position
move_to(furnace.position)

# Insert iron ore into the stone furnace
iron_ore_quantity = 22
insert_item(Prototype.IronOre, furnace, quantity=iron_ore_quantity)
print(f"Inserted {iron_ore_quantity} units of iron ore into the stone furnace.")

# Calculate the expected number of iron plates after smelting
initial_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
expected_iron_plate_count = initial_iron_plate_count + iron_ore_quantity

# Wait for the smelting process to complete
smelting_time_per_unit = 0.7
total_smelting_time = int(smelting_time_per_unit * iron_ore_quantity)
sleep(total_smelting_time)

# Start a loop to repeatedly attempt extracting iron plates until we reach the expected count
max_attempts = 10
for attempt in range(max_attempts):
    # Try extracting all possible iron plates
    extract_item(Prototype.IronPlate, furnace.position, quantity=iron_ore_quantity)

    # Check current inventory count of iron plates
    current_iron_plate_count = inspect_inventory().get(Prototype.IronPlate, 0)
    print(f"Attempt {attempt + 1}: Current iron plate count: {current_iron_plate_count}")

    # If we've reached or exceeded expected count break out of loop early
    if current_iron_plate_count >= expected_iron_plate_count:
        break

    # If not enough yet wait a bit more before trying again
    sleep(10)

assert current_iron_plate_count >= expected_iron_plate_count, f"Failed to smelt enough iron plates. Expected: {expected_iron_plate_count}, Actual: {current_iron_plate_count}"
print(f"Successfully smelted {current_iron_plate_count} iron plates!")

"""
Step 5: Craft iron gear wheels. We need to craft 3 iron gear wheels using 6 iron plates.
"""
# Craft 3 iron gear wheels
print("Crafting 3 iron gear wheels...")
crafted = craft_item(Prototype.IronGearWheel, quantity=3)
assert crafted == 3, f"Failed to craft 3 iron gear wheels. Crafted: {crafted}"
print("Successfully crafted 3 iron gear wheels.")

# Verify that we have the correct number of iron gear wheels in our inventory
iron_gear_wheel_count = inspect_inventory().get(Prototype.IronGearWheel, 0)
assert iron_gear_wheel_count >= 3, f"Insufficient iron gear wheels after crafting. Expected at least 3, but got {iron_gear_wheel_count}"
print(f"Successfully verified that we have {iron_gear_wheel_count} iron gear wheels in our inventory.")

"""
Step 6: Craft burner-inserter. We need to craft a burner-inserter using 1 iron gear wheel and 1 iron plate.
"""
# Craft a burner-inserter
print("Crafting a burner-inserter...")
crafted = craft_item(Prototype.BurnerInserter, quantity=1)
assert crafted == 1, f"Failed to craft burner-inserter. Crafted: {crafted}"
print("Successfully crafted a burner-inserter.")

# Verify that we have the burner-inserter in our inventory
burner_inserter_count = inspect_inventory().get(Prototype.BurnerInserter, 0)
assert burner_inserter_count >= 1, f"Insufficient burner-inserters after crafting. Expected at least 1, but got {burner_inserter_count}"
print(f"Successfully verified that we have {burner_inserter_count} burner-inserters in our inventory.")

"""
Step 7: Craft firearm-magazine. We need to craft a firearm-magazine using 4 iron plates.
"""
# Craft a firearm-magazine
print("Crafting a firearm-magazine...")
crafted = craft_item(Prototype.FirearmMagazine, quantity=1)
assert crafted == 1, f"Failed to craft firearm-magazine. Crafted: {crafted}"
print("Successfully crafted a firearm-magazine.")

# Verify that we have the firearm-magazine in our inventory
firearm_magazine_count = inspect_inventory().get(Prototype.FirearmMagazine, 0)
assert firearm_magazine_count >= 1, f"Insufficient firearm-magazines after crafting. Expected at least 1, but got {firearm_magazine_count}"
print(f"Successfully verified that we have {firearm_magazine_count} firearm-magazines in our inventory.")

"""
Step 8: Craft transport-belt. We need to craft 1 transport-belt using 1 iron gear wheel and 1 iron plate.
"""
# Craft 1 transport-belt
print("Crafting 1 transport-belt...")
crafted = craft_item(Prototype.TransportBelt, quantity=1)
assert crafted == 1, f"Failed to craft 1 transport-belt. Crafted: {crafted}"
print("Successfully crafted 1 transport-belt.")

# Verify that we have the correct number of transport-belts in our inventory
transport_belt_count = inspect_inventory().get(Prototype.TransportBelt, 0)
assert transport_belt_count >= 1, f"Insufficient transport-belts after crafting. Expected at least 1, but got {transport_belt_count}"
print(f"Successfully verified that we have {transport_belt_count} transport-belts in our inventory.")

"""
Final step: Verify crafted items. We need to check our inventory to ensure we have 1 burner-inserter, 1
transport-belt, and 1 firearm-magazine.
"""
# Check final inventory for required items
final_inventory = inspect_inventory()

burner_inserter_count = final_inventory.get(Prototype.BurnerInserter, 0)
transport_belt_count = final_inventory.get(Prototype.TransportBelt, 0)
firearm_magazine_count = final_inventory.get(Prototype.FirearmMagazine, 0)

assert burner_inserter_count >= 1, f"Expected at least 1 Burner Inserter but found {burner_inserter_count}"
assert transport_belt_count >= 1, f"Expected at least 1 Transport Belt but found {transport_belt_count}"
assert firearm_magazine_count >= 1, f"Expected at least 1 Firearm Magazine but found {firearm_magazine_count}"

print("Successfully verified that all required items are present in the inventory.")
