from factorio_instance import *

"""
Main Objective: We need to craft 6 firearm magazines. The final success should be checked by looking if the firearm magazines are in inventory
"""



"""
Step 1: Print recipes. We need to print the recipes for the following items:
- Firearm Magazine
- Stone Furnace
- Burner Mining Drill
"""
# Inventory at the start of step {}
#Step Execution

# Get and print the recipe for Firearm Magazine
firearm_magazine_recipe = get_prototype_recipe(Prototype.FirearmMagazine)
print(f"Firearm Magazine Recipe: {firearm_magazine_recipe}")

# Get and print the recipe for Stone Furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace Recipe: {stone_furnace_recipe}")

# Get and print the recipe for Burner Mining Drill
burner_mining_drill_recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
print(f"Burner Mining Drill Recipe: {burner_mining_drill_recipe}")


"""
Step 2: Gather resources. We need to gather the following resources by hand:
- 5 stone for crafting a stone furnace
- 9 iron plates worth of iron ore (18 iron ore) for crafting a burner mining drill
- Additional iron ore for the firearm magazines
"""
# Inventory at the start of step {}
#Step Execution

# Plan:
# We need to gather:
# - Stone: For crafting a stone furnace, we need at least 5 stones
# - Iron Ore: For burner mining drill (18) + Firearm Magazines (48), totaling at least 66

resources_to_gather = [(Resource.Stone, 5), (Resource.IronOre, 66)]

for resource_type, quantity_needed in resources_to_gather:
    # Find nearest position of the resource
    resource_position = nearest(resource_type)
    
    # Move to that position
    move_to(resource_position)
    
    # Harvest the required amount
    harvested_amount = harvest_resource(resource_position, quantity_needed)
    
    # Log current status after harvesting each type of resource
    print(f"Harvested {harvested_amount} units of {resource_type}")
    
    # Verify that enough resources have been gathered
    inventory = inspect_inventory()
    inventory_count = inventory.get(resource_type, 0)
    assert inventory_count >= quantity_needed, f"Failed to gather enough {resource_type}. Expected {quantity_needed}, but got {inventory_count}"

# Print final inventory state
final_inventory = inspect_inventory()
print(f"Final inventory after gathering resources: {final_inventory}")


"""
Step 3: Craft stone furnace. Use the gathered stone to craft a stone furnace.
"""
# Inventory at the start of step {'stone': 5, 'iron-ore': 66}
#Step Execution

# Craft a stone furnace using the gathered stones
craft_item(Prototype.StoneFurnace, 1)

# Check if we have successfully crafted a stone furnace
stone_furnace_count = inspect_inventory()[Prototype.StoneFurnace]
assert stone_furnace_count >= 1, f"Failed to craft a Stone Furnace. Expected at least 1, but got {stone_furnace_count}"
print("Successfully crafted a Stone Furnace.")


"""
Step 4: Smelt iron plates for burner mining drill. We need to:
- Place the stone furnace
- Move to the wooden chest on the map and collect the coal
- Fuel the furnace with coal
- Smelt 9 iron plates using the iron ore gathered earlier
"""
# Inventory at the start of step {'stone-furnace': 1, 'iron-ore': 66}
#Step Execution

# Step 4: Smelt iron plates for burner mining drill

# Place the stone furnace at an appropriate location
furnace_position = Position(x=-11.0, y=19.5) # Example position near where resources were gathered
move_to(furnace_position)
stone_furnace = place_entity(Prototype.StoneFurnace, Direction.UP, furnace_position)
print(f"Placed Stone Furnace at {furnace_position}")

# Move to wooden chest and collect coal
chest_pos = Position(x=-11.5, y=-11.5)
move_to(chest_pos)

# Extract all available coal from wooden chest
wooden_chest = get_entity(Prototype.WoodenChest, chest_pos)
coal_in_chest = inspect_inventory(wooden_chest).get(Prototype.Coal.value[0], 0)
extract_item(Prototype.Coal, wooden_chest.position, quantity=coal_in_chest)
print(f"Extracted {coal_in_chest} units of coal from wooden chest")

# Fuel the stone furnace with extracted coal
stone_furnace = insert_item(Prototype.Coal, stone_furnace, quantity=coal_in_chest)
print("Inserted coal into Stone Furnace.")

# Insert iron ore into stone furnace for smelting
iron_ore_needed_for_smelting = 9 
stone_furnace = insert_item(Prototype.IronOre, stone_furnace, quantity=iron_ore_needed_for_smelting)
print(f"Inserted {iron_ore_needed_for_smelting} units of iron ore into Stone Furnace.")

# Wait for smelting process (approximate time per unit is 0.7 seconds * number of ores)
sleep_time_per_unit = 0.7
total_sleep_time = sleep_time_per_unit * iron_ore_needed_for_smelting
sleep(total_sleep_time)

# Attempt extraction until desired amount is achieved; try multiple times if necessary due to processing delays.
max_attempts_to_extract_plates = 5
for _ in range(max_attempts_to_extract_plates):
    extract_item(Prototype.IronPlate, stone_furnace.position,
                 quantity=iron_ore_needed_for_smelting)  
    current_inventory_count_of_iron_plate = inspect_inventory().get(
        Prototype.IronPlate.value[0], 0)

    if current_inventory_count_of_iron_plate >= iron_ore_needed_for_smelting:
        break

    sleep(sleep_time_per_unit) 

assert current_inventory_count_of_iron_plate >= iron_ore_needed_for_smelting,\
       f"Failed to produce enough Iron Plates! Expected at least {iron_ore_needed_for_smelting}, but got {current_inventory_count_of_iron_plate}"

print("Successfully produced sufficient Iron Plates.")


"""
Step 5: Craft burner mining drill. Use the 9 iron plates to craft a burner mining drill.
"""
# Placeholder 5

"""
Step 6: Set up iron ore mining. We need to:
- Find an iron ore patch
- Place the burner mining drill on the iron ore patch
- Fuel the burner mining drill with remaining coal from the wooden chest
"""
# Placeholder 6

"""
Step 7: Smelt iron plates for firearm magazines. We need to:
- Collect iron ore from the burner mining drill
- Smelt 24 iron plates using the stone furnace
"""
# Placeholder 7

"""
Step 8: Craft firearm magazines. Use the 24 iron plates to craft 6 firearm magazines.
"""
# Placeholder 8

"""
Step 9: Verify success. Check the inventory to ensure we have 6 firearm magazines.
##
"""
# Placeholder 9