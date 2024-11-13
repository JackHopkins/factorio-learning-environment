
from factorio_instance import *

"""
Step 1: Find underground-belts
- Search for chests on the map that might contain underground-belt
- If found, extract the underground-belt from the chest
- If not found, print a message indicating we couldn't find the necessary items
"""
# Define the items we need to find
items_to_find = [Prototype.UndergroundBelt]

# Get all the chests on the map
chests_on_map = get_entities({Prototype.WoodenChest, Prototype.IronChest})

# Loop through each chest
for chest in chests_on_map:
    # Move to the chest's position
    move_to(chest.position)
    
    # Check the chest's inventory
    chest_inventory = inspect_inventory(chest)
    
    # Check if the chest contains any of the items we're looking for
    for item in items_to_find:
        if chest_inventory.get(item, 0) > 0:
            # Extract the item from the chest
            extract_item(item, chest.position, chest_inventory[item])
            
            # Check if the extraction was successful
            player_inventory = inspect_inventory()
            assert player_inventory.get(item, 0) >= chest_inventory[item], f"Failed to extract {item}"

# Check if we have the underground-belt in our inventory
final_inventory = inspect_inventory()
if final_inventory.get(Prototype.UndergroundBelt, 0) >= 2:
    print("Successfully found and extracted 2 underground-belts!")
else:
    print("Couldn't find the necessary underground-belts. Crafting fast-underground-belt is not possible.")

"""
Step 2: Craft fast-underground-belt
- If we found the underground-belt, proceed to craft the fast-underground-belt
- Craft 1 fast-underground-belt using 2 underground-belt
"""
# Check if we have the underground-belt in our inventory
if final_inventory.get(Prototype.UndergroundBelt, 0) >= 2:
    # Craft the fast-underground-belt
    craft_item(Prototype.FastUndergroundBelt, 1)
    
    # Verify that we have crafted the fast-underground-belt
    crafted_inventory = inspect_inventory()
    assert crafted_inventory.get(Prototype.FastUndergroundBelt, 0) >= 1, "Failed to craft fast-underground-belt"
    print("Successfully crafted 1 fast-underground-belt!")
else:
    print("Not enough underground-belts to craft fast-underground-belt.")

# Final inventory check
print(f"Final inventory: {inspect_inventory()}")
