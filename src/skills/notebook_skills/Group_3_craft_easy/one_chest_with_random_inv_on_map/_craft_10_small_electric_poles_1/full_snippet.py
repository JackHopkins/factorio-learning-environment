from factorio_instance import *

"""
Main Objective: We need to craft 4 small electric poles. The final success should be checked by looking if the small electric poles are in inventory
"""



"""
Step 1: Print recipes. We need to print the recipes for small electric poles and copper cables.
"""
# Inventory at the start of step {}
#Step Execution

# Get and print the recipe for small electric poles
small_electric_pole_recipe = get_prototype_recipe(Prototype.SmallElectricPole)
print(f"Small Electric Pole Recipe: {small_electric_pole_recipe}")

# Get and print the recipe for copper cables
copper_cable_recipe = get_prototype_recipe(Prototype.CopperCable)
print(f"Copper Cable Recipe: {copper_cable_recipe}")


"""
Step 2: Gather resources. We need to gather the following resources:
- Mine copper ore (at least 2 copper ore for 2 copper plates)
- Gather wood (at least 2 wood)
- Mine coal for fuel (at least 5 coal)
- Mine stone for a furnace (at least 5 stone)
"""
# Inventory at the start of step {}
#Step Execution

# Define required amounts of resources
resources_needed = {
    Resource.CopperOre: 3,
    Resource.Coal: 6,
    Resource.Stone: 5,
    Resource.Wood: 3  # Include wood in the main dictionary
}

# Function to harvest a specific resource
def harvest_specific_resource(resource_type, amount):
    print(f"Gathering {resource_type}...")
    
    # Find nearest position of the given resource type
    resource_position = nearest(resource_type)
    
    # Move towards the resource position
    move_to(resource_position)
    
    # Harvest specified amount of this resource type
    harvested_amount = harvest_resource(resource_position, amount)
    
    # Assert if enough was harvested
    assert harvested_amount >= amount, f"Failed to gather enough {resource_type}. Needed {amount}, but got {harvested_amount}"
    
    print(f"Successfully gathered {harvested_amount} units of {resource_type}")

# Harvest all required resources one by one
for resource, amount in resources_needed.items():
    harvest_specific_resource(resource, amount)

# Verify the gathered resources
inventory = inspect_inventory()
print("All necessary resources have been gathered.")
print(f"Current Inventory after gathering: {inventory}")

for resource, amount in resources_needed.items():
    assert inventory[resource] >= amount, f"Not enough {resource} in inventory. Expected at least {amount}, but got {inventory[resource]}"

print("All resources verified successfully.")


"""
Step 3: Craft and place furnace. We need to craft a stone furnace and place it down:
- Craft a stone furnace using 5 stone
- Move to a suitable location and place the stone furnace
- Fuel the furnace with coal
"""
# Inventory at the start of step {'wood': 3, 'coal': 6, 'stone': 5, 'copper-ore': 3}
#Step Execution

# Step 3: Craft and place furnace

# Craft a stone furnace using 5 stones
print("Crafting a stone furnace...")
craft_item(Prototype.StoneFurnace, 1)

# Check if the stone furnace was crafted successfully
furnace_count = inspect_inventory().get(Prototype.StoneFurnace, 0)
assert furnace_count >= 1, f"Failed to craft stone furnace. Expected at least 1, but got {furnace_count}"
print(f"Successfully crafted {furnace_count} stone furnaces")

# Calculate position for the furnace (2 units right of the wooden chest)
chest_position = Position(x=-11.5, y=-11.5)
furnace_position = Position(x=chest_position.x + 2, y=chest_position.y)

# Move to the calculated furnace position
move_to(furnace_position)

# Place the stone furnace at this location
stone_furnace = place_entity(Prototype.StoneFurnace, Direction.UP, furnace_position)

# Verify that the furnace was placed successfully
placed_furnaces = get_entities({Prototype.StoneFurnace})
assert len(placed_furnaces) > 0, "Failed to place the stone furnace"
stone_furnace = placed_furnaces[0]
print(f"Stone furnace placed at position: {stone_furnace.position}")

# Fuel the newly placed stone furnace with coal
coal_amount = min(inspect_inventory().get(Prototype.Coal, 0), 5)  # Use up to 5 coal
if coal_amount > 0:
    print(f"Inserting {coal_amount} units of coal into the stone furnace")
    insert_item(Prototype.Coal, stone_furnace, quantity=coal_amount)
    print("Stone Furnace has been fueled.")
else:
    print("Warning: No coal available to fuel the furnace.")

print("Stone Furnace has been placed and fueled.")


"""
Step 4: Smelt copper plates. We need to smelt copper ore into copper plates:
- Put copper ore into the furnace
- Wait for the copper plates to be produced
- Collect the copper plates from the furnace
"""
# Inventory at the start of step {'wood': 3, 'coal': 1, 'copper-ore': 3}
#Step Execution

# Get current inventory status
inventory = inspect_inventory()
copper_ore_in_inventory = inventory.get(Prototype.CopperOre, 0)
print(f"Copper ore in inventory before smelting: {copper_ore_in_inventory}")

# Check if there is enough copper ore to smelt
assert copper_ore_in_inventory > 0, "No copper ore available to smelt."

# Insert the copper ore into the stone furnace
stone_furnace_position = Position(x=-10.0, y=-12.0) # Known position of our stone furnace
move_to(stone_furnace_position)

# Re-fetching the stone furnace entity after moving close by
stone_furnace = get_entity(Prototype.StoneFurnace, stone_furnace_position)
insert_item(Prototype.CopperOre, stone_furnace, quantity=copper_ore_in_inventory)
print(f"Inserted {copper_ore_in_inventory} units of copper ore into the furnace.")

# Calculate expected number of copper plates (same as input number since 1-to-1 conversion)
expected_copper_plates = inventory.get(Prototype.CopperPlate, 0) + copper_ore_in_inventory

# Wait for smelting process (approximately 3 seconds per batch of ores)
smelting_time_per_batch = 3  
sleep(copper_ore_in_inventory * smelting_time_per_batch)

# Extract produced copper plates from the furnace
extract_item(Prototype.CopperPlate, stone_furnace.position, quantity=copper_ore_in_inventory)

# Verify extraction success by checking updated inventory count
current_copper_plate_count = inspect_inventory().get(Prototype.CopperPlate, 0)
assert current_copper_plate_count >= expected_copper_plates,\
    f"Failed to extract enough Copper Plates. Expected at least {expected_copper_plates}, but got {current_copper_plate_count}"

print(f"Successfully extracted {current_copper_plate_count - (expected_copper_plates - copper_ore_in_inventory)} new Copper Plates.")
print(f"Current Inventory after extracting: {inspect_inventory()}")


"""
Step 5: Craft copper cables. We need to craft copper cables:
- Craft 4 copper cables using 2 copper plates (each craft produces 2 cables)
"""
# Inventory at the start of step {'wood': 3, 'coal': 1, 'copper-plate': 3}
#Step Execution

# Crafting Copper Cables

# Define how many crafts are needed; each craft yields 2 units
copper_cable_needed = 4
copper_plate_per_craft = get_prototype_recipe(Prototype.CopperCable).ingredients[0].count
crafts_required = int(copper_cable_needed / (copper_plate_per_craft * 2))

print(f"Initiating crafting of {crafts_required} batches of Copper Cables...")

# Perform the crafting process
for _ in range(crafts_required):
    # Craft one batch of Copper Cables
    crafted_count = craft_item(Prototype.CopperCable, quantity=1)
    
    # Assert if successful (it should always succeed given enough resources)
    assert crafted_count == 1, f"Failed to craft Copper Cable batch."

print("Copper Cable crafting complete.")

# Verify final count of Copper Cables in inventory
final_inventory = inspect_inventory()
copper_cable_count = final_inventory.get(Prototype.CopperCable, 0)

assert copper_cable_count >= copper_cable_needed, \
    f"Copper Cable count insufficient after crafting. Expected at least {copper_cable_needed}, but got {copper_cable_count}"

print(f"Successfully crafted {copper_cable_count} Copper Cables.")
print(f"Current Inventory after crafting: {final_inventory}")


"""
Step 6: Craft small electric poles. We need to craft the small electric poles:
- Craft 4 small electric poles using 4 copper cables and 2 wood
"""
# Inventory at the start of step {'wood': 3, 'coal': 1, 'copper-plate': 1, 'copper-cable': 4}
#Step Execution

def gather_missing_resources():
    current_inventory = inspect_inventory()
    print(f"Current Inventory before gathering missing resources: {current_inventory}")

    resources_needed = {
        Resource.Wood: max(0, 4 - current_inventory.get('wood', 0)),
        Resource.CopperOre: max(0, 4 - current_inventory.get('copper-ore', 0) - current_inventory.get('copper-plate', 0))
    }

    for resource, amount in resources_needed.items():
        if amount > 0:
            print(f"Gathering {amount} more units of {resource}...")
            resource_position = nearest(resource)
            move_to(resource_position)
            harvested_amount = harvest_resource(resource_position, amount)
            assert harvested_amount >= amount, f"Failed to gather enough {resource}. Needed {amount}, but got {harvested_amount}"
            print(f"Successfully gathered additional {harvested_amount} units of {resource}")

    print(f"Inventory after gathering missing resources: {inspect_inventory()}")

gather_missing_resources()

# Smelt copper ore into copper plates
furnace = get_entities({Prototype.StoneFurnace})[0]
copper_ore_count = inspect_inventory().get('copper-ore', 0)
if copper_ore_count > 0:
    move_to(furnace.position)
    insert_item(Prototype.CopperOre, furnace, quantity=copper_ore_count)
    print(f"Inserted {copper_ore_count} copper ore into the furnace")
    sleep(copper_ore_count * 3)  # Wait for smelting (3 seconds per ore)
    extract_item(Prototype.CopperPlate, furnace.position, quantity=copper_ore_count)
    print(f"Extracted {copper_ore_count} copper plates from the furnace")

# Craft copper cables
copper_plate_count = inspect_inventory().get('copper-plate', 0)
copper_cable_to_craft = max(0, 8 - inspect_inventory().get('copper-cable', 0))
copper_cable_crafts = min(copper_plate_count, copper_cable_to_craft // 2)
for _ in range(copper_cable_crafts):
    craft_item(Prototype.CopperCable, quantity=1)
print(f"Crafted {copper_cable_crafts * 2} copper cables")

# Craft Small Electric Poles
small_electric_poles_to_craft = 4
for _ in range(small_electric_poles_to_craft):
    crafted_count = craft_item(Prototype.SmallElectricPole, quantity=1)
    assert crafted_count == 1, "Failed to craft a Small Electric Pole."
    print("Crafted a Small Electric Pole.")

final_inventory_check = inspect_inventory()
small_electric_pole_count = final_inventory_check.get(Prototype.SmallElectricPole, 0)
assert small_electric_pole_count >= small_electric_poles_to_craft,\
       f"Small Electric Poles count insufficient after crafting. Expected at least {small_electric_poles_to_craft}, but got {small_electric_pole_count}"

print(f"Successfully crafted {small_electric_pole_count} Small Electric Poles.")
print(f"Final Inventory after crafting: {final_inventory_check}")


"""
Step 7: Store crafted items. We need to store the crafted small electric poles in the existing chest:
- Move to the wooden chest at position (-11.5, -11.5)
- Put the 4 small electric poles into the chest
"""
# Placeholder 7

"""
Step 8: Verify success. We need to check if the small electric poles are in the inventory:
- Check the contents of the wooden chest for 4 small electric poles
##
"""
# Placeholder 8