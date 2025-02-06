
from instance import *


"""
Step 1: Print recipes. We need to print the recipes for the following items:
- fast-underground-belt
"""

# Get the recipe for fast-underground-belt
recipe = get_prototype_recipe(Prototype.FastUndergroundBelt)

# Print the recipe
print("fast-underground-belt recipe:")
print(f"Ingredients: {recipe.ingredients}")

"""
Step 2: Craft a stone furnace. We need to craft a stone furnace to smelt iron ore into iron plates.
- Mine 5 stone
- Craft 1 stone furnace
"""
# Mine 5 stone
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=5)

# Check inventory for stone
inventory = inspect_inventory()
assert inventory.get(Prototype.Stone) >= 5, "Failed to get enough stone"

# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)

# Verify stone furnace crafted
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace) >= 1, "Failed to craft stone furnace"

"""
Step 3: Mine resources. We need to mine iron ore and coal.
- Mine at least 20 iron ore
- Mine at least 10 coal
"""
# Mine iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=20)

# Verify iron ore collected
inventory = inspect_inventory()
assert inventory.get(Prototype.IronOre) >= 20, "Failed to get enough iron ore"

# Mine coal
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=10)

# Verify coal collected
inventory = inspect_inventory()
assert inventory.get(Prototype.Coal) >= 10, "Failed to get enough coal"

"""
Step 4: Set up smelting. We need to set up a smelting area to produce iron plates.
- Place the stone furnace
- Add coal to the furnace as fuel
- Smelt 20 iron ore into iron plates
"""
# Place stone furnace
origin = Position(x=0, y=0)
move_to(origin)
furnace = place_entity(Prototype.StoneFurnace, position=origin)

# Add coal to furnace
insert_item(Prototype.Coal, furnace, quantity=10)

# Add iron ore to furnace
insert_item(Prototype.IronOre, furnace, quantity=20)

# Wait for smelting to complete
sleep(15)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=20)

# Verify iron plates produced
inventory = inspect_inventory()
assert inventory.get(Prototype.IronPlate) >= 20, "Failed to produce enough iron plates"

"""
Step 5: Craft iron gear wheels. We need to craft iron gear wheels as they are a component for underground belts.
- Craft 2 iron gear wheels (each requires 2 iron plates)
"""
# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, quantity=2)

# Verify iron gear wheels crafted
inventory = inspect_inventory()
assert inventory.get(Prototype.IronGearWheel) >= 2, "Failed to craft enough iron gear wheels"

"""
Step 6: Craft underground belts. We need to craft underground belts as they are a component for fast-underground-belt.
- Craft 2 underground belts (each requires 5 iron gear wheels and 5 transport belts)
"""
# Craft transport belts
craft_item(Prototype.TransportBelt, quantity=10)

# Craft underground belts
craft_item(Prototype.UndergroundBelt, quantity=2)

# Verify underground belts crafted
inventory = inspect_inventory()
assert inventory.get(Prototype.UndergroundBelt) >= 2, "Failed to craft enough underground belts"

"""
Step 7: Craft fast-underground-belt. We need to craft the final item.
- Craft 1 fast-underground-belt (requires 2 iron gear wheels and 2 underground belts)
"""
# Craft fast-underground-belt
craft_item(Prototype.FastUndergroundBelt, quantity=1)

# Verify fast-underground-belt crafted
inventory = inspect_inventory()
assert inventory.get(Prototype.FastUndergroundBelt) >= 1, "Failed to craft fast-underground-belt"
