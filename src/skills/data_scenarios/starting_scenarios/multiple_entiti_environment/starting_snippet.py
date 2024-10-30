from factorio_instance import *

iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
# put down the burner mining drill
drill = place_entity(Prototype.BurnerMiningDrill, Direction.UP, iron_pos)

copper_pos = nearest(Resource.CopperOre)
move_to(copper_pos)
# put down the burner mining drill
drill = place_entity(Prototype.BurnerMiningDrill, Direction.UP, copper_pos)


#move to 0,0
move_to(Position(x = 0, y = 0))

# set down one furnace at 0, 5
furnace = place_entity(Prototype.StoneFurnace,Direction.UP, Position(x = 0, y = 5))
# put one coal
insert_item(Prototype.Coal, furnace, 1)
# put 50 iron
insert_item(Prototype.IronOre, furnace, 50)

#set down one furnace at 0, -3
furnace = place_entity(Prototype.StoneFurnace, Direction.UP, Position(x = 0,y = -5))
# put one coal
insert_item(Prototype.Coal, furnace, 1)
# put 50 copper
insert_item(Prototype.CopperOre, furnace, 50)

# set down one furnace at 3, 0
furnace = place_entity(Prototype.StoneFurnace, Direction.UP, Position(x = 5, y=0))
# put one coal
insert_item(Prototype.Coal, furnace, 1)
# put 50 stone
insert_item(Prototype.Stone, furnace, 50)

# put down 2 wooden chests at 3, 3 and 3, -3

chest = place_entity(Prototype.WoodenChest, Direction.UP, Position(x=0,y=0))
chest = place_entity(Prototype.WoodenChest, Direction.UP, Position(x=5,y=-5))
# put 100 coal in one chest
insert_item(Prototype.Coal, chest, 100)