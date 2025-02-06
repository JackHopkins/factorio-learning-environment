
from instance import *

"""
Step 1: Craft an iron pickaxe
- We need to gather the necessary resources to craft an iron pickaxe
- This will allow us to mine stone for the furnace and iron ore for smelting
"""
# Craft an iron pickaxe
# Need 3 iron plates and 2 sticks (crafted from wood)

# Get wood for sticks
wood_pos = nearest(Resource.Wood)
move_to(wood_pos)
harvest_resource(wood_pos, quantity=5)

# Get iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=5)

# Get coal for smelting
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=5)

# Smelt iron ore into plates
furnace_pos = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
insert_item(Prototype.Coal, furnace_pos, quantity=5)
insert_item(Prototype.IronOre, furnace_pos, quantity=5)
sleep(5)
extract_item(Prototype.IronPlate, furnace_pos, quantity=5)

# Craft sticks
craft_item(Prototype.Stick, quantity=2)

# Craft iron pickaxe
craft_item(Prototype.IronPickaxe, quantity=1)

"""
Step 2: Craft a stone furnace
- We need to mine stone and craft a furnace for smelting iron plates
"""
# Mine stone
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=5)

# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)

"""
Step 3: Set up smelting operation
- Place the furnace and smelt iron ore into iron plates
"""
# Place stone furnace
furnace_pos = place_entity(Prototype.StoneFurnace, position=Position(x=2, y=0))

# Get more coal for fuel
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=10)

# Get more iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=20)

# Smelt iron plates
move_to(furnace_pos)
insert_item(Prototype.Coal, furnace_pos, quantity=10)
insert_item(Prototype.IronOre, furnace_pos, quantity=20)
sleep(20)
extract_item(Prototype.IronPlate, furnace_pos, quantity=20)

"""
Step 4: Craft iron gear wheels
- We need 4 iron gear wheels (2 for the fast underground belt, 2 for the underground belt)
"""
craft_item(Prototype.IronGearWheel, quantity=4)

"""
Step 5: Craft underground belt
- We need 1 underground belt as an ingredient for the fast underground belt
"""
craft_item(Prototype.UndergroundBelt, quantity=1)

"""
Step 6: Craft fast underground belt
- We now have all the ingredients to craft the fast underground belt
"""
craft_item(Prototype.FastUndergroundBelt, quantity=1)

"""
Step 7: Verify success
- Check that we have crafted a fast underground belt
"""
inventory = inspect_inventory()
assert inventory.get(Prototype.FastUndergroundBelt) >= 1, "Failed to craft fast underground belt"

