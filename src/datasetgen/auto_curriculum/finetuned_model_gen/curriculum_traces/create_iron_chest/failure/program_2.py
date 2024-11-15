
from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipes for the following items:
- stone-furnace
- firearm-magazine
- iron-chest
"""
# Print the recipe for stone-furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)
print("stone-furnace recipe:")
print(stone_furnace_recipe)

# Print the recipe for firearm-magazine
firearm_magazine_recipe = get_prototype_recipe(Prototype.FirearmMagazine)
print("firearm-magazine recipe:")
print(firearm_magazine_recipe)

# Print the recipe for iron-chest
iron_chest_recipe = get_prototype_recipe(Prototype.IronChest)
print("iron-chest recipe:")
print(iron_chest_recipe)

"""
Step 2: Gather resources. We need to mine the following resources:
- 6 stone (for the furnace)
- 14 iron ore (for the iron plates)
- 1 coal (for fuel)
"""
# Define the resources we need to gather
resources_to_gather = [
    (Resource.Stone, 6),
    (Resource.IronOre, 14),
    (Resource.Coal, 1)
]

# Loop over each resource type and quantity
for resource_type, quantity in resources_to_gather:
    # Find the nearest patch of this resource
    resource_position = nearest(resource_type)
    # Move to the resource
    move_to(resource_position)
    print(f"Moved to {resource_type} at {resource_position}")
    # Harvest the resource
    harvested = harvest_resource(resource_position, quantity)
    print(f"Harvested {harvested} {resource_type}")
    # Check if we harvested enough
    current_inventory = inspect_inventory()
    actual_quantity = current_inventory.get(resource_type, 0)
    assert actual_quantity >= quantity, f"Failed to gather enough {resource_type}. Expected {quantity}, got {actual_quantity}"

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory:")
print(f"Stone: {final_inventory.get(Resource.Stone, 0)}")
print(f"Iron Ore: {final_inventory.get(Resource.IronOre, 0)}")
print(f"Coal: {final_inventory.get(Resource.Coal, 0)}")

# Assert that we have gathered at least the required amount
assert final_inventory.get(Resource.Stone, 0) >= 6, "Not enough Stone"
assert final_inventory.get(Resource.IronOre, 0) >= 14, "Not enough Iron Ore"
assert final_inventory.get(Resource.Coal, 0) >= 1, "Not enough Coal"

print("Successfully gathered all required resources!")

"""
Step 3: Craft stone furnace. Use 5 stone to craft a stone furnace.
"""
# Craft the stone furnace
crafted = craft_item(Prototype.StoneFurnace, 1)
print(f"Crafted {crafted} Stone Furnace")

# Check if the crafting was successful
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.StoneFurnace, 0) >= 1, "Failed to craft Stone Furnace"

print("Successfully crafted a Stone Furnace!")

"""
Step 4: Set up smelting area. We need to:
- Place the stone furnace
- Add coal as fuel to the furnace
"""
# Place the stone furnace at the origin
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
print(f"Placed Stone Furnace at {furnace.position}")

# Insert coal into the furnace as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=1)
print("Inserted coal into the Stone Furnace")

# Check if the coal was successfully added as fuel
coal_in_furnace = updated_furnace.fuel.get(Prototype.Coal, 0)
assert coal_in_furnace > 0, "Failed to add coal as fuel to the Stone Furnace"

print("Successfully set up smelting area!")

"""
Step 5: Smelt iron plates. We need to:
- Smelt 14 iron ore into 14 iron plates
"""
# Insert 14 Iron Ore into the Furnace
print("Inserting Iron Ore...")
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=14)
print("Inserted Iron Ore into the Furnace")

# Wait for the smelting to complete
smelting_time_per_unit = 0.7  # 0.7 seconds per iron ore
total_smelting_time = int(smelting_time_per_unit * 14)
sleep(total_smelting_time)

# Extract Iron Plates from the Furnace
max_attempts = 5
for attempt in range(max_attempts):
    print(f"Attempt {attempt + 1}: Extracting Iron Plates...")
    extract_item(Prototype.IronPlate, updated_furnace.position, quantity=14)
    current_iron_plates = inspect_inventory().get(Prototype.IronPlate, 0)
    if current_iron_plates >= 14:
        break
    sleep(10)  # Wait a bit before trying again

print(f"Extracted Iron Plates; Current Inventory Count: {current_iron_plates}")
assert current_iron_plates >= 14, f"Failed to obtain required number of Iron Plates; Expected: 14, Actual: {current_iron_plates}"

print("Successfully smelted Iron Plates!")

"""
Step 6: Craft firearm magazine. We need to craft a firearm magazine using 4 iron plates.
"""
# Crafting a Firearm Magazine
crafted_magazines = craft_item(Prototype.FirearmMagazine, 1)
print(f"Crafted {crafted_magazines} Firearm Magazine(s)")

# Check if the crafting was successful
magazines_in_inventory = inspect_inventory().get(Prototype.FirearmMagazine, 0)
assert magazines_in_inventory >= 1, f"Failed to craft Firearm Magazine; Expected at least 1, Found: {magazines_in_inventory}"

print("Successfully crafted a Firearm Magazine!")

"""
Step 7: Craft iron chest. We need to craft an iron chest using 8 iron plates.
"""
# Crafting an Iron Chest
crafted_chests = craft_item(Prototype.IronChest, 1)
print(f"Crafted {crafted_chests} Iron Chest(s)")

# Check if the crafting was successful
chests_in_inventory = inspect_inventory().get(Prototype.IronChest, 0)
assert chests_in_inventory >= 1, f"Failed to craft Iron Chest; Expected at least 1, Found: {chests_in_inventory}"

print("Successfully crafted an Iron Chest!")

# Final inventory check
final_inventory = inspect_inventory()
print("Final Inventory:")
print(f"Iron Plates: {final_inventory.get(Prototype.IronPlate, 0)}")
print(f"Iron Chests: {final_inventory.get(Prototype.IronChest, 0)}")
print(f"Firearm Magazines: {final_inventory.get(Prototype.FirearmMagazine, 0)}")

