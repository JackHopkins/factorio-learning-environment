from factorio_instance import *

"""
Main Objective: We need three stone furnaces. The final success should be checked by looking if 3 stone furnaces are in inventory
"""



"""
Step 1: Gather resources. We need to mine the following resources by hand:
- Mine at least 15 stone
- Mine some coal (around 5 pieces) for potential fuel needs
"""
# Inventory at the start of step {}
#Step Execution

# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 15),
    (Resource.Coal, 5)
]

# Loop through each resource type
for resource, amount in resources_to_gather:
    # Find the nearest patch of the current resource
    resource_position = nearest(resource)
    print(f"Found {resource} at position {resource_position}")

    # Move to the resource position
    move_to(resource_position)
    print(f"Moved to {resource} position")

    # Harvest the resource
    harvested = harvest_resource(resource_position, amount)
    print(f"Harvested {harvested} {resource}")

    # Check if we've gathered enough
    current_amount = inspect_inventory().get(resource, 0)
    assert current_amount >= amount, f"Failed to gather enough {resource}. Got {current_amount}, needed {amount}"
    print(f"Successfully gathered {current_amount} {resource}")

# Print final inventory state
final_inventory = inspect_inventory()
print(f"Final inventory after gathering resources: {final_inventory}")

# Additional assertions to ensure we have the required resources
assert final_inventory.get(Resource.Stone, 0) >= 15, "Not enough stone in inventory"
assert final_inventory.get(Resource.Coal, 0) >= 5, "Not enough coal in inventory"

print("Successfully gathered all required resources!")


"""
Step 2: Craft stone furnaces. We need to craft three stone furnaces using the gathered stone. The recipe for each stone furnace is:
- 5 stone
"""
# Inventory at the start of step {'coal': 5, 'stone': 15}
#Step Execution

# Get the recipe for stone furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)

# Check if we have enough stone to craft 3 furnaces
stone_in_inventory = inspect_inventory()[Prototype.Stone]
stone_needed = stone_furnace_recipe.ingredients[0].count * 3  # 5 stone * 3 furnaces
assert stone_in_inventory >= stone_needed, f"Not enough stone to craft 3 furnaces. Have {stone_in_inventory}, need {stone_needed}"

print(f"Starting to craft 3 stone furnaces. Stone in inventory: {stone_in_inventory}")

# Craft 3 stone furnaces
for i in range(3):
    craft_result = craft_item(Prototype.StoneFurnace, 1)
    assert craft_result == 1, f"Failed to craft stone furnace. Expected to craft 1, but crafted {craft_result}"
    print(f"Crafted stone furnace {i+1}")

# Verify the number of stone furnaces in inventory
furnaces_in_inventory = inspect_inventory()[Prototype.StoneFurnace]
assert furnaces_in_inventory == 3, f"Expected 3 stone furnaces in inventory, but found {furnaces_in_inventory}"

# Check remaining stone
remaining_stone = inspect_inventory()[Prototype.Stone]
assert remaining_stone == 0, f"Expected 0 stone remaining, but found {remaining_stone}"

print(f"Successfully crafted 3 stone furnaces. Remaining stone: {remaining_stone}")
print(f"Current inventory: {inspect_inventory()}")


"""
Step 3: Verify success. Check the inventory to ensure we have 3 stone furnaces.
##
"""
# Inventory at the start of step {'stone-furnace': 3, 'coal': 5}
#Step Execution

# Verify success. Check the inventory to ensure we have 3 stone furnaces.
current_inventory = inspect_inventory()
stone_furnaces_count = current_inventory[Prototype.StoneFurnace]

assert stone_furnaces_count == 3, f"Expected 3 stone furnaces in inventory, but found {stone_furnaces_count}"

print(f"Success! We have {stone_furnaces_count} stone furnaces in our inventory.")
print(f"Final inventory: {current_inventory}")
