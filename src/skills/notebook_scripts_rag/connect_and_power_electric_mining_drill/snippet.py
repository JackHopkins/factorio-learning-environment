
    
# Place offshore pump near water
water_position = nearest(Resource.Water)
assert water_position, "No water source found nearby"
move_to(water_position)
offshore_pump = place_entity(Prototype.OffshorePump, Direction.DOWN, water_position)
assert offshore_pump, "Failed to place offshore pump"
print(f"Offshore pump placed at {offshore_pump.position}")

# Place boiler next to offshore pump
# Important: The boiler needs to be placed with a spacing of 2 to allow for pipe connections
boiler = place_entity_next_to(Prototype.Boiler, offshore_pump.position, Direction.DOWN, spacing=2)
assert boiler, "Failed to place boiler"
print(f"Boiler placed at {boiler.position}")
print(f"Current inventory: {inspect_inventory()}")

# add coal to the boiler
# need to update the boiler var after insert
boiler = insert_item(Prototype.Coal, boiler, quantity=5)
print(f"Inventory after adding coal: {inspect_inventory()}")

# Connect offshore pump to boiler with pipes
pipes = connect_entities(offshore_pump, boiler, Prototype.Pipe)
assert pipes, "Failed to connect offshore pump to boiler"
print(f"Pipes placed between offshore pump and boiler")

# Place steam engine next to boiler
# Important: The steam engine needs to be placed with a spacing of 2 to allow for pipe connections
steam_engine = place_entity_next_to(Prototype.SteamEngine, boiler.position, Direction.LEFT, spacing=2)
assert steam_engine, "Failed to place steam engine"
print(f"Steam engine placed at {steam_engine.position}")

# Connect boiler to steam engine with pipes
pipes = connect_entities(boiler, steam_engine, Prototype.Pipe)
assert pipes, "Failed to connect boiler to steam engine"
print(f"Pipes placed between boiler and steam engine")

# check if the boiler is receiving electricity
# if it says not connected to power network, then it is working
# it just isn't connected to any power poles
inspected_steam_engine = inspect_entities(position=steam_engine.position, radius=1).get_entity(Prototype.SteamEngine)
assert inspected_steam_engine.warning == 'not connected to power network'
print(f"Steam engine warning: {inspected_steam_engine.warning}")
