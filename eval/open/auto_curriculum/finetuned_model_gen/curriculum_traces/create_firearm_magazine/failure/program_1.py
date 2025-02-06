
from instance import *

"""
Step 1: Craft a stone furnace
- Mine 6 stone
- Craft 1 stone furnace
"""
# Task: Craft a stone furnace
# We need to mine stone and craft a stone furnace

# Print recipe for stone furnace
recipe = get_prototype_recipe(Prototype.StoneFurnace)
print("Stone Furnace Recipe:")
print(f"Ingredients: {recipe.ingredients}")

# Step 1: Get stone for stone furnace
stone_position = nearest(Resource.Stone)
move_to(stone_position)
stone_mined = harvest_resource(stone_position, quantity=6)
print(f"Mined {stone_mined} stone")
assert stone_mined >= 6, f"Failed to mine enough stone. Mined: {stone_mined}"

# Check inventory for stone
current_inventory = inspect_inventory()
stone_in_inventory = current_inventory.get(Prototype.Stone, 0)
assert stone_in_inventory >= 6, f"Not enough stone in inventory. Expected: 6, Found: {stone_in_inventory}"
print(f"Current Inventory after mining stone: {current_inventory}")

# Step 2: Craft stone furnace
crafted = craft_item(Prototype.StoneFurnace, quantity=1)
print(f"Crafted {crafted} stone furnace(s)")
assert crafted >= 1, "Failed to craft stone furnace"

# Verify that the stone furnace is in the inventory
stone_furnace_in_inventory = inspect_inventory().get(Prototype.StoneFurnace, 0)
assert stone_furnace_in_inventory >= 1, f"Stone Furnace not in inventory after crafting. Expected: 1, Found: {stone_furnace_in_inventory}"

print("Successfully crafted and obtained a Stone Furnace")

"""
Step 2: Set up the smelting area
- Place the stone furnace
- Mine coal for fuel (at least 1 piece)
"""
# Step 1: Place the stone furnace
current_position = inspect_entities().player_position
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=current_position[0]+2, y=current_position[1]))
print(f"Placed stone furnace at {furnace.position}")

# Step 2: Mine coal for fuel
coal_position = nearest(Resource.Coal)
move_to(coal_position)
coal_mined = harvest_resource(coal_position, quantity=1)
print(f"Mined {coal_mined} coal")
assert coal_mined >= 1, f"Failed to mine enough coal. Mined: {coal_mined}"

"""
Step 3: Gather iron ore
- Mine at least 4 iron ore
"""
# Step 1: Find and move to iron ore patch
iron_position = nearest(Resource.IronOre)
print(f"Nearest iron ore found at: {iron_position}")
move_to(iron_position)
print(f"Moved to iron ore patch at: {iron_position}")

# Step 2: Mine the iron ore
iron_mined = harvest_resource(iron_position, quantity=4)
print(f"Mined {iron_mined} iron ore")
assert iron_mined >= 4, f"Failed to mine enough iron ore. Expected: 4, Mined: {iron_mined}"

# Step 3: Verify that we have enough iron ore in our inventory
current_inventory = inspect_inventory()
iron_in_inventory = current_inventory.get(Prototype.IronOre, 0)
assert iron_in_inventory >= 4, f"Not enough iron ore in inventory. Expected: 4, Found: {iron_in_inventory}"
print(f"Current Inventory after mining iron ore: {current_inventory}")

"""
Step 4: Smelt iron plates
- Place coal in the furnace as fuel
- Place iron ore in the furnace
- Wait for the smelting process to complete (4 seconds per plate)
- Extract 4 iron plates from the furnace
"""
# Step 1: Move to the stone furnace
move_to(furnace.position)
print(f"Moved to stone furnace at: {furnace.position}")

# Step 2: Insert coal into the furnace as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=1)
coal_inserted = updated_furnace.fuel.get(Prototype.Coal, 0)
print(f"Inserted {coal_inserted} coal into the furnace")
assert coal_inserted >= 1, f"Failed to insert enough coal. Inserted: {coal_inserted}"

# Step 3: Insert iron ore into the furnace
iron_ore_in_inventory = inspect_inventory().get(Prototype.IronOre, 0)
print(f"Iron ore in inventory before insertion: {iron_ore_in_inventory}")
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=iron_ore_in_inventory)
print(f"Inserted {iron_ore_in_inventory} iron ore into the furnace")

# Step 4: Wait for smelting to complete
smelting_time = 4 * iron_ore_in_inventory
sleep(smelting_time)
print(f"Waited {smelting_time} seconds for smelting")

# Step 5: Extract iron plates from the furnace
# First extract any existing items to make space
extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
# Then extract the new iron plates
extracted_plates = extract_item(Prototype.IronPlate, updated_furnace.position, quantity=iron_ore_in_inventory)
print(f"Extracted {extracted_plates} iron plates from the furnace")

# Step 6: Verify that we have enough iron plates in our inventory
iron_plates_in_inventory = inspect_inventory().get(Prototype.IronPlate, 0)
assert iron_plates_in_inventory >= 4, f"Not enough iron plates in inventory. Expected: 4, Found: {iron_plates_in_inventory}"
print(f"Current Inventory after extracting iron plates: {inspect_inventory()}")

"""
Step 5: Craft firearm magazine
- Use 4 iron plates to craft 1 firearm magazine
"""
# Step 1: Print recipe for Firearm Magazine
recipe = get_prototype_recipe(Prototype.FirearmMagazine)
print("Firearm Magazine Recipe:")
print(f"Ingredients: {recipe.ingredients}")

# Step 2: Craft the Firearm Magazine
crafted = craft_item(Prototype.FirearmMagazine, quantity=1)
print(f"Crafted {crafted} firearm magazine(s)")
assert crafted >= 1, "Failed to craft firearm magazine"

# Step 3: Verify that the firearm magazine is in the inventory
firearm_magazine_in_inventory = inspect_inventory().get(Prototype.FirearmMagazine, 0)
assert firearm_magazine_in_inventory >= 1, f"Firearm Magazine not in inventory after crafting. Expected: 1, Found: {firearm_magazine_in_inventory}"

# Step 4: Print final inventory state
final_inventory = inspect_inventory()
print(f"Final Inventory: {final_inventory}")

# Additional verification: Check if iron plates were used correctly
iron_plates_used = initial_iron_plates - final_inventory.get(Prototype.IronPlate, 0)
assert iron_plates_used >= 4, f"Iron plates not used correctly. Expected to use at least 4, but used {iron_plates_used}"

print("Successfully crafted and obtained a Firearm Magazine")

