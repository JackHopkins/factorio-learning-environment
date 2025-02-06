
from instance import *

"""
Step 1: Gather raw resources
"""
# Find and mine iron ore
iron_ore_position = nearest(Resource.IronOre)
move_to(iron_ore_position)
harvest_resource(iron_ore_position, quantity=30)
print(f"Mined 30 iron ore")

# Find and mine stone
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=12)
print(f"Mined 12 stone")

# Find and mine coal
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, quantity=10)
print(f"Mined 10 coal")

"""
Step 2: Craft stone furnaces
"""
craft_item(Prototype.StoneFurnace, quantity=2)
print("Crafted 2 stone furnaces")

"""
Step 3: Set up smelting operation
"""
# Place stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)

# Insert coal into furnace for fuel
insert_item(Prototype.Coal, furnace, quantity=5)

# Insert iron ore into furnace
insert_item(Prototype.IronOre, furnace, quantity=30)

"""
Step 4: Smelt iron plates
"""
# Wait for smelting to complete (30 iron ore takes 15 seconds)
sleep(15)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=30)
print("Extracted 30 iron plates")

# Verify we have enough iron plates
iron_plates = inspect_inventory()[Prototype.IronPlate]
assert iron_plates >= 30, f"Failed to obtain enough iron plates! Only have {iron_plates}"

"""
Step 5: Craft iron gear wheels
"""
craft_item(Prototype.IronGearWheel, quantity=4)
print("Crafted 4 iron gear wheels")

"""
Step 6: Craft burner mining drill
"""
craft_item(Prototype.BurnerMiningDrill, quantity=1)
print("Crafted 1 burner mining drill")

# Verify we have the burner mining drill
inventory = inspect_inventory()
assert inventory[Prototype.BurnerMiningDrill] >= 1, "Failed to craft burner mining drill"
