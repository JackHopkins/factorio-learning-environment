

from factorio_instance import *

"""
Step 1: Print recipes. We need to print the recipes for stone furnace, transport belt, and underground belt.
"""
# Get the recipe for stone furnace
stone_furnace_recipe = get_prototype_recipe(Prototype.StoneFurnace)

# Get the recipe for transport belt
transport_belt_recipe = get_prototype_recipe(Prototype.TransportBelt)

# Get the recipe for underground belt
underground_belt_recipe = get_prototype_recipe(Prototype.UndergroundBelt)

print(f"Stone Furnace Recipe: {stone_furnace_recipe}")
print(f"Transport Belt Recipe: {transport_belt_recipe}")
print(f"Underground Belt Recipe: {underground_belt_recipe}")

"""
Step 2: Craft stone furnace. We need to gather 5 stone and craft a stone furnace.
"""
# Gather 5 stone
stone_position = nearest(Resource.Stone)
move_to(stone_position)
harvest_resource(stone_position, quantity=5)

# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)

"""
Step 3: Gather resources. We need to mine iron ore and coal. We need at least 10 iron ore and some coal for fuel.
"""
# Gather iron ore
iron_position = nearest(Resource.IronOre)
move_to(iron_position)
harvest_resource(iron_position, quantity=10)

# Gather coal
coal_position = nearest(Resource.Coal)
move_to(coal_position)
harvest_resource(coal_position, quantity=5)

"""
Step 4: Set up smelting. We need to place the stone furnace and smelt the iron ore into iron plates.
"""
# Place the stone furnace near the iron ore
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=iron_position.x+2, y=iron_position.y))

# Insert coal into the furnace as fuel
insert_item(Prototype.Coal, furnace, quantity=5)

# Insert iron ore into the furnace
insert_item(Prototype.IronOre, furnace, quantity=10)

# Wait for smelting to complete
sleep(10)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace.position, quantity=10)

"""
Step 5: Craft transport belts. We need to craft 5 transport belts using 10 iron plates.
"""
# Craft 5 transport belts
craft_item(Prototype.TransportBelt, quantity=5)

"""
Step 6: Craft underground belt. We need to use the 10 iron plates and 5 transport belts to craft an underground belt.
"""
# Craft underground belt
craft_item(Prototype.UndergroundBelt, quantity=1)

# Verify that we have crafted an underground belt
inventory = inspect_inventory()
assert inventory.get(Prototype.UndergroundBelt, 0) >= 1, "Failed to craft underground belt"

print("Successfully crafted an underground belt!")

