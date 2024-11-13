

from factorio_instance import *

"""
Step 1: Craft a stone furnace
"""
# Print recipe for stone furnace
recipe = get_prototype_recipe(Prototype.StoneFurnace)
print("Stone Furnace Recipe:")
print(f"Ingredients: {recipe.ingredients}")

# Get stone for furnace
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=5)

# Verify stone collected
inventory = inspect_inventory()
assert inventory.get(Prototype.Stone) >= 5, "Failed to get enough stone"

# Craft stone furnace
craft_item(Prototype.StoneFurnace, quantity=1)

# Verify furnace crafted
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace) >= 1, "Failed to craft stone furnace"

"""
Step 2: Set up iron smelting
"""
# Get coal for fuel
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=10)

# Get iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=40)

# Place furnaces near iron ore patch
furnace1 = place_entity(Prototype.StoneFurnace, position=Position(x=iron_pos.x+2, y=iron_pos.y))
furnace2 = place_entity(Prototype.StoneFurnace, position=Position(x=iron_pos.x+4, y=iron_pos.y))

# Add coal to furnaces
insert_item(Prototype.Coal, furnace1, 5)
insert_item(Prototype.Coal, furnace2, 5)

# Add iron ore to furnaces
insert_item(Prototype.IronOre, furnace1, 20)
insert_item(Prototype.IronOre, furnace2, 20)

"""
Step 3: Craft intermediate products
"""
# Wait for iron plates
sleep(10)

# Retrieve iron plates
extract_item(Prototype.IronPlate, furnace1.position, 20)
extract_item(Prototype.IronPlate, furnace2.position, 20)

# Verify iron plates
inventory = inspect_inventory()
assert inventory.get(Prototype.IronPlate) >= 30, "Failed to get enough iron plates"

# Craft iron gear wheels
craft_item(Prototype.IronGearWheel, 20)

# Verify gear wheels crafted
inventory = inspect_inventory()
assert inventory.get(Prototype.IronGearWheel) >= 20, "Failed to craft iron gear wheels"

"""
Step 4: Craft underground belt
"""
# Craft underground belt
craft_item(Prototype.UndergroundBelt, 1)

# Verify underground belt crafted
inventory = inspect_inventory()
assert inventory.get(Prototype.UndergroundBelt) >= 1, "Failed to craft underground belt"

"""
Step 5: Craft fast-underground-belt
"""
# Craft fast-underground-belt
craft_item(Prototype.FastUndergroundBelt, 1)

# Verify fast-underground-belt crafted
inventory = inspect_inventory()
assert inventory.get(Prototype.FastUndergroundBelt) >= 1, "Failed to craft fast-underground-belt"

print("Successfully crafted fast-underground-belt!")

