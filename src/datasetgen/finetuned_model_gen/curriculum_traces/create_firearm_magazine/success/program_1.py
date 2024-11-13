
from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipes for stone-furnace and firearm-magazine
"""
# Get the recipe for stone-furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)

# Print the recipe for stone-furnace
print("stone-furnace Recipe:")
print(f"Ingredients: {stone_furnace_recipe.ingredients}")


# Get the recipe for firearm-magazine
firearm_magazine_recipe = get_prototype_recipe(Prototype.FirearmMagazine)

# Print the recipe for firearm-magazine
print("firearm-magazine Recipe:")
print(f"Ingredients: {firearm_magazine_recipe.ingredients}")

"""
Step 2: Gather raw resources
- Mine 6 stone (5 for stone-furnace, 1 extra)
- Mine 8 iron ore (4 for firearm-magazine, 4 extra for safety)
- Mine 3 coal (1 for furnace fuel, 2 extra for safety)
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 6),
    (Resource.IronOre, 8),
    (Resource.Coal, 3)
]

# Loop through each resource type and quantity
for resource_type, required_quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    # Move to the resource
    move_to(resource_position)
    # Harvest the resource, with a bit of extra to ensure we have enough
    harvested = harvest_resource(resource_position, required_quantity + 2)
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= required_quantity, f"Failed to gather enough {resource_type}. Required: {required_quantity}, Actual: {actual_quantity}"
    print(f"Successfully gathered {actual_quantity} {resource_type}")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory: {final_inventory}")

# Verify that we have at least the required amount of each resource
assert final_inventory.get(Resource.Stone, 0) >= 6, f"Not enough Stone. Required: 6, Actual: {final_inventory.get(Resource.Stone, 0)}"
assert final_inventory.get(Resource.IronOre, 0) >= 8, f"Not enough Iron Ore. Required: 8, Actual: {final_inventory.get(Resource.IronOre, 0)}"
assert final_inventory.get(Resource.Coal, 0) >= 3, f"Not enough Coal. Required: 3, Actual: {final_inventory.get(Resource.Coal, 0)}"

print("Successfully gathered all required resources!")


"""
Step 3: Craft stone-furnace
- Craft 1 stone-furnace
"""
# Craft the stone-furnace
crafted = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted {crafted} Stone Furnace(s)")

# Verify that we crafted the stone-furnace
stone_furnaces_in_inventory = inspect_inventory().get(Prototype.StoneFurnace, 0)
assert stone_furnaces_in_inventory >= 1, f"Failed to craft Stone Furnace. Expected at least 1, but found {stone_furnaces_in_inventory}"

print("Successfully crafted Stone Furnace!")

"""
Step 4: Set up smelting operation
- Place the stone-furnace
- Add 1 coal to the furnace as fuel
- Smelt 8 iron ore into iron plates
"""
# Place the stone-furnace
origin = Position(x=0, y=0) 
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed Stone Furnace at {furnace.position}")

# Add coal to the furnace as fuel
coal_in_inventory = inspect_inventory().get(Prototype.Coal, 0)
assert coal_in_inventory >= 1, f"Not enough coal in inventory. Expected at least 1, but found {coal_in_inventory}"

# Insert coal into the furnace
fueled_furnace = insert_item(Prototype.Coal, furnace, quantity=1)
print("Inserted coal into the Stone Furnace")

# Verify that coal was inserted successfully
coal_in_furnace = fueled_furnace.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace >= 1, "Failed to insert coal into Stone Furnace"

# Insert iron ore into the furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
assert iron_ore_in_inventory >= 8, f"Not enough iron ore in inventory. Expected at least 8, but found {iron_ore_in_inventory}"

# Smelt 8 iron ore into iron plates
for _ in range(8):
    # Insert one piece of iron ore
    furnace = insert_item(Prototype.IronOre, fueled_furnace, quantity=1)
    print("Inserted Iron Ore into the Stone Furnace")

    # Wait for smelting to complete
    sleep(1)  # Adjust sleep time if necessary

    # Extract iron plate
    extract_item(Prototype.IronPlate, furnace.position, quantity=1)
    print("Extracted Iron Plate from the Stone Furnace")

# Verify that we have at least 8 iron plates in our inventory
iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
assert iron_plates_in_inventory >= 8, f"Failed to smelt enough Iron Plates. Expected at least 8, but found {iron_plates_in_inventory}"

print(f"Successfully set up smelting operation and obtained {iron_plates_in_inventory} Iron Plates")


"""
Step 5: Craft firearm-magazine
- Craft 1 firearm-magazine using 4 iron plates
"""
# Check current inventory for iron plates
iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
assert iron_plates_in_inventory >= 4, f"Not enough Iron Plates in inventory. Expected at least 4, but found {iron_plates_in_inventory}"

# Craft the firearm-magazine
crafted = craft_item(Prototype.FirearmMagazine, quantity=1)
print(f"Crafted {crafted} Firearm Magazine(s)")

# Verify that we crafted the firearm-magazine
firearm_magazines_in_inventory = inspect_inventory().get(Prototype.FirearmMagazine, 0)
assert firearm_magazines_in_inventory >= 1, f"Failed to craft Firearm Magazine. Expected at least 1, but found {firearm_magazines_in_inventory}"

print("Successfully crafted Firearm Magazine!")

# Final inventory check
final_inventory = inspect_inventory()
print(f"Final inventory after crafting Firearm Magazine: {final_inventory}")

