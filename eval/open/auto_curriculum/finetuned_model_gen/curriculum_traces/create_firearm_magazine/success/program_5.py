
from instance import *

"""
Objective: Create a firearm magazine from scratch

Planning:
We need to create a firearm magazine, but we have no items in our inventory and no entities on the map.
To craft a firearm magazine, we need 4 iron plates.
We need to smelt iron ore into iron plates, which requires a furnace.
We'll need to mine all the necessary resources (stone, coal, iron ore) and craft the required items.
"""

"""
Step 1: Print out recipes
"""
print("Recipe for firearm magazine: 4 iron plates")
print("Recipe for stone furnace: 5 stone")

"""
Step 2: Craft stone furnace
- Mine stone for the furnace
- Craft the stone furnace
"""
# Mine stone
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=6)  # Get 6 stone (1 extra for safety)

# Verify we have enough stone
stone_in_inventory = inspect_inventory()[Prototype.Stone]
assert stone_in_inventory >= 5, f"Failed to gather enough stone! Have {stone_in_inventory}"

# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)
print("Crafted 1 Stone Furnace")

# Verify we have the stone furnace
furnace_in_inventory = inspect_inventory()[Prototype.StoneFurnace]
assert furnace_in_inventory >= 1, "Failed to craft Stone Furnace"

# Place the stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)
print("Placed Stone Furnace")

"""
Step 3: Prepare resources for smelting
- Mine coal for fuel
- Mine iron ore
"""
# Mine coal
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, quantity=8)  # Get 8 coal

# Verify coal
coal_in_inventory = inspect_inventory()[Prototype.Coal]
assert coal_in_inventory >= 8, f"Failed to gather enough coal! Have {coal_in_inventory}"

# Mine iron ore
iron_position = nearest(Resource.IronOre)
move_to(iron_position)
harvest_resource(iron_position, quantity=16)  # Get 16 iron ore

# Verify iron ore
iron_in_inventory = inspect_inventory()[Prototype.IronOre]
assert iron_in_inventory >= 16, f"Failed to gather enough iron ore! Have {iron_in_inventory}"

"""
Step 4: Smelt iron plates
"""
# Move back to furnace
move_to(furnace.position)

# Insert coal into furnace
updated_furnace = insert_item(Prototype.Coal, furnace, quantity=8)
print("Inserted coal into furnace")

# Insert iron ore into furnace
updated_furnace = insert_item(Prototype.IronOre, updated_furnace, quantity=16)
print("Inserted iron ore into furnace")

# Wait for smelting
smelting_time = 16  # 16 seconds for 16 iron plates
sleep(smelting_time)

# Extract iron plates
extract_item(Prototype.IronPlate, updated_furnace.position, quantity=16)

# Verify iron plates
iron_plate_in_inventory = inspect_inventory()[Prototype.IronPlate]
assert iron_plate_in_inventory >= 8, f"Failed to smelt enough iron plates! Have {iron_plate_in_inventory}"

"""
Step 5: Craft firearm magazine
"""
craft_item(Prototype.FirearmMagazine, quantity=1)
print("Crafted 1 Firearm Magazine")

# Verify firearm magazine
firearm_magazine_in_inventory = inspect_inventory()[Prototype.FirearmMagazine]
assert firearm_magazine_in_inventory >= 1, "Failed to craft Firearm Magazine"

print("Successfully crafted Firearm Magazine!")
print(f"Final inventory: {inspect_inventory()}")
