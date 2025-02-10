# place_entity_next_to

The `place_entity_next_to` tool enables placement of entities relative to other entities. It automatically handles spacing and alignment based on entity dimensions and types.

## Basic Usage

```python
place_entity_next_to(
    entity: Prototype,
    reference_position: Position,
    direction: Direction = Direction.RIGHT,
    spacing: int = 0
) -> Entity
```

Returns the placed Entity object.

### Parameters
- `entity`: Prototype of entity to place
- `reference_position`: Position of reference entity/point
- `direction`: Which direction to place from reference (UP/DOWN/LEFT/RIGHT)
- `spacing`: Additional tiles of space between entities (0 or more)

### Examples
```python
# Place chest next to drill with no gap
chest = place_entity_next_to(
    Prototype.WoodenChest,
    drill.position,
    direction=Direction.DOWN,
    spacing=0
)

# Place inserter with spacing
inserter = place_entity_next_to(
    Prototype.BurnerInserter,
    furnace.position,
    direction=Direction.UP,
    spacing=1
)
```

## Common Entity Combinations

### 1. Mining Setup
```python
# Place furnace next to mining drill
def setup_mining_outpost():
    # Place drill on ore
    drill = place_entity(
        Prototype.BurnerMiningDrill, 
        position=ore_position
    )
    
    # Place furnace next to drill's output
    furnace = place_entity_next_to(
        Prototype.StoneFurnace,
        reference_position=drill.position,
        direction=Direction.DOWN,
        spacing=0
    )
    
    return drill, furnace
```

### 2. Power Infrastructure
```python
# Setup steam power
def create_power_line():
    # Place boiler near water pump
    boiler = place_entity_next_to(
        Prototype.Boiler,
        pump.position,
        direction=Direction.DOWN,
        spacing=3  # Leave room for pipes
    )
    
    # Place steam engine after boiler
    engine = place_entity_next_to(
        Prototype.SteamEngine,
        boiler.position,
        direction=Direction.DOWN,
        spacing=3
    )
    
    return boiler, engine
```

### 3. Assembly Line
```python
def create_assembly_line():
    # Place inserter next to machine
    input_inserter = place_entity_next_to(
        Prototype.BurnerInserter,
        assembler.position,
        direction=Direction.LEFT,
        spacing=0
    )
    
    # Place chest next to inserter
    input_chest = place_entity_next_to(
        Prototype.WoodenChest,
        input_inserter.position,
        direction=Direction.LEFT,
        spacing=0
    )
```

## Entity-Specific Considerations

### 1. Inserters
```python
# Always use 0 spacing with inserters
def place_inserter(target: Entity, direction: Direction):
    return place_entity_next_to(
        Prototype.BurnerInserter,
        target.position,
        direction=direction,
        spacing=0  # Must be 0 for inserters
    )
```

### 2. Mining Drills
```python
# Ensure mining area overlaps resources
def place_drill_line():
    previous_drill = None
    for i in range(3):
        if not previous_drill:
            drill = place_entity(
                Prototype.ElectricMiningDrill,
                position=ore_position
            )
        else:
            drill = place_entity_next_to(
                Prototype.ElectricMiningDrill,
                previous_drill.position,
                direction=Direction.RIGHT,
                spacing=0
            )
        previous_drill = drill
```


## Best Practices

1. **Spacing Guidelines**
```python
# Use 0 spacing for:
- Inserters
- Adjacent belts
- Direct connections

# Use 1+ spacing for:
- Leaving room for inserters
- Future expansion
- Entity access

# Use 3+ spacing for:
- Pipe connections
- Power setups
- Major factory sections
```

2. **Direction Selection**
```python
def optimize_direction(source: Entity, target: Entity):
    """Choose best direction based on entity types"""
    if isinstance(source, MiningDrill):
        return Direction.DOWN  # Output direction
    elif isinstance(target, Inserter):
        return Direction.UP  # Input direction
    return Direction.RIGHT  # Default
```

3. **Position Verification**
```python
def verify_placement(entity: Entity, ref_pos: Position):
    try:
        return place_entity_next_to(entity, ref_pos)
    except Exception as e:
        if "collision" in str(e):
            # Try alternative direction
            return place_entity_next_to(
                entity,
                ref_pos,
                direction=Direction.opposite(direction)
            )
```

## Common Patterns

1. **Input/Output Setup**
```python
def setup_machine_io(machine: Entity):
    # Input inserter
    input_inserter = place_entity_next_to(
        Prototype.BurnerInserter,
        machine.position,
        direction=Direction.LEFT,
        spacing=0
    )
    
    # Input chest
    input_chest = place_entity_next_to(
        Prototype.WoodenChest,
        input_inserter.position,
        direction=Direction.LEFT,
        spacing=0
    )
    
    # Output inserter
    output_inserter = place_entity_next_to(
        Prototype.BurnerInserter,
        machine.position,
        direction=Direction.RIGHT,
        spacing=0
    )
    
    return input_inserter, input_chest, output_inserter
```

2. **Production Line**
```python
def create_production_line(start_pos: Position, machines: int):
    entities = []
    current = start_pos
    
    for i in range(machines):
        machine = place_entity_next_to(
            Prototype.AssemblingMachine1,
            current,
            direction=Direction.RIGHT,
            spacing=2  # Space for inserters
        )
        entities.append(machine)
        current = machine.position
        
    return entities
```

## Error Handling

1. **Collision Detection**
```python
try:
    entity = place_entity_next_to(prototype, position)
except Exception as e:
    if "collision" in str(e):
        print("Space already occupied")
    elif "water" in str(e):
        print("Cannot place on water")
    else:
        raise
```

2. **Resource Coverage**
```python
try:
    drill = place_entity_next_to(
        Prototype.ElectricMiningDrill,
        reference_position
    )
except Exception as e:
    if "no resources found" in str(e):
        print("Must place drill over resources")
```