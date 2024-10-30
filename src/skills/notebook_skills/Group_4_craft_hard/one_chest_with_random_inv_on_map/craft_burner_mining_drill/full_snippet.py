from factorio_instance import *

"""
Main Objective: We require one BurnerMiningDrill. The final success should be checked by looking if a BurnerMiningDrill is in inventory
"""



"""
Step 1: Print recipes. We need to craft a BurnerMiningDrill. We must print the recipes of all the items we need to craft:
- BurnerMiningDrill
- IronGearWheel
- StoneFurnace
- IronPlate
"""
# Inventory at the start of step {}
#Step Execution

# Print recipes for required items

# 1. BurnerMiningDrill recipe
burner_drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
print("BurnerMiningDrill Recipe:")
print(f"Ingredients: {burner_drill_recipe.ingredients}")
print(f"Energy required: {burner_drill_recipe.energy}")
print(f"Category: {burner_drill_recipe.category}")
print()

# 2. IronGearWheel recipe
iron_gear_recipe = get_prototype_recipe(Prototype.IronGearWheel)
print("IronGearWheel Recipe:")
print(f"Ingredients: {iron_gear_recipe.ingredients}")
print(f"Energy required: {iron_gear_recipe.energy}")
print(f"Category: {iron_gear_recipe.category}")
print()

# 3. StoneFurnace recipe
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print("StoneFurnace Recipe:")
print(f"Ingredients: {stone_furnace_recipe.ingredients}")
print(f"Energy required: {stone_furnace_recipe.energy}")
print(f"Category: {stone_furnace_recipe.category}")
print()

# 4. IronPlate recipe
iron_plate_recipe = get_prototype_recipe(Prototype.IronPlate)
print("IronPlate Recipe:")
print(f"Ingredients: {iron_plate_recipe.ingredients}")
print(f"Energy required: {iron_plate_recipe.energy}")
print(f"Category: {iron_plate_recipe.category}")
print()

# Summary of required raw materials
print("Summary of required raw materials:")
print(f"Iron Ore: {9 + 6}")  # 9 for BurnerMiningDrill, 6 for IronGearWheel
print(f"Stone: {5}")  # 5 for StoneFurnace
print("Coal: Some for fueling the furnace")

# Assert to ensure we have all the necessary recipes
assert burner_drill_recipe and iron_gear_recipe and stone_furnace_recipe and iron_plate_recipe, "Failed to retrieve all required recipes"

print("Successfully retrieved and printed all required recipes.")


"""
Step 2: Gather resources. We need to gather the following resources:
- 9 iron ore (for 9 iron plates)
- 5 stone (for the stone furnace)
- Coal for fueling the furnace
"""
# Inventory at the start of step {}
#Step Execution

# Define the resources we need to gather
resources_needed = [
    (Resource.IronOre, 12),  # 9 + 3 extra for safety
    (Resource.Stone, 7),     # 5 + 2 extra for safety
    (Resource.Coal, 10)      # 10 for fueling
]

# Loop through each resource and gather it
for resource, amount in resources_needed:
    # Find the nearest patch of the resource
    resource_position = nearest(resource)
    print(f"Found {resource} at {resource_position}")

    # Move to the resource
    move_to(resource_position)
    print(f"Moved to {resource} at {resource_position}")

    # Harvest the resource
    harvested = harvest_resource(resource_position, amount)
    print(f"Harvested {harvested} {resource}")

    # Check if we have enough of the resource
    inventory = inspect_inventory()
    actual_amount = inventory.get(resource, 0)
    assert actual_amount >= amount, f"Failed to gather enough {resource}. Expected at least {amount}, but got {actual_amount}"
    print(f"Successfully gathered {actual_amount} {resource}")

# Print the final inventory
final_inventory = inspect_inventory()
print("Final inventory after gathering resources:")
print(final_inventory)

# Final assertions to ensure we have all required resources
assert final_inventory.get(Resource.IronOre, 0) >= 9, "Not enough iron ore gathered"
assert final_inventory.get(Resource.Stone, 0) >= 5, "Not enough stone gathered"
assert final_inventory.get(Resource.Coal, 0) >= 10, "Not enough coal gathered"

print("Successfully gathered all required resources!")


"""
Step 3: Smelt iron plates. We need to craft a stone furnace and use it to smelt iron ore into iron plates:
- Craft a stone furnace using 5 stone
- Place the stone furnace and fuel it with coal
- Smelt 9 iron ore into 9 iron plates
"""
# Inventory at the start of step {'coal': 10, 'stone': 7, 'iron-ore': 12}
#Step Execution

# Step 3: Smelt iron plates

# 1. Craft a stone furnace
print("Crafting stone furnace...")
crafted = craft_item(Prototype.StoneFurnace, 1)
assert crafted == 1, f"Failed to craft stone furnace. Crafted: {crafted}"
print("Stone furnace crafted successfully.")

# 2. Find a suitable location to place the stone furnace
furnace_position = Position(x=0, y=0)  # Starting position
print(f"Placing stone furnace at {furnace_position}")

# 3. Place the stone furnace
move_to(furnace_position)
furnace = place_entity(Prototype.StoneFurnace, Direction.UP, furnace_position)
print(f"Stone furnace placed at {furnace.position}")

# 4. Fuel the stone furnace with coal
coal_to_insert = 5  # Insert 5 coal for now
print(f"Inserting {coal_to_insert} coal into the furnace")
furnace = insert_item(Prototype.Coal, furnace, coal_to_insert)
print("Coal inserted successfully")

# 5. Insert iron ore into the furnace
iron_ore_to_smelt = 9
print(f"Inserting {iron_ore_to_smelt} iron ore into the furnace")
furnace = insert_item(Prototype.IronOre, furnace, iron_ore_to_smelt)
print("Iron ore inserted successfully")

# 6. Wait for the smelting process to complete and extract plates
max_attempts = 20
smelting_time = 3.2  # Base smelting time for one iron plate
total_iron_plates = 0

for attempt in range(max_attempts):
    print(f"Smelting attempt {attempt + 1}")
    
    # Wait for smelting
    sleep(smelting_time)
    
    # Move close to the furnace
    move_to(furnace.position)
    
    # Update furnace entity
    furnace = get_entity(Prototype.StoneFurnace, furnace.position)
    
    # Check furnace status and contents
    if furnace.status == EntityStatus.NO_FUEL:
        print("Furnace needs more fuel. Adding coal.")
        furnace = insert_item(Prototype.Coal, furnace, 2)
        continue
    
    # Check if there are iron plates in the furnace
    iron_plates_in_furnace = furnace.furnace_result.get(Prototype.IronPlate, 0)
    if iron_plates_in_furnace > 0:
        # Extract plates
        extracted = extract_item(Prototype.IronPlate, furnace.position, iron_plates_in_furnace)
        total_iron_plates += extracted
        print(f"Extracted {extracted} iron plates. Total: {total_iron_plates}")
    else:
        print("No iron plates ready yet. Waiting...")
    
    # Check if we have enough plates
    if total_iron_plates >= iron_ore_to_smelt:
        break

# 7. Verify that we have the required number of iron plates
inventory = inspect_inventory()
iron_plates_in_inventory = inventory.get(Prototype.IronPlate, 0)
print(f"Iron plates in inventory: {iron_plates_in_inventory}")

assert iron_plates_in_inventory >= iron_ore_to_smelt, f"Failed to smelt enough iron plates. Expected at least {iron_ore_to_smelt}, but got {iron_plates_in_inventory}"

print("Successfully smelted iron plates!")
print(f"Final inventory: {inspect_inventory()}")


"""
Step 4: Craft components. We need to craft the following components:
- 3 iron gear wheels (using 6 iron plates)
- 1 stone furnace (using 5 stone)
"""
# Inventory at the start of step {'coal': 5, 'stone': 2, 'iron-ore': 3, 'iron-plate': 9}
#Step Execution

# Step 4: Craft components

# First, let's check our current inventory
current_inventory = inspect_inventory()
print(f"Current inventory: {current_inventory}")

# Check if we have enough iron plates for 3 iron gear wheels
iron_plates = current_inventory.get(Prototype.IronPlate, 0)
if iron_plates < 6:
    print(f"Not enough iron plates. Have {iron_plates}, need 6.")
    assert False, f"Insufficient iron plates to craft iron gear wheels. Have {iron_plates}, need 6."

# Craft 3 iron gear wheels
print("Crafting 3 iron gear wheels...")
for _ in range(3):
    craft_item(Prototype.IronGearWheel, 1)

# Check if we have 3 iron gear wheels
current_inventory = inspect_inventory()  # Update inventory after crafting
gear_wheels = current_inventory.get(Prototype.IronGearWheel, 0)
assert gear_wheels >= 3, f"Failed to craft 3 iron gear wheels. Only have {gear_wheels}"
print(f"Successfully crafted 3 iron gear wheels. Total: {gear_wheels}")

# Check if we have enough stone for the furnace
stone_count = current_inventory.get(Prototype.Stone, 0)
if stone_count < 5:
    stone_needed = 5 - stone_count
    print(f"Not enough stone. Need {stone_needed} more. Gathering stone...")
    
    # Find nearest stone patch
    stone_position = nearest(Resource.Stone)
    
    # Move to stone patch
    move_to(stone_position)
    
    # Harvest stone
    harvested = harvest_resource(stone_position, stone_needed)
    print(f"Harvested {harvested} stone")
    
    # Update stone count
    current_inventory = inspect_inventory()
    stone_count = current_inventory.get(Prototype.Stone, 0)
    assert stone_count >= 5, f"Failed to gather enough stone. Only have {stone_count}"

# Craft 1 stone furnace
print("Crafting 1 stone furnace...")
craft_item(Prototype.StoneFurnace, 1)

# Check if we have 1 stone furnace
current_inventory = inspect_inventory()
furnace_count = current_inventory.get(Prototype.StoneFurnace, 0)
assert furnace_count >= 1, f"Failed to craft stone furnace. Only have {furnace_count}"
print(f"Successfully crafted 1 stone furnace. Total: {furnace_count}")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory after crafting components: {final_inventory}")

# Final assertions
assert final_inventory.get(Prototype.IronGearWheel, 0) >= 3, "Not enough iron gear wheels"
assert final_inventory.get(Prototype.StoneFurnace, 0) >= 1, "Not enough stone furnaces"

print("Successfully crafted all required components!")


"""
Step 5: Craft BurnerMiningDrill. We need to craft the BurnerMiningDrill using:
- 3 iron gear wheels
- 3 iron plates
- 1 stone furnace
After crafting, check the inventory to confirm that a BurnerMiningDrill is present.
##
"""
# Inventory at the start of step {'stone-furnace': 1, 'coal': 5, 'iron-ore': 3, 'iron-plate': 3, 'iron-gear-wheel': 3}
#Step Execution

# Step 5: Craft BurnerMiningDrill

# Check current inventory
current_inventory = inspect_inventory()
print(f"Current inventory: {current_inventory}")

# Check if we have all required components
iron_gear_wheels = current_inventory.get(Prototype.IronGearWheel, 0)
iron_plates = current_inventory.get(Prototype.IronPlate, 0)
stone_furnaces = current_inventory.get(Prototype.StoneFurnace, 0)

print(f"Iron Gear Wheels: {iron_gear_wheels}")
print(f"Iron Plates: {iron_plates}")
print(f"Stone Furnaces: {stone_furnaces}")

# If we don't have enough components, craft or gather more
if iron_gear_wheels < 3:
    craft_count = 3 - iron_gear_wheels
    print(f"Crafting {craft_count} more Iron Gear Wheels")
    craft_item(Prototype.IronGearWheel, craft_count)

if iron_plates < 3:
    # We need to smelt more iron ore
    iron_ore_needed = 3 - iron_plates
    print(f"Need to smelt {iron_ore_needed} more Iron Plates")
    
    # Check if we have enough iron ore
    if current_inventory.get(Prototype.IronOre, 0) < iron_ore_needed:
        iron_ore_to_mine = iron_ore_needed - current_inventory.get(Prototype.IronOre, 0)
        print(f"Mining {iron_ore_to_mine} Iron Ore")
        iron_ore_position = nearest(Resource.IronOre)
        move_to(iron_ore_position)
        harvest_resource(iron_ore_position, iron_ore_to_mine)
    
    # Smelt the iron ore
    furnace = get_entities(set([Prototype.StoneFurnace]))[0]
    move_to(furnace.position)
    insert_item(Prototype.IronOre, furnace, iron_ore_needed)
    insert_item(Prototype.Coal, furnace, 1)  # Add some coal for fuel
    
    # Wait for smelting to complete
    sleep(5)  # Adjust this time based on smelting duration
    
    # Extract the iron plates
    extract_item(Prototype.IronPlate, furnace.position, iron_ore_needed)

if stone_furnaces < 1:
    print("Crafting 1 Stone Furnace")
    craft_item(Prototype.StoneFurnace, 1)

# Now we should have all the components, let's craft the BurnerMiningDrill
print("Crafting BurnerMiningDrill")
craft_item(Prototype.BurnerMiningDrill, 1)

# Check if BurnerMiningDrill is in the inventory
final_inventory = inspect_inventory()
burner_drill_count = final_inventory.get(Prototype.BurnerMiningDrill, 0)

print(f"Final inventory: {final_inventory}")
assert burner_drill_count >= 1, f"Failed to craft BurnerMiningDrill. Expected at least 1, but got {burner_drill_count}"

print("Successfully crafted BurnerMiningDrill!")
