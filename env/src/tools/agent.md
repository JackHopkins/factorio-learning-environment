# Factorio Implementation Guide

## Core Systems Implementation

### 1. Resource Mining Systems

#### Self-Fueling Coal Mining System
```python
def build_coal_mining_system(game, coal_patch_position):
    # Define building area
    building_box = BuildingBox(width=2, height=4)  # 2 for drill, 4 for drill + inserter + belt
    buildable_coords = game.nearest_buildable(Prototype.BurnerMiningDrill, building_box, coal_patch_position)
    
    # Place drill
    game.move_to(buildable_coords.left_top)
    drill = game.place_entity(Prototype.BurnerMiningDrill, 
                            position=buildable_coords.left_top,
                            direction=Direction.DOWN)
    print(f"Placed BurnerMiningDrill to mine coal at {drill.position}")
    
    # Place self-fueling inserter
    inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                        drill.position,
                                        direction=Direction.DOWN,
                                        spacing=0)
    inserter = game.rotate_entity(inserter, Direction.UP)
    print(f"Placed inserter at {inserter.position} to fuel the drill")
    
    # Connect with belts
    belts = game.connect_entities(drill.drop_position,
                                inserter.pickup_position,
                                Prototype.TransportBelt)
    print(f"Connected drill to inserter with transport belt")
    
    # Bootstrap system
    drill = game.insert_item(Prototype.Coal, drill, quantity=5)
    return drill, inserter, belts
```

#### Shared Resource Mining Line
```python
def build_shared_mining_line(game, ore_position, num_drills=5):
    # Calculate total width needed: 2 tiles per drill * number of drills
    # Height needs 5: 2 for upper drill, 1 for belt, 2 for lower drill
    building_box = BuildingBox(width=2*num_drills, height=5)
    buildable_coords = game.nearest_buildable(Prototype.BurnerMiningDrill, 
                                            building_box, 
                                            ore_position)
    left_top = buildable_coords.left_top
    drills = []
    
    # Place upper drill line
    for i in range(num_drills):
        drill_pos = Position(x=left_top.x + i*2, y=left_top.y)
        game.move_to(drill_pos)
        drill = game.place_entity(Prototype.BurnerMiningDrill,
                                direction=Direction.DOWN,
                                position=drill_pos)
        drills.append(drill)
        print(f"Placed upper drill {i} at {drill.position}")
        
        # Place lower drill
        bottom_drill = game.place_entity_next_to(Prototype.BurnerMiningDrill,
                                               direction=Direction.DOWN,
                                               reference_position=drill.position,
                                               spacing=1)
        bottom_drill = game.rotate_entity(bottom_drill, Direction.UP)
        drills.append(bottom_drill)
        print(f"Placed bottom drill {i} at {bottom_drill.position}")
    
    # Create shared belt line
    x_coords = [drill.drop_position.x for drill in drills]
    belt_start = Position(x=min(x_coords), y=drills[0].drop_position.y)
    belt_end = Position(x=max(x_coords), y=drills[0].drop_position.y)
    
    main_belt = game.connect_entities(belt_start,
                                    belt_end,
                                    Prototype.TransportBelt)
    print(f"Created shared transport belt line for drills")
    
    return drills, main_belt
```

### 2. Smelting Systems

#### Basic Smelting Line
```python
def build_smelting_line(game, input_belt_position, num_furnaces=5):
    # Plan space: each furnace is 2x2, need space for inserters
    building_box = BuildingBox(width=3*num_furnaces, height=4)
    buildable_coords = game.nearest_buildable(Prototype.StoneFurnace,
                                            building_box,
                                            input_belt_position)
    
    furnaces = []
    input_inserters = []
    output_inserters = []
    
    # Place furnace line
    for i in range(num_furnaces):
        # Place furnace
        furnace_pos = Position(x=buildable_coords.left_top.x + i*3,
                             y=buildable_coords.left_top.y)
        game.move_to(furnace_pos)
        furnace = game.place_entity(Prototype.StoneFurnace, position=furnace_pos)
        furnaces.append(furnace)
        print(f"Placed furnace {i} at {furnace.position}")
        
        # Input inserter
        input_inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                                  furnace.position,
                                                  direction=Direction.UP,
                                                  spacing=0)
        input_inserters.append(input_inserter)
        
        # Output inserter
        output_inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                                   furnace.position,
                                                   direction=Direction.DOWN,
                                                   spacing=0)
        output_inserters.append(output_inserter)
        
        # Add initial fuel
        game.insert_item(Prototype.Coal, furnace, quantity=5)
        game.insert_item(Prototype.Coal, input_inserter, quantity=1)
        game.insert_item(Prototype.Coal, output_inserter, quantity=1)
    
    return furnaces, input_inserters, output_inserters
```

### 3. Power Systems

#### Steam Power Setup
```python
def build_steam_power(game, water_position):
    # Place offshore pump
    game.move_to(water_position)
    pump = game.place_entity(Prototype.OffshorePump,
                           position=water_position)
    print(f"Placed offshore pump at {pump.position}")
    
    # Place boiler with spacing
    boiler = game.place_entity_next_to(Prototype.Boiler,
                                      reference_position=pump.position,
                                      direction=Direction.RIGHT,
                                      spacing=2)
    game.insert_item(Prototype.Coal, boiler, quantity=10)
    print(f"Placed boiler at {boiler.position}")
    
    # Place steam engine
    engine = game.place_entity_next_to(Prototype.SteamEngine,
                                      reference_position=boiler.position,
                                      direction=Direction.RIGHT,
                                      spacing=2)
    print(f"Placed steam engine at {engine.position}")
    
    # Connect with pipes
    water_pipes = game.connect_entities(pump, boiler, Prototype.Pipe)
    steam_pipes = game.connect_entities(boiler, engine, Prototype.Pipe)
    
    # Verify power generation
    game.sleep(10)
    engine = game.get_entity(Prototype.SteamEngine, engine.position)
    assert engine.energy > 0, "Steam engine is not generating power"
    
    return pump, boiler, engine
```

### 4. Automated Assembly Systems

#### Basic Assembly Line
```python
def build_assembly_line(game, recipe_prototype, power_source, input_belt):
    # Plan space for assembler and inserters
    building_box = BuildingBox(width=5, height=3)
    buildable_coords = game.nearest_buildable(Prototype.AssemblingMachine1,
                                            building_box,
                                            input_belt.position.right(10))
    
    # Place assembling machine
    game.move_to(buildable_coords.left_top)
    assembler = game.place_entity(Prototype.AssemblingMachine1,
                                position=buildable_coords.left_top)
    print(f"Placed assembling machine at {assembler.position}")
    
    # Set recipe
    game.set_entity_recipe(assembler, recipe_prototype)
    
    # Add input inserter
    input_inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                              assembler.position,
                                              direction=Direction.RIGHT,
                                              spacing=0)
    input_inserter = game.rotate_entity(input_inserter, Direction.LEFT)
    
    # Add output inserter
    output_inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                               assembler.position,
                                               direction=Direction.DOWN,
                                               spacing=0)
    
    # Connect power
    game.connect_entities(power_source,
                         assembler,
                         Prototype.SmallElectricPole)
    
    # Connect input belt
    game.connect_entities(input_belt,
                         input_inserter.pickup_position,
                         Prototype.TransportBelt)
    
    return assembler, input_inserter, output_inserter
```

### 5. Research Systems

#### Basic Research Setup
```python
def build_research_facility(game, power_source):
    # Plan space for lab and inserters
    building_box = BuildingBox(width=4, height=4)
    buildable_coords = game.nearest_buildable(Prototype.Lab,
                                            building_box,
                                            power_source.position.right(10))
    
    # Place lab
    game.move_to(buildable_coords.left_top)
    lab = game.place_entity(Prototype.Lab,
                          position=buildable_coords.left_top)
    print(f"Placed lab at {lab.position}")
    
    # Connect power
    game.connect_entities(power_source,
                         lab,
                         Prototype.SmallElectricPole)
    
    # Add science pack inserter
    inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                        lab.position,
                                        direction=Direction.UP,
                                        spacing=0)
    
    # Place input chest
    chest = game.place_entity_next_to(Prototype.WoodenChest,
                                     inserter.position,
                                     direction=Direction.UP,
                                     spacing=0)
    
    return lab, inserter, chest
```

## Key Implementation Patterns

### 1. Entity Placement Safety
```python
def safe_entity_placement(game, prototype, position):
    try:
        game.move_to(position)
        entity = game.place_entity(prototype, position=position)
        print(f"Placed {prototype} at {position}")
        return entity
    except Exception as e:
        print(f"Failed to place {prototype}: {e}")
        return None
```

### 2. Resource Validation
```python
def validate_resources(game, requirements):
    for item, count in requirements.items():
        inventory_count = game.inspect_inventory()[item]
        if inventory_count < count:
            print(f"Insufficient {item}: need {count}, have {inventory_count}")
            return False
    return True
```

### 3. Power Connection Verification
```python
def verify_power_connection(game, entity, retry_attempts=3):
    for _ in range(retry_attempts):
        game.sleep(5)
        entity = game.get_entity(entity.prototype, entity.position)
        if entity.energy > 0:
            return True
    return False
```

### 4. Belt Connection Pattern
```python
def connect_with_belts(game, source, target, allow_underground=True):
    try:
        if allow_underground and abs(source.position.x - target.position.x) > 5:
            return game.connect_entities(source, target, Prototype.TransportBelt)
        return game.connect_entities(source, target, Prototype.TransportBelt)
    except Exception as e:
        print(f"Failed to connect entities with belts: {e}")
        return None
```

## Error Handling and Recovery

### 1. Entity Status Monitoring
```python
def monitor_entity_status(game, entity, expected_status):
    entity = game.get_entity(entity.prototype, entity.position)
    if entity.status != expected_status:
        print(f"Entity at {entity.position} has unexpected status: {entity.status}")
        return False
    return True
```

### 2. Resource Shortage Recovery
```python
def handle_resource_shortage(game, resource_prototype):
    # Find nearest resource patch
    resource_pos = game.nearest(resource_prototype)
    if not resource_pos:
        print(f"No {resource_prototype} found nearby")
        return False
        
    # Set up emergency mining
    game.move_to(resource_pos)
    drill = game.place_entity(Prototype.BurnerMiningDrill,
                            position=resource_pos)
    game.insert_item(Prototype.Coal, drill, quantity=5)
    return drill
```

### 3. Power System Recovery
```python
def recover_power_system(game, power_entities):
    for entity in power_entities:
        if isinstance(entity, Prototype.Boiler):
            game.insert_item(Prototype.Coal, entity, quantity=10)
        
        game.sleep(5)
        entity = game.get_entity(entity.prototype, entity.position)
        if not verify_power_connection(game, entity):
            print(f"Power system recovery failed for {entity}")
            return False
    return True
```

## Factory Expansion Patterns

### 1. Production Line Duplication
```python
def duplicate_production_line(game, template_entities, offset_position):
    new_entities = []
    for entity in template_entities:
        new_pos = Position(x=entity.position.x + offset_position.x,
                          y=entity.position.y + offset_position.y)
        new_entity = safe_entity_placement(game, entity.prototype, new_pos)
        if new_entity:
            new_entities.append(new_entity)
    return new_entities
```

### 2. Resource Network Extension
```python
def extend_resource_network(game, existing_belt_end, new_consumers):
    for consumer in new_consumers:
        # Create branch from main belt
        branch = game.connect_entities(existing_belt_end,
                                     consumer.position,
                                     Prototype.TransportBelt)
        if not branch:
            return False
        
        # Add inserter for the consumer
        inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                           consumer.position,
                                           direction=Direction.UP,
                                           spacing=0)
        if not inserter:
            return False
            
    return True
```