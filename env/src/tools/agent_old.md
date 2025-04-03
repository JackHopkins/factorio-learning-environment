# Patterns

## Core Systems Implementation

### 1. Resource Mining Systems

#### Self-Fueling Coal Mining System
```python
def build_self_fueling_coal_mining_system(coal_patch_position):
    # Define building area
    building_box = BuildingBox(width=Prototype.BurnerMiningDrill.WIDTH, height=Prototype.BurnerMiningDrill.HEIGHT + Prototype.BurnerInserter.HEIGHT + Prototype.TransportBelt.HEIGHT)  #  drill width, drill + inserter + belt height
    buildable_coords = nearest_buildable(Prototype.BurnerMiningDrill, building_box, coal_patch_position)
    
    # Place drill
    move_to(buildable_coords.center)
    drill = place_entity(Prototype.BurnerMiningDrill, 
                            position=buildable_coords.center,
                            direction=Direction.DOWN)
    print(f"Placed BurnerMiningDrill to mine coal at {drill.position}")
    
    # Place self-fueling inserter
    inserter = place_entity_next_to(Prototype.BurnerInserter,
                                        drill.position,
                                        direction=Direction.DOWN,
                                        spacing=0)
    inserter = rotate_entity(inserter, Direction.UP)
    print(f"Placed inserter at {inserter.position} to fuel the drill")
    
    # Connect with belts
    belts = connect_entities(drill.drop_position,
                                inserter.pickup_position,
                                Prototype.TransportBelt)
    print(f"Connected drill to inserter with transport belt")
    
    # Bootstrap system
    drill = insert_item(Prototype.Coal, drill, quantity=5)
    return drill, inserter, belts
```

### 2. Power Systems

**Power Infrastructure with steam engine**

Power typically involves:
-> Water Source + OffshorePump
-> Boiler (burning coal)
-> SteamEngine

IMPORTANT: We also need to be very careful and check where we can place boiler and steam engine as they cannot be on water
We will do this in 3 separate code examples
```python
# log your general idea what you will do next
print(f"I will create a power generation setup with a steam engine")
# Power system pattern
move_to(water_position)
# first place offshore pump on the water system
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

### 3. Automated Assembly Systems

#### Basic Assembly Line
Important: Each section of the mine should be atleast 20 spaces further away from the other and have enough room for connections
```python
furnace_output_inserter = get_entity(Prototype.BurnerInserter, Position(x = 9, y = 0))
solar_panel = get_entity(Prototype.SolarPanel, Position(x = 0, y = 0))
# get a position 15 spaces away
assembler_position = Position(x = furnace_output_inserter.x + 15, y = furnace_output_inserter.y)
# Plan space for assembler and inserters, add some buffer
building_box = BuildingBox(width=Prototype.AssemblingMachine1.WIDTH + 2*Prototype.BurnerInserter.WIDTH + 2, height=Prototype.AssemblingMachine1.HEIGHT+ 2)
buildable_coords = nearest_buildable(Prototype.AssemblingMachine1,
                                        building_box,
                                        assembler_position)

# Place assembling machine
move_to(buildable_coords.center)
assembler = place_entity(Prototype.AssemblingMachine1,
                            position=buildable_coords.center,
                            direction = Direction.DOWN)
print(f"Placed assembling machine at {assembler.position}")

# Set recipe
set_entity_recipe(assembler, Prototype.CopperCable)

# Add input inserter
# place it to the right as we added to the width of the building box
assembly_machine_input_inserter = place_entity_next_to(Prototype.BurnerInserter,
                                          assembler.position,
                                          direction=Direction.RIGHT,
                                          spacing=0)
# rotate it to input items into the assembling machine                                          
assembly_machine_input_inserter = rotate_entity(assembly_machine_input_inserter, Direction.LEFT)

# Add output inserter
# put it on the other side of assembling machine
output_inserter = place_entity_next_to(Prototype.BurnerInserter,
                                           assembler.position,
                                           direction=Direction.LEFT,
                                           spacing=0)
output_chest = place_entity(Prototype.WoodenChest, position = output_inserter.drop_position)
# add coal to inserters
output_inserter = insert_item(Prototype.Coal, output_inserter, quantity = 5)
input_inserter = insert_item(Prototype.Coal, input_inserter, quantity = 5)
# Connect power
poles = connect_entities(power_source,
                     assembler,
                     Prototype.SmallElectricPole)
print(f"Powered assembling machine at {assembler.position} with {poles}")
# wait for 5 seconds to check power
sleep(5)
assembler = get_entity(Prototype.AssemblingMachine1, assembler.position)
assert assembler.energy > 0, f"Assembling machine at {assembler.position} is not receiving power" 
# Connect input belt
belts = connect_entities(furnace_output_inserter,
                     assembly_machine_input_inserter,
                     Prototype.TransportBelt)
print(f"Connected assembling machine at {assembler.position} to furnace_output_inserter with {belts}")

# wait for 15 seconds to if structure works and machine is creating copper cables into the output chest
sleep(15)
output_chest = get_entity(Prototype.WoodenChest, output_chest.position)
inventory = inspect_inventory(output_chest)
copper_cables_in_inventory = inventory[Prototype.CopperCable]
assert copper_cables_in_inventory > 0, f"No copper cables created"
```

### 4. Research Systems

#### Basic Research Setup
```python
def build_research_facility(power_source, lab):
    # Connect power
    poles = connect_entities(power_source,
                         lab,
                         Prototype.SmallElectricPole)
    print(f"Powered lab at {lab.position} with {poles}")
    # Add science pack inserter
    # put it to the left of lab
    inserter = place_entity_next_to(Prototype.BurnerInserter,
                                        lab.position,
                                        direction=Direction.LEFT,
                                        spacing=0)
    # rotate it to input items into the lab                                          
    inserter = rotate_entity(inserter, Direction.RIGHT)
    # Place input chest
    chest = place_entity(Prototype.WoodenChest,
                                     inserter.pickup_position,
                                     direction=Direction.LEFT)
    print(f"Placed chest at {chest.position} to input automation packs to lab at {lab.position}")
    
    return lab, inserter, chest
```

# Key Implementation Patterns

## Error Handling and Recovery

### 1. Entity Status Monitoring
```python
def monitor_entity_status(entity, expected_status):
    entity = get_entity(entity.prototype, entity.position)
    if entity.status != expected_status:
        print(f"Entity at {entity.position} has unexpected status: {entity.status}")
        return False
    return True
```


## Chemical plants
Set recipe for chemical plant and connect to input and output storage tanks
```python
# get the chemical plant
chemical_plant = get_entity(Prototype.ChemicalPlant, position=Position(x=0, y=0))

# Set the recipe to craft solid fuel from heavy oil
# IMPORTANT: The recipe for chemical plants and oil refineries must be set before connecting to inputs and outputs
chemical_plant = set_entity_recipe(chemical_plant, RecipeName.HeavyOilCracking)
print(f"Set the recipe of chemical plant at {chemical_plant.position} to HeavyOilCracking")

# get the input storage tank
storage_tank = get_entity(Prototype.StorageTank, position=Position(x=10, y=0))
# connect with underground and overground pipes
# the order matters as the storage tank will be connected to recipe inputs
pipes = connect_entities(storage_tank, chemical_plant, connection_type={Prototype.UndergroundPipe, Prototype.Pipe})
print(f"Connected the input tank at {storage_tank.position} to chemical plant at {chemical_plant.position} with {pipes}")

# get the output storage tank
output_storage_tank = get_entity(Prototype.StorageTank, position=Position(x=-10, y=0))
# connect with underground and overground pipes
# the order matters as the storage tank will be connected to recipe outputs
pipes = connect_entities(chemical_plant, output_storage_tank, connection_type={Prototype.UndergroundPipe, Prototype.Pipe})
print(f"Connected the output tank at {output_storage_tank.position} to chemical plant at {chemical_plant.position} with {pipes}")
```

## Oil Refinery
Set recipe for oil refinery to get petroleum gas
```python
# get the pumpjack
pumpjack = get_entity(Prototype.PumpJack, position=Position(x=-50, y=0))
oil_refinery = get_entity(Prototype.Oilrefinery, position = Position(x = -25, y = 10))

# Set the recipe to basc oil processing
# IMPORTANT: The recipe for chemical plants and oil refineries must be set before connecting to inputs and outputs
oil_refinery = set_entity_recipe(oil_refinery, RecipeName.BasicOilProcessing)
print(f"Set the recipe of oil refinery at {oil_refinery.position} to BasicOilProcessing")

# connect with underground and overground pipes to the pumpjack
pipes = connect_entities(pumpjack, oil_refinery, connection_type={Prototype.UndergroundPipe, Prototype.Pipe})
print(f"Connected the pumpjack at {pumpjack.position} to oil refinery at {oil_refinery.position} with {pipes}")

```


## TIPS WHEN CREATING STRUCTURES
- When a entity has status "WAITING_FOR_SPACE_IN_DESTINATION", it means the there is no space in the drop position. For instance, a mining drill will have status WAITING_FOR_SPACE_IN_DESTINATION when the entities it mines are not being properly collected by a furnace or a chest or transported away from drop position with transport belts
- Make sure to always put 20+ fuel into all entities that require fuel. It's easy to mine more coal, so it's better to insert in abundance 
- Keep it simple! Only use transport belts if you need them. Use chests and furnaces to catch the ore directly from drills
- Inserters put items into entities or take items away from entities. You need to add inserters when items need to be automatically put into entities like chests, assembling machines, furnaces, boilers etc. The only exception is you can put a chest directly at drills drop position, that catches the ore directly or a furnace with place_entity_next_to(drill.drop_position), where the furnace will be fed the ore
- have at least 10 spaces between different factory sections