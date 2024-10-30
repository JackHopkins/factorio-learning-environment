from factorio_instance import *


furnace_pos = Position(x = -12, y = -12)
move_to(furnace_pos)
stone_furnace = place_entity(Prototype.StoneFurnace, Direction.UP, furnace_pos)