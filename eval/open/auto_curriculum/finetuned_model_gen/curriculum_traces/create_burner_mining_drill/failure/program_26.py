
from instance import *

"""
Step 1: Gather raw resources
- Mine at least 12 stone (5 for the stone furnace, 7 for extra stone furnace)
- Mine 30 iron ore (6 for iron gear wheels, 3 for drill, 5 for furnace, 16 for extra plates)
- Mine 2 coal for fuel
"""
# Get stone first
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=12)
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.Stone) >= 12, "Failed to get enough stone"

# Get iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=30)
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronOre) >= 30, "Failed to get enough iron ore"

# Get coal
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=2)
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.Coal) >= 2, "Failed to get enough coal"

"""
Step 2: Craft stone furnaces
- Craft 2 stone furnaces (one for smelting, one for drill)
"""
craft_item(Prototype.StoneFurnace, quantity=2)
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.StoneFurnace) >= 2, "Failed to craft 2 stone furnaces"

"""
Step 3: Set up smelting
- Place a stone furnace
- Add coal to the furnace as fuel
- Smelt 29 iron ore into iron plates (30 needed, but we'll have 1 leftover for safety)
"""
# Place furnace near us
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
# Add coal as fuel
insert_item(Prototype.Coal, furnace, quantity=2)
# Add iron ore
insert_item(Prototype.IronOre, furnace, quantity=30)

# Wait for smelting
sleep(30)  # 1 second per ore
# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=30)
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronPlate) >= 30, "Failed to smelt enough iron plates"


"""
Step 4: Craft iron gear wheels
- Craft 6 iron gear wheels (3 for the drill, 3 for extra gear wheels)
"""
craft_item(Prototype.IronGearWheel, quantity=6)
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.IronGearWheel) >= 6, "Failed to craft 6 iron gear wheels"

"""
Step 5: Craft the burner mining drill
- Craft 1 burner mining drill
"""
craft_item(Prototype.BurnerMiningDrill, quantity=1)
current_inventory = inspect_inventory()
assert current_inventory.get(Prototype.BurnerMiningDrill) >= 1, "Failed to craft burner mining drill"
