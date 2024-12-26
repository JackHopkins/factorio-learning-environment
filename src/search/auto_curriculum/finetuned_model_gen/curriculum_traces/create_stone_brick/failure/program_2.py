

from factorio_instance import *

"""
Step 1: Craft a Stone Furnace
"""
# Check current inventory
current_inventory = inspect_inventory()
print(f"Current inventory: {current_inventory}")

# We need 5 stone for a stone furnace, we have 4, so we need to mine 1 more
stone_to_mine = 1

# Find nearest stone patch and mine
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=stone_to_mine)

# Update inventory
current_inventory = inspect_inventory()
print(f"Updated inventory after mining: {current_inventory}")

# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 Stone Furnace")

# Verify we have the stone furnace
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.StoneFurnace) >= 1, "Failed to craft Stone Furnace"
print("Successfully crafted Stone Furnace")

"""
Step 2: Place and Fuel the Furnace
"""
# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print(f"Placed Stone Furnace at {furnace.position}")

# Insert coal into the furnace as fuel
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=5)
print("Inserted coal into the Stone Furnace")

"""
Step 3: Smelt Stone into Stone Brick
"""
# We have 4 stone in our inventory, so we can smelt 2 stone bricks
stone_in_inventory = current_inventory.get(Prototype.Stone)
assert stone_in_inventory >= 2, "Not enough stone to smelt into stone bricks"

# Insert stone into the furnace
updated_furnace = insert_item(Prototype.Stone, updated_furnace, quantity=2)
print("Inserted stone into the Stone Furnace")

# Wait for smelting to complete (2 seconds per stone)
smelting_time = 2 * 2
sleep(smelting_time)

# Extract stone bricks
extract_item(Prototype.StoneBrick, updated_furnace.position, quantity=2)
print("Extracted stone bricks from the Stone Furnace")

# Verify we have stone bricks in our inventory
final_inventory = inspect_inventory()
stone_bricks = final_inventory.get(Prototype.StoneBrick)
assert stone_bricks >= 1, "Failed to smelt stone bricks"
print(f"Successfully smelted stone bricks. Current inventory: {final_inventory}")

"""
Additional Steps: Crafting Steel Plate
"""
# We need 10 iron ore to make 1 steel plate
iron_ore_to_mine = 10

# Find nearest iron ore patch and mine
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
harvest_resource(iron_ore_position, quantity=iron_ore_to_mine)

# Update inventory
current_inventory = inspect_inventory()
print(f"Updated inventory after mining iron ore: {current_inventory}")

# Insert iron ore into the furnace
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=10)
print("Inserted iron ore into the Stone Furnace")

# Wait for smelting to complete (0.7 seconds per iron ore)
smelting_time = int(0.7 * 10)
sleep(smelting_time)

# Extract iron plates
extract_item(Prototype.IronPlate, updated_furnace.position, quantity=10)
print("Extracted iron plates from the Stone Furnace")

# Insert iron plates back to make steel
updated_furnace = insert_item(Prototype.IronPlate, updated_furnace, quantity=5)
print("Inserted iron plates into the Stone Furnace to make steel")

# Wait for steel smelting to complete (5 seconds per steel plate)
smelting_time = int(5 * 1)
sleep(smelting_time)

# Extract steel plates
extract_item(Prototype.SteelPlate, updated_furnace.position, quantity=1)
print("Extracted steel plate from the Stone Furnace")

# Verify we have steel plates in our inventory
final_inventory = inspect_inventory()
steel_plates = final_inventory.get(Prototype.SteelPlate)
assert steel_plates >= 1, "Failed to craft steel plate"
print(f"Successfully crafted steel plate. Current inventory: {final_inventory}")

