from factorio_instance import *

# Check initial inventory
iron_position = nearest(Resource.Stone)
move_to(iron_position)
print(f"Moved to iron patch at {iron_position}")
harvest_resource(iron_position, 20)

craft_item(Prototype.StoneFurnace, 3)

# 1. Place a stone furnace
stone_furnace = place_entity(Prototype.StoneFurnace, Direction.UP, iron_position)
assert stone_furnace is not None, "Failed to place stone furnace"