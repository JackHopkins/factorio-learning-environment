

from factorio_instance import *

"""
Step 1: Craft stone furnace
"""
# Get stone for furnace
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, quantity=10)  # Get extra for safety

# Verify stone collected
inventory = inspect_inventory()
assert inventory.get(Prototype.Stone) >= 10, "Failed to get enough stone"

# Craft stone furnace
craft_item(Prototype.StoneFurnace, 2)

# Verify furnace crafted
inventory = inspect_inventory()
assert inventory.get(Prototype.StoneFurnace) >= 2, "Failed to craft stone furnace"

"""
Step 2: Gather resources
"""
# Get coal for fuel
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, quantity=20)

# Get iron ore
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, quantity=40)

# Verify resources collected
inventory = inspect_inventory()
assert inventory.get(Prototype.Coal) >= 20, "Failed to get enough coal"
assert inventory.get(Prototype.IronOre) >= 40, "Failed to get enough iron ore"

"""
Step 3: Smelt iron plates
"""
# Place furnaces
current_pos = inspect_entities().player_position
furnace1 = place_entity(Prototype.StoneFurnace, position=Position(x=current_pos[0], y=current_pos[1]+2))
furnace2 = place_entity(Prototype.StoneFurnace, position=Position(x=current_pos[0], y=current_pos[1]+4))

# Add fuel to furnaces
insert_item(Prototype.Coal, furnace1, 10)
insert_item(Prototype.Coal, furnace2, 10)

# Add iron ore to furnaces
insert_item(Prototype.IronOre, furnace1, 20)
insert_item(Prototype.IronOre, furnace2, 20)

sleep(10)

# Extract iron plates
extract_item(Prototype.IronPlate, furnace1.position, 20)
extract_item(Prototype.IronPlate, furnace2.position, 20)

# Verify iron plates
inventory = inspect_inventory()
assert inventory.get(Prototype.IronPlate) >= 20, f"Failed to smelt enough iron plates, only have {inventory.get(Prototype.IronPlate)}"

"""
Step 4: Craft transport belts and underground belt
"""
# Craft iron gear wheels (5)
craft_item(Prototype.IronGearWheel, 5)

# Craft transport belts (5)
craft_item(Prototype.TransportBelt, 5)

# Craft underground belt (1)
craft_item(Prototype.UndergroundBelt, 1)

# Verify transport belts crafted
inventory = inspect_inventory()
assert inventory.get(Prototype.TransportBelt) >= 5, f"Failed to craft transport belts, only have {inventory.get(Prototype.TransportBelt)}"
assert inventory.get(Prototype.UndergroundBelt) >= 1, f"Failed to craft an underground belt, only have {inventory.get(Prototype.UndergroundBelt)}"

print("Successfully crafted transport belts and an underground belt")

