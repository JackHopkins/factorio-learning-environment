from factorio_instance import *

"""
Main Objective: We need to craft 6 firearm magazines. The final success should be checked by looking if the firearm magazines are in inventory
"""



"""
Step 1: Print recipes. We need to craft firearm magazines and a stone furnace. Print out the recipes:
- FirearmMagazine - Crafting requires 4 iron plates
- StoneFurnace - Crafting requires 5 stone
"""
# Inventory at the start of step {}
#Step Execution

# Get and print the recipe for Firearm Magazine
firearm_magazine_recipe = get_prototype_recipe(Prototype.FirearmMagazine)
print(f"Firearm Magazine Recipe: {firearm_magazine_recipe}")

# Get and print the recipe for Stone Furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print(f"Stone Furnace Recipe: {stone_furnace_recipe}")


"""
Step 2: Gather resources. We need to gather the following resources:
- Mine 5 stone for the stone furnace
- Mine 4 additional iron ore (we have 20 in the chest, need 24 total)
- Mine some coal for fuel (at least 10)
"""
# Inventory at the start of step {}
#Step Execution

# Define required resources and their quantities
required_resources = [(Resource.Stone, 5), (Resource.IronOre, 4), (Resource.Coal, 10)]

# Loop through each required resource
for resource_type, amount_needed in required_resources:
    # Find the nearest position of this resource type
    print(f"Finding nearest {resource_type}...")
    nearest_resource_position = nearest(resource_type)
    
    # Move towards that position to start harvesting
    print(f"Moving to {resource_type} at position {nearest_resource_position}...")
    move_to(nearest_resource_position)
    
    # Harvesting the specified amount of resource
    print(f"Harvesting {amount_needed} units of {resource_type}.")
    harvested_amount = harvest_resource(nearest_resource_position, quantity=amount_needed)
    
    # Check if we successfully harvested enough resources
    current_inventory_count = inspect_inventory().get(resource_type, 0)
    assert current_inventory_count >= amount_needed, f"Failed to gather enough {resource_type}. Expected at least {amount_needed}, but got {current_inventory_count}"
    
    print(f"Successfully gathered {harvested_amount} units of {resource_type}. Current inventory count is now: {current_inventory_count}")

# Final check on inventory status after gathering all necessary resources
final_inventory_status = inspect_inventory()
print("Final Inventory after Resource Gathering:", final_inventory_status)

# Get the amount of iron ore in the wooden chest
chest = get_entities({Prototype.WoodenChest})[0]
iron_ore_in_chest = chest.inventory.get(Prototype.IronOre.value[0], 0)

assert final_inventory_status.get(Resource.Stone, 0) >= 5, "Not enough stone gathered."
assert final_inventory_status.get(Resource.IronOre, 0) + iron_ore_in_chest >= 24, "Not enough iron ore gathered."
assert final_inventory_status.get(Resource.Coal, 0) >= 10, "Not enough coal gathered."

print("Successfully completed gathering all necessary resources.")


"""
Step 3: Craft and place stone furnace. We need to:
- Craft the stone furnace using the 5 stone
- Place the stone furnace near the wooden chest
"""
# Inventory at the start of step {'coal': 10, 'stone': 5, 'iron-ore': 4}
#Step Execution

# Step: Craft and place a stone furnace

# First, craft one Stone Furnace
print("Crafting a Stone Furnace...")
craft_item(Prototype.StoneFurnace, 1)
print("Stone Furnace crafted successfully.")

# Get current position of Wooden Chest for reference
chest_position = Position(x=-11.5, y=-11.5)

# Move closer to where we'll be placing the Stone Furnace
move_to(chest_position)

# Decide on a placement direction; here we choose RIGHT of the chest for simplicity
furnace_placement_direction = Direction.RIGHT

# Place Stone Furnace right next to Wooden Chest
stone_furnace = place_entity_next_to(
    entity=Prototype.StoneFurnace,
    reference_position=chest_position,
    direction=furnace_placement_direction,
    spacing=0  # No space between them
)
print(f"Placed Stone Furnace at {stone_furnace.position}")

# Verify if placement was successful by checking if there's now an additional Stone Furnace entity nearby
entities_nearby = get_entities({Prototype.StoneFurnace}, position=chest_position, radius=10)
assert len(entities_nearby) > 0, "Failed to place Stone Furnace."

print("Successfully placed a Stone Furnace near Wooden Chest.")


"""
Step 4: Smelt iron plates. We need to:
- Move to the wooden chest and retrieve the 20 iron ore
- Move to the stone furnace and insert the iron ore
- Add coal to the furnace for fuel
- Wait for the iron ore to smelt into iron plates
- Retrieve the iron plates from the furnace
- Smelt the additional 4 iron ore into iron plates
"""
# Placeholder 4

"""
Step 5: Craft firearm magazines. We need to:
- Use the 24 iron plates to craft 6 firearm magazines
"""
# Placeholder 5

"""
Step 6: Check success. We need to:
- Check the inventory to ensure we have 6 firearm magazines
##
"""
# Placeholder 6