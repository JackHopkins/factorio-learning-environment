from factorio_instance import *

"""
Main Objective: We need 12 iron plates. The final success should be checked by looking if the iron plates are in inventory
"""



"""
Step 1: Print recipes. We need to craft a stone furnace and a burner mining drill. Print out the recipes for these items:
- Stone Furnace: 5 stone
- Burner Mining Drill: 3 iron gear wheels, 3 iron plates, 1 stone furnace (total: 9 iron plates, 5 stone)
"""
# Inventory at the start of step {}
#Step Execution

# Get and print the recipe for Stone Furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace Recipe: {stone_furnace_recipe}")

# Get and print the recipe for Burner Mining Drill
burner_mining_drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
print(f"Burner Mining Drill Recipe: {burner_mining_drill_recipe}")


"""
Step 2: Gather resources. We need to gather the following resources:
- 14 stone (5 for furnace, 5 for burner mining drill, 4 extra for smelting)
- 9 iron ore (for crafting burner mining drill)
- 12 iron ore (for the final objective)
- Use the coal from the wooden chest on the map for fuel
"""
# Inventory at the start of step {}
#Step Execution

# Define resource requirements
resources_to_gather = [(Resource.Stone, 14), (Resource.IronOre, 21)]

# Gather each type of resource needed
for resource_type, quantity_needed in resources_to_gather:
    # Find nearest resource position
    resource_position = nearest(resource_type)
    
    # Move to that position
    print(f"Moving to {resource_type[0]} at {resource_position}")
    move_to(resource_position)
    
    # Harvest required amount of resource
    harvested_amount = harvest_resource(resource_position, quantity_needed)
    
    # Assert that we've gathered enough resources
    current_inventory_count = inspect_inventory()[resource_type[0]]
    assert current_inventory_count >= quantity_needed, f"Failed to gather enough {resource_type[0]}. Expected at least {quantity_needed}, but got {current_inventory_count}"
    
    print(f"Successfully gathered {current_inventory_count} units of {resource_type[0]}")

# Now handle collecting coal from the wooden chest

# Get chest entity information using its known position
chest_pos = Position(x=-11.5, y=-11.5)

# Move close to the wooden chest first before extracting items due to proximity requirement 
print(f"Moving near wooden chest located at {chest_pos}")
move_to(chest_pos)

# Extract all available coal from it as fuel source (we know it has 'coal':14)
extracted_coal = extract_item(Prototype.Coal, chest_pos, 14)

assert extracted_coal == True, "Failed extracting coal from Wooden Chest"
print("Successfully collected all available coal from Wooden Chest")

final_inventory_state = inspect_inventory()
print(f"Final inventory after gathering resources: {final_inventory_state}")

# Additional assertions to ensure we have gathered all required resources
assert final_inventory_state['stone'] >= 14, f"Not enough stone gathered. Expected at least 14, but got {final_inventory_state['stone']}"
assert final_inventory_state['iron-ore'] >= 21, f"Not enough iron ore gathered. Expected at least 21, but got {final_inventory_state['iron-ore']}"
assert final_inventory_state['coal'] >= 14, f"Not enough coal collected. Expected at least 14, but got {final_inventory_state['coal']}"


"""
Step 3: Craft initial items. We need to craft the following:
- Craft a stone furnace using 5 stone
- Smelt 9 iron ore into 9 iron plates using the crafted furnace
- Craft 3 iron gear wheels using 6 iron plates
- Craft another stone furnace using 5 stone
- Craft a burner mining drill using 3 iron gear wheels, 3 iron plates, and 1 stone furnace
"""
# Inventory at the start of step {'coal': 14, 'stone': 14, 'iron-ore': 21}
#Step Execution

# Step to craft initial items

# Craft first stone furnace using 5 stone
print("Crafting first Stone Furnace...")
craft_item(Prototype.StoneFurnace, quantity=1)
stone_furnace_count = inspect_inventory()[Prototype.StoneFurnace]
assert stone_furnace_count >= 1, f"Failed to craft first Stone Furnace. Expected at least one, but got {stone_furnace_count}"

# Move near where we'll place the furnace for smelting
furnace_position = nearest(Resource.IronOre)
move_to(furnace_position)

# Place the first crafted stone furnace on map for smelting operation
placed_stone_furnace = place_entity(Prototype.StoneFurnace, position=furnace_position)

# Smelt 9 iron ore into iron plates using placed furnace and some coal as fuel
print("Smelting Iron Ore into Iron Plates...")
insert_item(Prototype.Coal, target=placed_stone_furnace, quantity=2)
insert_item(Prototype.IronOre, target=placed_stone_furnace, quantity=9)

sleep(10)  # Wait for smelting process

# Extract smelted iron plates
for _ in range(10):  # Try extracting for up to 10 times
    smelted_iron_plates = extract_item(Prototype.IronPlate, placed_stone_furnace.position, quantity=9)
    if smelted_iron_plates:
        break
    sleep(1)  # Wait a bit more if extraction failed

assert smelted_iron_plates, "Failed extracting all expected Iron Plates after smelting"

current_inventory_after_smelting = inspect_inventory()
print(f"Inventory after smelting: {current_inventory_after_smelting}")

# Craft three iron gear wheels
print("Crafting Iron Gear Wheels...")
craft_item(Prototype.IronGearWheel, quantity=3)
gear_wheel_count = inspect_inventory()[Prototype.IronGearWheel]
assert gear_wheel_count >= 3, f"Failed crafting expected number of Iron Gear Wheels. Got {gear_wheel_count}"

# Check stone inventory before crafting second furnace
stone_count = inspect_inventory()[Prototype.Stone]
assert stone_count >= 5, f"Not enough stone to craft second furnace. Have {stone_count}, need 5"

# Craft second stone furnace
print("Crafting second Stone Furnace...")
craft_item(Prototype.StoneFurnace)
second_stone_furnace_count = inspect_inventory()[Prototype.StoneFurnace]
assert second_stone_furnace_count >= 1, f"Second Stone Furnace could not be crafted successfully. Expected at least 1, got {second_stone_furnace_count}"

# Construct burner mining drill
print("Constructing Burner Mining Drill...")
craft_item(Prototype.BurnerMiningDrill)
burner_mining_drill_count = inspect_inventory()[Prototype.BurnerMiningDrill]
assert burner_mining_drill_count >= 1, f"Burner Mining Drill was not constructed as intended. Expected at least 1, got {burner_mining_drill_count}"

final_crafting_state = inspect_inventory()
print(f"Final Inventory State Post-Crafting Operations: {final_crafting_state}")


"""
Step 4: Set up mining and smelting. We need to set up a simple mining and smelting operation:
- Find an iron ore patch and place the burner mining drill
- Place the remaining stone furnace next to the burner mining drill
- Fuel both the burner mining drill and the stone furnace with coal from the wooden chest
"""
# Inventory at the start of step {'burner-mining-drill': 1, 'coal': 12, 'stone': 4, 'iron-ore': 12}
#Step Execution

# Step 1: Locate nearest iron ore patch
iron_ore_position = nearest(Resource.IronOre)
print(f"Nearest Iron Ore located at: {iron_ore_position}")

# Step 2: Move close enough to place entities
move_to(iron_ore_position)

# Step 3: Place Burner Mining Drill on/near Iron Ore Patch
print("Placing Burner Mining Drill...")
burner_mining_drill = place_entity(Prototype.BurnerMiningDrill, position=iron_ore_position)
print(f"Burner Mining Drill placed at {burner_mining_drill.position}")

# Step 4: Place Stone Furnace next to Burner Mining Drill
print("Placing Stone Furnace next to Burner Mining Drill...")
stone_furnace = place_entity_next_to(Prototype.StoneFurnace, reference_position=burner_mining_drill.position)
print(f"Stone Furnace placed at {stone_furnace.position}")

# Step 5: Fuel both Burner Mining Drill and Stone Furnace with Coal

# Move closer if needed before inserting items due to proximity requirement 
move_to(burner_mining_drill.position)

# Insert coal into Burner Mining Drill
insert_item(Prototype.Coal, target=burner_mining_drill, quantity=6)
print("Fueled Burner Mining Drill with Coal")

# Insert coal into Stone Furnace
insert_item(Prototype.Coal, target=stone_furnace, quantity=6)
print("Fueled Stone Furnace with Coal")

final_inventory_check = inspect_inventory()
assert final_inventory_check['coal'] == 0 or final_inventory_check['coal'] < 12,\
    f"Coal should have been used for fueling operations; remaining amount unexpected"

print("Successfully set up mining and smelting operation.")


"""
Step 5: Mine and smelt iron plates. We need to mine and smelt 12 iron plates:
- Wait for the burner mining drill to mine 12 iron ore
- Transfer the iron ore from the burner mining drill to the stone furnace
- Wait for the stone furnace to smelt 12 iron plates
"""
# Placeholder 5

"""
Step 6: Collect iron plates. We need to collect the 12 iron plates:
- Move to the stone furnace
- Collect all 12 iron plates from the furnace into the inventory
"""
# Placeholder 6

"""
Step 7: Verify success. Check if there are 12 iron plates in the inventory.
##
"""
# Placeholder 7