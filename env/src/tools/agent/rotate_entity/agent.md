# rotate_entity

The `rotate_entity` tool allows you to change the orientation of placed entities in Factorio. Different entities have different rotation behaviors and requirements.

## Basic Usage

```python
rotate_entity(entity: Entity, direction: Direction = Direction.UP) -> Entity
```

Returns the rotated Entity object.

### Parameters
- `entity`: Entity to rotate
- `direction`: Target direction (UP/DOWN/LEFT/RIGHT)

### Examples
```python
# Basic rotation
belt = place_entity(Prototype.TransportBelt, position=pos)
belt = rotate_entity(belt, Direction.RIGHT)

# Rotating inserter
inserter = place_entity(Prototype.BurnerInserter, position=pos)
inserter = rotate_entity(inserter, Direction.DOWN)
```

## Entity-Specific Behaviors

### 1. Transport Belts
```python
# Belt rotation affects input/output positions
belt = place_entity(Prototype.TransportBelt, position=pos)
print(f"Original: in={belt.input_position}, out={belt.output_position}")

belt = rotate_entity(belt, Direction.DOWN)
print(f"Rotated: in={belt.input_position}, out={belt.output_position}")
```

### 2. Inserters
```python
# Inserter rotation affects pickup/drop positions
inserter = place_entity(Prototype.BurnerInserter, position=pos)
print(f"Original: pickup={inserter.pickup_position}, drop={inserter.drop_position}")

inserter = rotate_entity(inserter, Direction.LEFT)
print(f"Rotated: pickup={inserter.pickup_position}, drop={inserter.drop_position}")
```

### 3. Assembling Machines
```python
# Must set recipe before rotating
assembler = place_entity(Prototype.AssemblingMachine1, position=pos)

# This will fail:
try:
    assembler = rotate_entity(assembler, Direction.RIGHT)
except Exception as e:
    print("Cannot rotate without recipe")

# Correct way:
assembler = set_entity_recipe(assembler, Prototype.IronGearWheel)
assembler = rotate_entity(assembler, Direction.RIGHT)
```

## Common Patterns

1. **Aligning Input/Output**
```python
def align_entities(source: Entity, target: Entity):
    # Calculate desired direction
    dx = target.position.x - source.position.x
    dy = target.position.y - source.position.y
    
    if abs(dx) > abs(dy):
        direction = Direction.RIGHT if dx > 0 else Direction.LEFT
    else:
        direction = Direction.DOWN if dy > 0 else Direction.UP
        
    return rotate_entity(source, direction)
```


2. **Inserter Configuration**
```python
def configure_inserter(inserter: Entity, source: Entity, target: Entity):
    # Calculate direction based on source/target positions
    dx = target.position.x - source.position.x
    dy = target.position.y - source.position.y
    
    if abs(dx) > abs(dy):
        direction = Direction.RIGHT if dx > 0 else Direction.LEFT
    else:
        direction = Direction.DOWN if dy > 0 else Direction.UP
        
    return rotate_entity(inserter, direction)
```

## Best Practices

1. **Update References**
```python
# Always update entity reference after rotation
inserter = place_entity(Prototype.BurnerInserter, position=pos)
inserter = rotate_entity(inserter, Direction.RIGHT)  # Update reference
```

2. **Verify Rotation**
```python
def verify_rotation(entity: Entity, target_direction: Direction):
    rotated = rotate_entity(entity, target_direction)
    if rotated.direction != target_direction:
        raise Exception(f"Rotation failed: {entity} to {target_direction}")
    return rotated
```

3. **Handle Recipe Requirements**
```python
def safe_rotate_assembler(assembler: Entity, direction: Direction):
    try:
        return rotate_entity(assembler, direction)
    except Exception as e:
        if "recipe" in str(e):
            assembler = set_entity_recipe(assembler, Prototype.IronGearWheel)
            return rotate_entity(assembler, direction)
        raise
```

## Error Handling

1. **Recipe Requirements**
```python
def rotate_production_machine(machine: Entity, direction: Direction):
    try:
        return rotate_entity(machine, direction)
    except Exception as e:
        if "Set the recipe first" in str(e):
            print("Machine requires recipe before rotation")
            return machine
        raise
```


## Common Use Cases

1. **Production Line Setup**
```python
def setup_assembly_line():
    # Place and orient machines
    assembler = place_entity(
        Prototype.AssemblingMachine1,
        position=pos
    )
    assembler = set_entity_recipe(
        assembler,
        Prototype.IronGearWheel
    )
    
    # Orient input inserter
    input_inserter = place_entity_next_to(
        Prototype.BurnerInserter,
        assembler.position,
        Direction.LEFT
    )
    input_inserter = rotate_entity(
        input_inserter,
        Direction.RIGHT  # Face assembler
    )
    
    # Orient output inserter
    output_inserter = place_entity_next_to(
        Prototype.BurnerInserter,
        assembler.position,
        Direction.RIGHT
    )
    output_inserter = rotate_entity(
        output_inserter,
        Direction.LEFT  # Face away from assembler
    )
```

2. **Smelting Setup**
```python
def setup_smelting_line(start_pos: Position):
    # Place furnace
    furnace = place_entity(
        Prototype.StoneFurnace,
        position=start_pos
    )
    
    # Input inserter on the left, facing right
    input_inserter = place_entity_next_to(
        Prototype.BurnerInserter,
        furnace.position,
        Direction.LEFT
    )
    input_inserter = rotate_entity(
        input_inserter,
        Direction.RIGHT
    )
    
    # Output inserter on the right, facing left
    output_inserter = place_entity_next_to(
        Prototype.BurnerInserter,
        furnace.position,
        Direction.RIGHT
    )
    output_inserter = rotate_entity(
        output_inserter,
        Direction.LEFT
    )
    
    return furnace, input_inserter, output_inserter
```
