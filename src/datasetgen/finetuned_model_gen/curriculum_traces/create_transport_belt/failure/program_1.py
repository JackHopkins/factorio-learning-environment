
from factorio_instance import *


"""
Step 1: Print recipes. We need to print to following recipes:
- transport-belt
- burner-inserter
- firearm-magazine
- stone-furnace
"""
# Print recipes
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)
burner_inserter_recipe = get_prototype_recipe(Prototype.BurnerInserter)
firearm_magazine_recipe = get_prototype_recipe(Prototype.FirearmMagazine)
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)

print(f"Transport Belt Recipe: {transport_belt_recipe}")
print(f"Burner Inserter Recipe: {burner_inserter_recipe}")
print(f"Firearm Magazine Recipe: {firearm_magazine_recipe}")
print(f"Stone Furnace Recipe: {stone_furnace_recipe}")


"""
Step 2: Gather initial resources. We need to get the following resources:
- Mine 22 iron ore
- Mine 6 stone
- Mine 2 coal
"""
# Define resources to gather
resources_to_gather = [
    (Resource.IronOre, 22),
    (Resource.Stone, 6),
    (Resource.Coal, 2)
]

# Loop through each resource type and gather the required amount
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest position of the current resource type
    resource_position = nearest(resource_type)
    print(f"Nearest {resource_type} found at position: {resource_position}")

    # Move to the resource position
    move_to(resource_position)
    print(f"Moved to {resource_type} position: {resource_position}")

    # Harvest the resource
    harvested = harvest_resource(resource_position, required_quantity)
    print(f"Harvested {harvested} units of {resource_type}")

    # Verify that we have gathered the required amount
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} units of {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final Inventory: {final_inventory}")

# Assert that we have at least the required quantities of each resource
assert final_inventory.get(Resource.IronOre, 0) >= 22, "Not enough Iron Ore"
assert final_inventory.get(Resource.Stone, 0) >= 6, "Not enough Stone"
assert final_inventory.get(Resource.Coal, 0) >= 2, "Not enough Coal"

print("Successfully gathered all required resources!")


"""
Step 3: Craft stone furnace. We need to craft:
- 1 stone furnace
"""
# Craft a stone furnace using 5 stone
crafted_furnaces = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted {crafted_furnaces} Stone Furnace(s)")

# Verify that we have crafted at least one stone furnace
stone_furnaces_in_inventory = inspect_inventory().get(Prototype.StoneFurnace, 0)
assert stone_furnaces_in_inventory >= 1, f"Failed to craft Stone Furnace. Expected at least 1, but found {stone_furnaces_in_inventory}"
print(f"Successfully crafted a Stone Furnace. Current inventory count: {stone_furnaces_in_inventory}")

# Additional inventory check for remaining stone
remaining_stone = inspect_inventory().get(Resource.Stone, 0)
print(f"Remaining Stone in Inventory: {remaining_stone}")

print("Completed crafting of Stone Furnace and verified its presence in the inventory.")


"""
Step 4: Set up smelting operation. We need to:
- Place the stone furnace
- Add coal to the furnace as fuel
"""
# Place the stone furnace at the origin
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
print(f"Placed Stone Furnace at position: {furnace.position}")

# Insert coal into the furnace as fuel
coal_inserted = insert_item(Prototype.Coal, furnace, quantity=2)
print(f"Inserted {coal_inserted} units of Coal into the Stone Furnace")

# Verify that coal has been inserted successfully
coal_in_furnace = furnace.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace > 0, "Failed to insert Coal into the Stone Furnace"
print("Coal successfully inserted into the Stone Furnace as fuel")

# Update furnace reference after inserting items
furnace = get_entity(Prototype.StoneFurnace, position=furnace.position)


"""
Step 5: Smelt iron plates. We need to:
- Smelt 22 iron ore into iron plates
"""
# Calculate required iron plates
required_iron_plates = 22

# Insert all harvested iron ore into the furnace
iron_ore_inserted = insert_item(Prototype.IronOre, furnace, quantity=22)
print(f"Inserted {iron_ore_inserted} units of Iron Ore into the Stone Furnace")

# Start smelting process: Wait for smelting to complete
smelting_time_per_unit = 0.7  # Adjusted time per unit for safety margin
total_smelting_time = int(smelting_time_per_unit * required_iron_plates)
sleep(total_smelting_time)

# Extract iron plates from the furnace
max_attempts_to_extract = 5
for attempt in range(max_attempts_to_extract):
    extract_item(Prototype.IronPlate, furnace.position, quantity=required_iron_plates)
    current_inventory = inspect_inventory()
    iron_plates_in_inventory = current_inventory.get(Prototype.IronPlate, 0)
    
    if iron_plates_in_inventory >= required_iron_plates:
        break
    
    sleep(10)  # Allow additional time if needed

print(f"Extracted Iron Plates; Current Inventory Count: {iron_plates_in_inventory}")

# Final verification of iron plates count
assert iron_plates_in_inventory >= required_iron_plates, f"Failed to smelt enough Iron Plates. Expected at least {required_iron_plates}, but found {iron_plates_in_inventory}"
print(f"Successfully smelted {iron_plates_in_inventory} Iron Plates")


"""
Step 6: Craft iron gear wheels. We need to craft:
- 2 iron gear wheels
"""
# Craft iron gear wheels using available iron plates
crafted_gear_wheels = craft_item(Prototype.IronGearWheel, quantity=2)
print(f"Crafted {crafted_gear_wheels} Iron Gear Wheel(s)")

# Verify that we have crafted the required number of iron gear wheels
gear_wheels_in_inventory = inspect_inventory().get(Prototype.IronGearWheel, 0)
assert gear_wheels_in_inventory >= 2, f"Failed to craft Iron Gear Wheels. Expected at least 2, but found {gear_wheels_in_inventory}"
print(f"Successfully crafted {gear_wheels_in_inventory} Iron Gear Wheel(s)")


"""
Step 7: Craft burner inserter. We need to craft:
- 1 burner inserter
"""
# Craft a burner inserter using available materials
crafted_burner_inserters = craft_item(Prototype.BurnerInserter, quantity=1)
print(f"Crafted {crafted_burner_inserters} Burner Inserter(s)")

# Verify that we have crafted the required number of burner inserters
burner_inserters_in_inventory = inspect_inventory().get(Prototype.BurnerInserter, 0)
assert burner_inserters_in_inventory >= 1, f"Failed to craft Burner Inserters. Expected at least 1, but found {burner_inserters_in_inventory}"
print(f"Successfully crafted {burner_inserters_in_inventory} Burner Inserter(s)")


"""
Step 8: Craft firearm magazine. We need to craft:
- 1 firearm magazine
"""
# Craft a firearm magazine using available materials
crafted_firearm_magazines = craft_item(Prototype.FirearmMagazine, quantity=1)
print(f"Crafted {crafted_firearm_magazines} Firearm Magazine(s)")

# Verify that we have crafted the required number of firearm magazines
firearm_magazines_in_inventory = inspect_inventory().get(Prototype.FirearmMagazine, 0)
assert firearm_magazines_in_inventory >= 1, f"Failed to craft Firearm Magazines. Expected at least 1, but found {firearm_magazines_in_inventory}"
print(f"Successfully crafted {firearm_magazines_in_inventory} Firearm Magazine(s)")


"""
Step 9: Craft transport belt. We need to craft:
- 1 transport belt
"""
# Craft a transport belt using available materials
crafted_transport_belts = craft_item(Prototype.TransportBelt, quantity=1)
print(f"Crafted {crafted_transport_belts} Transport Belt(s)")

# Verify that we have crafted the required number of transport belts
transport_belts_in_inventory = inspect_inventory().get(Prototype.TransportBelt, 0)
assert transport_belts_in_inventory >= 1, f"Failed to craft Transport Belts. Expected at least 1, but found {transport_belts_in_inventory}"
print(f"Successfully crafted {transport_belts_in_inventory} Transport Belt(s)")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final Inventory: {final_inventory}")

print("Successfully completed all crafting steps!")


"""
Step 10: Verify crafted items. We need to check if we have:
- 1 transport belt
- 1 burner inserter
- 1 firearm magazine
"""
# Check for transport belt in inventory
transport_belts_in_inventory = inspect_inventory().get(Prototype.TransportBelt, 0)
assert transport_belts_in_inventory >= 1, f"Transport Belt verification failed. Expected at least 1, but found {transport_belts_in_inventory}"

# Check for burner inserter in inventory
burner_inserters_in_inventory = inspect_inventory().get(Prototype.BurnerInserter, 0)
assert burner_inserters_in_inventory >= 1, f"Burner Inserter verification failed. Expected at least 1, but found {burner_inserters_in_inventory}"

# Check for firearm magazine in inventory
firearm_magazines_in_inventory = inspect_inventory().get(Prototype.FirearmMagazine, 0)
assert firearm_magazines_in_inventory >= 1, f"Firearm Magazine verification failed. Expected at least 1, but found {firearm_magazines_in_inventory}"

print("Successfully verified that all required items are present in the inventory!")


"""
Step 11: Clean up. We need to:
- Extract any remaining resources from the furnace
- Pick up the stone furnace
"""
# Extract any remaining resources from the furnace
extract_item(Prototype.IronPlate, furnace.position, quantity=5)
extract_item(Prototype.Coal, furnace.position, quantity=2)
extract_item(Prototype.IronOre, furnace.position, quantity=5)

# Pick up the stone furnace
pickup_entity(Prototype.StoneFurnace, furnace.position)

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final Inventory: {final_inventory}")

print("Successfully cleaned up and completed the task!")
