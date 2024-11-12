move_to(Position(x=1, y=1))
    
# Place offshore pump near water
water_position = nearest(Resource.Water)
assert water_position, "No water source found nearby"
move_to(water_position)
offshore_pump = place_entity(Prototype.OffshorePump, Direction.DOWN, water_position)
assert offshore_pump, "Failed to place offshore pump"

# Place boiler next to offshore pump
# Important: The boiler needs to be placed with a spacing of 2 to allow for pipe connections
boiler = place_entity_next_to(Prototype.Boiler, offshore_pump.position, Direction.DOWN, spacing=2)
assert boiler, "Failed to place boiler"

# add coal to the boiler
# need to update the boiler var after insert
boiler = insert_item(Prototype.Coal, boiler, quantity=5)

# Connect offshore pump to boiler with pipes
pipes = connect_entities(offshore_pump, boiler, Prototype.Pipe)
assert pipes, "Failed to connect offshore pump to boiler"

# Place steam engine next to boiler
# Important: The steam engine needs to be placed with a spacing of 2 to allow for pipe connections
steam_engine = place_entity_next_to(Prototype.SteamEngine, boiler.position, Direction.LEFT, spacing=2)
assert steam_engine, "Failed to place steam engine"

# Connect boiler to steam engine with pipes
pipes = connect_entities(boiler, steam_engine, Prototype.Pipe)
assert pipes, "Failed to connect boiler to steam engine"

# check if the boiler is receiving electricity
# if it says not connected to power network, then it is working
# it just isn't connected to any power poles
inspected_steam_engine = inspect_entities(position=steam_engine.position, radius=1).get_entity(Prototype.SteamEngine)
assert inspected_steam_engine.warning == 'not connected to power network'


chest_pos = Position(x = 1, y = 1)
# move to chest position
move_to(chest_pos)
# put down the chest
place_entity(Prototype.WoodenChest, Direction.UP, chest_pos)