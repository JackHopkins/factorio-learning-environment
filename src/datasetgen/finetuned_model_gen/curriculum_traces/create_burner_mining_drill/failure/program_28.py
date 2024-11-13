
from factorio_instance import *

"""
Step 1: Place a stone furnace
"""
# Get stone for furnace
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=5)

# Craft and place furnace
craft_item(Prototype.StoneFurnace, 1)
furnace = place_entity(Prototype.StoneFurnace, position=stone_pos) 

"""
Step 2: Get iron plates and craft stone furnaces
"""
# Get coal for fuel
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=10)
insert_item(Prototype.Coal, furnace, 5)

# Get iron ore
iron_pos = nearest(Resource.IronOre) 
move_to(iron_pos)
harvest_resource(iron_pos, quantity=30) 

# Smelt iron plates
insert_item(Prototype.IronOre, furnace, 30)
sleep(20)
extract_item(Prototype.IronPlate, furnace.position, 30)

# Verify we have enough iron plates
inventory = inspect_inventory()
assert inventory.get(Prototype.IronPlate) >= 30, "Not enough iron plates"

# Craft 2 stone furnaces
craft_item(Prototype.StoneFurnace, 2)

"""
Step 3: Craft burner mining drill
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, 3)

# Craft burner mining drill
craft_item(Prototype.BurnerMiningDrill, 1)

# Verify we have the drill
inventory = inspect_inventory()
assert inventory.get(Prototype.BurnerMiningDrill) >= 1, "Failed to craft burner mining drill"

# Verify we have 2 stone furnaces
assert inventory.get(Prototype.StoneFurnace) >= 2, "Failed to craft 2 stone furnaces"
