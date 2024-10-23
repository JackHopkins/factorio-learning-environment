from factorio_instance import *

"""
Main Objective: We need to craft 4 automation science packs. The final success should be checked by looking if the automation science packs are in inventory
"""



"""
Step 1: Print recipes and gather resources. We need to print the recipe for automation science packs and gather the necessary resources. We'll need to:
- Print the recipe for Automation Science Pack
- Mine iron ore (at least 12 for 4 iron gear wheels and 4 copper plates)
- Mine copper ore (at least 4 for 4 copper plates)
- Mine coal (for fueling the furnace)
- Mine stone (for crafting a stone furnace)
"""
# Inventory at the start of step {}
#Step Execution

# Print the recipe for Automation Science Pack
automation_science_pack_recipe = get_prototype_recipe(Prototype.AutomationSciencePack)
print(f"Recipe for Automation Science Pack: {automation_science_pack_recipe}")

# Define the required resources
required_resources = [
    (Resource.IronOre, 12),
    (Resource.CopperOre, 4),
    (Resource.Coal, 10),
    (Resource.Stone, 5)
]

# Gather resources
for resource, amount in required_resources:
    resource_position = nearest(resource)
    print(f"Moving to {resource} at position {resource_position}")
    move_to(resource_position)
    
    print(f"Harvesting {amount} {resource}")
    harvested = harvest_resource(resource_position, amount)
    print(f"Harvested {harvested} {resource}")
    
    # Verify that we harvested the required amount
    inventory = inspect_inventory()
    actual_amount = inventory.get(resource, 0)
    print(f"Current inventory of {resource}: {actual_amount}")
    assert actual_amount >= amount, f"Failed to harvest enough {resource}. Required: {amount}, Actual: {actual_amount}"

# Print final inventory
final_inventory = inspect_inventory()
print(f"Final inventory after gathering resources: {final_inventory}")

# Verify that we have all required resources
for resource, amount in required_resources:
    actual_amount = final_inventory.get(resource, 0)
    assert actual_amount >= amount, f"Missing required {resource}. Required: {amount}, Actual: {actual_amount}"

print("Successfully gathered all required resources for crafting Automation Science Packs")


"""
Step 2: Craft and set up smelting. We need to craft a stone furnace and use it to smelt the iron and copper ore into plates. We'll:
- Craft a stone furnace
- Place the stone furnace
- Fuel the furnace with coal
- Smelt iron ore into iron plates
- Smelt copper ore into copper plates
"""
# Inventory at the start of step {'coal': 10, 'stone': 5, 'iron-ore': 12, 'copper-ore': 4}
#Step Execution

# Craft a stone furnace
craft_item(Prototype.StoneFurnace, 1)
print("Crafted a stone furnace")

# Find a suitable location to place the furnace (near coal for easy refueling)
coal_position = nearest(Resource.Coal)
furnace_position = Position(x=coal_position.x + 2, y=coal_position.y)

# Move to the placement location
move_to(furnace_position)

# Place the stone furnace
furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)
print(f"Placed stone furnace at {furnace_position}")

# Fuel the furnace with coal
coal_to_insert = 5  # Insert more coal than necessary
furnace = insert_item(Prototype.Coal, furnace, coal_to_insert)
print(f"Inserted {coal_to_insert} coal into the furnace")

# Function to smelt ore and extract plates
def smelt_and_extract(furnace, ore_prototype, plate_prototype, amount):
    # Insert ore into the furnace
    furnace = insert_item(ore_prototype, furnace, amount)
    print(f"Inserted {amount} {ore_prototype.value[0]} into the furnace")

    # Wait for smelting to complete (3.2 seconds per ore)
    sleep(amount * 3.2)

    # Extract plates
    extract_item(plate_prototype, furnace.position, amount)
    print(f"Extracted {amount} {plate_prototype.value[0]} from the furnace")

    # Verify extraction
    plates_in_inventory = inspect_inventory()[plate_prototype]
    assert plates_in_inventory >= amount, f"Failed to extract enough {plate_prototype.value[0]}. Expected at least {amount}, but got {plates_in_inventory}"

    return furnace

# Smelt iron ore into iron plates
furnace = smelt_and_extract(furnace, Prototype.IronOre, Prototype.IronPlate, 12)

# Smelt copper ore into copper plates
furnace = smelt_and_extract(furnace, Prototype.CopperOre, Prototype.CopperPlate, 4)

# Print final inventory
final_inventory = inspect_inventory()
print(f"Final inventory after smelting: {final_inventory}")

# Verify that we have the required plates
assert final_inventory[Prototype.IronPlate] >= 12, f"Not enough iron plates. Expected at least 12, but got {final_inventory[Prototype.IronPlate]}"
assert final_inventory[Prototype.CopperPlate] >= 4, f"Not enough copper plates. Expected at least 4, but got {final_inventory[Prototype.CopperPlate]}"

print("Successfully crafted and set up smelting, produced required iron and copper plates")


"""
Step 3: Craft components. We need to craft the iron gear wheels required for the automation science packs:
- Craft 4 iron gear wheels using 8 iron plates
"""
# Inventory at the start of step {'coal': 5, 'iron-plate': 12, 'copper-plate': 4}
#Step Execution

# Craft 4 iron gear wheels
print("Crafting 4 iron gear wheels...")
craft_item(Prototype.IronGearWheel, 4)

# Check the inventory after crafting
inventory = inspect_inventory()
iron_gear_wheels = inventory.get(Prototype.IronGearWheel, 0)
remaining_iron_plates = inventory.get(Prototype.IronPlate, 0)

print(f"Crafted iron gear wheels: {iron_gear_wheels}")
print(f"Remaining iron plates: {remaining_iron_plates}")

# Verify that we have crafted the correct number of iron gear wheels
assert iron_gear_wheels >= 4, f"Failed to craft enough iron gear wheels. Expected at least 4, but got {iron_gear_wheels}"

# Verify that we have used the correct number of iron plates
expected_remaining_iron_plates = 12 - (4 * 2)  # We started with 12 and used 8
assert remaining_iron_plates == expected_remaining_iron_plates, f"Unexpected number of remaining iron plates. Expected {expected_remaining_iron_plates}, but got {remaining_iron_plates}"

print("Successfully crafted 4 iron gear wheels")

# Print the final inventory for this step
print(f"Final inventory after crafting iron gear wheels: {inventory}")


"""
Step 4: Craft automation science packs. We'll use the crafted components and smelted plates to make the science packs:
- Craft 4 automation science packs using 4 copper plates and 4 iron gear wheels
"""
# Inventory at the start of step {'coal': 5, 'iron-plate': 4, 'copper-plate': 4, 'iron-gear-wheel': 4}
#Step Execution

# Craft 4 automation science packs
print("Crafting 4 automation science packs...")
craft_item(Prototype.AutomationSciencePack, 4)

# Check the inventory after crafting
inventory = inspect_inventory()
automation_science_packs = inventory.get(Prototype.AutomationSciencePack, 0)
remaining_copper_plates = inventory.get(Prototype.CopperPlate, 0)
remaining_iron_gear_wheels = inventory.get(Prototype.IronGearWheel, 0)

print(f"Crafted automation science packs: {automation_science_packs}")
print(f"Remaining copper plates: {remaining_copper_plates}")
print(f"Remaining iron gear wheels: {remaining_iron_gear_wheels}")

# Verify that we have crafted the correct number of automation science packs
assert automation_science_packs >= 4, f"Failed to craft enough automation science packs. Expected at least 4, but got {automation_science_packs}"

# Verify that we have used the correct number of copper plates and iron gear wheels
assert remaining_copper_plates == 0, f"Unexpected number of remaining copper plates. Expected 0, but got {remaining_copper_plates}"
assert remaining_iron_gear_wheels == 0, f"Unexpected number of remaining iron gear wheels. Expected 0, but got {remaining_iron_gear_wheels}"

print("Successfully crafted 4 automation science packs")

# Print the final inventory for this step
print(f"Final inventory after crafting automation science packs: {inventory}")


"""
Step 5: Verify success. We need to check if the crafting was successful:
- Check the inventory to confirm that 4 automation science packs are present
##
"""
# Inventory at the start of step {'coal': 5, 'iron-plate': 4, 'automation-science-pack': 4}
#Step Execution

# Check the inventory to confirm that 4 automation science packs are present
inventory = inspect_inventory()
print(f"Final inventory: {inventory}")

# Verify the number of automation science packs
automation_science_packs = inventory.get(Prototype.AutomationSciencePack, 0)
assert automation_science_packs >= 4, f"Failed to craft enough automation science packs. Expected at least 4, but got {automation_science_packs}"

# Verify that we have used all necessary resources
remaining_copper_plates = inventory.get(Prototype.CopperPlate, 0)
remaining_iron_gear_wheels = inventory.get(Prototype.IronGearWheel, 0)
assert remaining_copper_plates == 0, f"Unexpected number of remaining copper plates. Expected 0, but got {remaining_copper_plates}"
assert remaining_iron_gear_wheels == 0, f"Unexpected number of remaining iron gear wheels. Expected 0, but got {remaining_iron_gear_wheels}"

# Check if we have any leftover iron plates (which is fine)
remaining_iron_plates = inventory.get(Prototype.IronPlate, 0)
print(f"Remaining iron plates: {remaining_iron_plates}")

# Print success message
print("Successfully crafted 4 automation science packs!")
print("Main objective achieved: We have crafted 4 automation science packs.")
