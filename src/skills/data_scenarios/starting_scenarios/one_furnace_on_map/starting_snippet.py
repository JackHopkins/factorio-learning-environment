from factorio_instance import *


iron_position = nearest(Resource.Stone)
move_to(iron_position)
stone_furnace = place_entity(Prototype.StoneFurnace, Direction.UP, iron_position)