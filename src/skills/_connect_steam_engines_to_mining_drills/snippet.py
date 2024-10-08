# Find the nearest water and move to it
water_position = nearest(Resource.Water)
move_to(water_position)

# Place offshore pump near water
offshore_pump = place_entity(Prototype.OffshorePump, Direction.UP, water_position)
assert offshore_pump, "Failed to place offshore pump"
print(f"Offshore pump placed at {offshore_pump.position}")

# Place 3 boilers in a line
boilers = []
for i in range(3):
    boiler_position = Position(x=offshore_pump.position.x + i*3, y=offshore_pump.position.y)
    move_to(boiler_position)
    boiler = place_entity(Prototype.Boiler, Direction.RIGHT, boiler_position)
    assert boiler, f"Failed to place boiler {i+1}"
    boilers.append(boiler)
    print(f"Boiler {i+1} placed at {boiler.position}")

# Connect boilers with pipes
for i in range(2):
    pipes = connect_entities(boilers[i], boilers[i+1], Prototype.Pipe)
    assert pipes, f"Failed to connect boiler {i+1} to boiler {i+2}"

# Place 3 steam engines
steam_engines = []
for i in range(3):
    engine_position = Position(x=boilers[i].position.x, y=boilers[i].position.y + 3)
    move_to(engine_position)
    steam_engine = place_entity(Prototype.SteamEngine, Direction.RIGHT, engine_position)
    assert steam_engine, f"Failed to place steam engine {i+1}"
    steam_engines.append(steam_engine)
    print(f"Steam engine {i+1} placed at {steam_engine.position}")

# Connect boilers to steam engines
for i in range(3):
    pipes = connect_entities(boilers[i], steam_engines[i], Prototype.Pipe)
    assert pipes, f"Failed to connect boiler {i+1} to steam engine {i+1}"

# Find coal and move to it
coal_position = nearest(Resource.Coal)
move_to(coal_position)

# Place burner mining drill on coal patch
coal_miner = place_entity(Prototype.BurnerMiningDrill, Direction.UP, coal_position)
assert coal_miner, "Failed to place burner mining drill for coal"
print(f"Coal miner placed at {coal_miner.position}")

# Place inserter to feed coal into first boiler
inserter_position = Position(x=coal_miner.position.x + 1, y=coal_miner.position.y)
move_to(inserter_position)
coal_inserter = place_entity(Prototype.BurnerInserter, Direction.LEFT, inserter_position)
assert coal_inserter, "Failed to place inserter for coal"
print(f"Coal inserter placed at {coal_inserter.position}")

# Place electric poles to connect steam engines
poles = []
for i in range(3):
    pole_position = Position(x=steam_engines[i].position.x + 1, y=steam_engines[i].position.y)
    move_to(pole_position)
    pole = place_entity(Prototype.SmallElectricPole, Direction.UP, pole_position)
    assert pole, f"Failed to place electric pole {i+1}"
    poles.append(pole)
    print(f"Electric pole {i+1} placed at {pole.position}")

# Find iron ore and move to it
ore_position = nearest(Resource.IronOre)
move_to(ore_position)

# Place 2 electric mining drills on ore patch
ore_miners = []
for i in range(2):
    miner_position = Position(x=ore_position.x + i*5, y=ore_position.y)
    move_to(miner_position)
    miner = place_entity(Prototype.ElectricMiningDrill, Direction.UP, miner_position)
    assert miner, f"Failed to place electric mining drill {i+1}"
    ore_miners.append(miner)
    print(f"Electric mining drill {i+1} placed at {miner.position}")

# Connect electric mining drills to power network
for miner in ore_miners:
    pole_position = Position(x=miner.position.x + 2, y=miner.position.y + 2)
    move_to(pole_position)
    pole = place_entity(Prototype.SmallElectricPole, Direction.UP, pole_position)
    assert pole, f"Failed to place electric pole for miner at {miner.position}"
    print(