### 2. Power Systems

### Power Infrastructure with steam engine

Power typically involves:
-> Water Source + OffshorePump. This moves water from the water source using the offshore pump
-> Boiler (burning coal). This creates the water from water source into steam
-> SteamEngine. This creates electricity from steam

IMPORTANT: We also need to be very careful and check where we can place boiler and steam engine as they cannot be on water
We will do this in 2 separate code examples
```python
# log your general idea what you will do next
print(f"I will create a power generation setup with a steam engine")
# Power system pattern
move_to(water_position)
# first place offshore pump on the water system
# The offshore pump gets water from the water source and will transport it to the boiler via pipes
offshore_pump = place_entity(Prototype.OffshorePump, position=water_position)
print(f"Placed offshore pump to get water at {offshore_pump.position}") # Placed at Position(x = 1, y = 0)
# Then place the boiler near the offshore pump
# IMPORTANT: We need to be careful as there is water nearby which is unplaceable,
# We do not know where the water is so we will use nearest_buildable for safety and place the entity at the center of the boundingbox
# We will also need to be atleast 4 tiles away from the offshore-pump and otherwise won't have room for connections.

# first get the width and height of a BurnerMiningDrill
print(f"Boiler width: {Prototype.Boiler.WIDTH}, height: {Prototype.Boiler.HEIGHT}") # width 3, height 2
# use the prototype width and height attributes 
# add 4 to ensure no overlap
building_box = BuildingBox(width = Prototype.Boiler.WIDTH + 4, height = Prototype.Boiler.HEIGHT + 4)

coords = nearest_buildable(Prototype.Boiler,building_box,offshore_pump.position)
# place the boiler at the centre coordinate
# first move to the center coordinate
move_to(coords.center)
boiler = place_entity(Prototype.Boiler, position = coords.center, direction = Direction.LEFT)
print(f"Placed boiler to generate steam at {boiler.position}. This will be connected to the offshore pump at {offshore_pump.position}") # placed boiler at Position(x = 10, y = 0)
# add coal to boiler to start the power generation
boiler = insert_item(Prototype.Coal, boiler, 10)
```

```python
boiler = get_entity(Prototype.Boiler, Position(x = 10, y = 0))
# Finally we need to place the steam engine close to the boiler
# use the prototype width and height attributes 
# add 4 to ensure no overlap
building_box = BuildingBox(width = Prototype.SteamEngine.WIDTH + 4, height = Prototype.SteamEngine.HEIGHT + 4)

coords = nearest_buildable(Prototype.SteamEngine,bbox,boiler.position)
# move to the centre coordinate
move_to(coords.center)
# place the steam engine on the centre coordinate
steam_engine = place_entity(Prototype.SteamEngine, 
                            position = coords.center,
                            direction = Direction.LEFT)

print(f"Placed steam_engine to generate electricity at {steam_engine.position}. This will be connected to the boiler at {boiler.position} to generate electricity") # Placed at Position(x = 10, y = 10)
```

```python
offshore_pump = get_entity(Prototype.OffshorePump, Position(x = 1, y = 0))
boiler = get_entity(Prototype.Boiler, Position(x = 10, y = 0))
steam_engine = get_entity(Prototype.SteamEngine, Position(x = 10, y = 10))
# Connect entities in order
water_pipes = connect_entities(offshore_pump, boiler, Prototype.Pipe)
print(f"Connected offshore pump at {offshore_pump.position} to boiler at {boiler.position} with pipes {water_pipes}")
steam_pipes = connect_entities(boiler, steam_engine, Prototype.Pipe)
print(f"Connected boiler at {boiler.position} to steam_engine at {steam_engine.position} with pipes {water_pipes}")

# check that it has power
# sleep for 5 seconds to ensure flow
sleep(5)
# update the entity
steam_engine = get_entity(Prototype.SteamEngine, position = steam_engine.position)
# check that the steam engine is generating power
assert steam_engine.energy > 0, f"Steam engine is not generating power"
print(f"Steam engine at {steam_engine.position} is generating power!")
```



### Powering entities with existing steam engines
To power an entity with existing steam engine, they need to be connected with power poles

Example
Power an existing electric mining drill
```python
# get the steam engine and electric mining drill
steam_engine = get_entity(Prototype.SteamEngine, Position(x = 1, y = 0))
electric_mining_drill = get_entity(Prototype.ElectricMiningDrill, Position(x = 10, y = 0))

# Connect power to the electric mining drill
poles = connect_entities(steam_engine,
                     electric_mining_drill,
                     Prototype.SmallElectricPole)
print(f"Powered electric mining drill at {electric_mining_drill.position} with {poles}")
# wait for 5 seconds to check power
sleep(5)
electric_mining_drill = get_entity(Prototype.ElectricMiningDrill, electric_mining_drill.position)
assert electric_mining_drill.energy > 0, f"electric_mining_drill at {electric_mining_drill.position} is not receiving power" 
print(f"Electric mining drill at {electric_mining_drill.position} has been successfully powered")
```

### Using solar panels for energy
Using solar panels for energy is very easy.
Solar panels need to be just placed on the ground and then can be connected directly to targets requiring power 