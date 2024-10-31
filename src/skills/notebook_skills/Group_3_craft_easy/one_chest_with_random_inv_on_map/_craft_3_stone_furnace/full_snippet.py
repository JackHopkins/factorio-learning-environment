from factorio_instance import *

"""
Main Objective: We need three stone furnaces. The final success should be checked by looking if 3 stone furnaces are in inventory
"""



"""
Step 1: Print recipes. We need to craft stone furnaces and a burner mining drill. Print out the recipes for:
- Stone Furnace
- Burner Mining Drill
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
- 15 stone for the furnaces
- 9 iron plates and 5 stone for the burner mining drill
- Coal for fueling the burner mining drill (already available in the chest)
"""
# Inventory at the start of step {}
#Step Execution

# Define the resources needed
resources_needed = [(Resource.Stone, 20), (Resource.IronOre, 10)]  # Adding extra for inefficiencies

# Loop through each resource type needed
for resource_type, quantity_needed in resources_needed:
    print(f"Gathering {quantity_needed} of {resource_type[0]}.")
    
    # Find the nearest patch of the current resource type
    position_of_resource = nearest(resource_type)
    print(f"Nearest {resource_type[0]} located at: {position_of_resource}")
    
    # Move towards the resource location
    move_to(position_of_resource)
    
    # Harvest the specified amount of this resource
    harvested_amount = harvest_resource(position_of_resource, quantity=quantity_needed)
    
    # Verify if harvesting was successful by checking the harvested amount
    assert harvested_amount >= quantity_needed, f"Failed to gather enough {resource_type[0]}. Needed: {quantity_needed}, but got: {harvested_amount}"
    
    print(f"Successfully gathered {harvested_amount} units of {resource_type[0]}. Current Inventory: {inspect_inventory()}")

# Check if we have enough iron plates (9) after mining iron ore
iron_plates_needed = 9
iron_ore_count = inspect_inventory().get('iron-ore', 0)
assert iron_ore_count >= iron_plates_needed, f"Not enough iron ore to make {iron_plates_needed} iron plates. Current iron ore: {iron_ore_count}"

final_inventory_after_gathering = inspect_inventory()
print(f"Final Inventory after gathering resources: {final_inventory_after_gathering}")

# Since coal is already available in chest as per logs,
# We need to retrieve it from the chest
chest = get_entities({Prototype.WoodenChest})[0]
move_to(chest.position)
extract_item(Prototype.Coal, chest.position, quantity=8)

# Verify that we have coal in our inventory
coal_count = inspect_inventory().get('coal', 0)
assert coal_count == 8, f"Failed to extract coal from chest. Expected 8, but got {coal_count}"

print(f"Final Inventory after gathering all resources: {inspect_inventory()}")


"""
Step 3: Craft burner mining drill. We need to:
- Mine iron ore
- Smelt iron ore into iron plates
- Craft the burner mining drill
"""
# Inventory at the start of step {'coal': 8, 'stone': 20, 'iron-ore': 10}
#Step Execution

# Check current inventory before starting
current_inventory = inspect_inventory()
print(f"Current Inventory at start: {current_inventory}")

# Step 1: Craft Stone Furnace
stone_needed = 5
assert current_inventory.get('stone', 0) >= stone_needed, f"Not enough stone to craft Stone Furnace. Need {stone_needed}, have {current_inventory.get('stone', 0)}"

craft_item(Prototype.StoneFurnace, quantity=1)
stone_furnace_count = inspect_inventory().get('stone-furnace', 0)
assert stone_furnace_count == 1, f"Stone Furnace crafting failed! Expected count: 1 but found: {stone_furnace_count}"
print("Successfully crafted Stone Furnace.")

# Step 2: Place Stone Furnace
stone_furnace_position = Position(x=0, y=0)  # Assuming this position is suitable; adjust as needed
move_to(stone_furnace_position)
stone_furnace = place_entity(Prototype.StoneFurnace, position=stone_furnace_position)
print("Placed Stone Furnace.")

# Step 3: Smelt Iron Ore into Iron Plates
iron_plates_needed = 9
iron_ore_available = current_inventory.get('iron-ore', 0)
assert iron_ore_available >= iron_plates_needed, f"Not enough Iron Ore available! Need {iron_plates_needed}, have {iron_ore_available}"

insert_item(Prototype.Coal, target=stone_furnace, quantity=5)
insert_item(Prototype.IronOre, target=stone_furnace, quantity=iron_plates_needed)

# Wait until all ores are processed 
sleep(15)  # Sleep time may vary depending on game settings 

# Extract resulting iron plates from furnace 
extract_item(Prototype.IronPlate, position=stone_furnace.position, quantity=iron_plates_needed)
print(f"Extracted {iron_plates_needed} Iron Plates.")

# Verify extraction was successful 
extracted_iron_plate_count = inspect_inventory().get('iron-plate', 0)
assert extracted_iron_plate_count >= iron_plates_needed, f"Failed extracting enough Iron Plates! Expected: {iron_plates_needed}, but got: {extracted_iron_plate_count}"

print(f"Iron Plates after extraction: {inspect_inventory()}")

# Step 4: Craft Iron Gear Wheels
iron_gear_wheels_needed = 3
craft_item(Prototype.IronGearWheel, quantity=iron_gear_wheels_needed)
iron_gear_wheel_count = inspect_inventory().get('iron-gear-wheel', 0)
assert iron_gear_wheel_count >= iron_gear_wheels_needed, f"Iron Gear Wheel crafting failed! Expected count: {iron_gear_wheels_needed} but found: {iron_gear_wheel_count}"
print(f"Successfully crafted {iron_gear_wheels_needed} Iron Gear Wheels.")

# Step 5: Craft Burner Mining Drill
craft_item(Prototype.BurnerMiningDrill, quantity=1)

burner_mining_drill_count = inspect_inventory().get('burner-mining-drill', 0)
assert burner_mining_drill_count == 1, f"Burner Mining Drill crafting failed! Expected count: 1 but found: {burner_mining_drill_count}"

print("Successfully crafted Burner Mining Drill.")
print(f"Final Inventory: {inspect_inventory()}")


"""
Step 4: Set up stone mining. We need to:
- Move to a stone patch
- Place the burner mining drill on the stone patch
- Fuel the burner mining drill with coal from the chest on the map
"""
# Placeholder 4

"""
Step 5: Mine stone. We need to:
- Wait for the burner mining drill to mine at least 15 stone
- Collect the mined stone
"""
# Placeholder 5

"""
Step 6: Craft stone furnaces. We need to:
- Use the collected stone to craft 3 stone furnaces
"""
# Placeholder 6

"""
Step 7: Verify success. Check the inventory to ensure we have 3 stone furnaces.
##
"""
# Placeholder 7