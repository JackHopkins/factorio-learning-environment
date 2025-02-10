# pickup_entity

The `pickup_entity` tool allows you to remove entities from the world and return them to your inventory. It can handle single entities, entity groups (like belt lines), and items on the ground.

## Basic Usage

```python
pickup_entity(
    entity: Union[Entity, Prototype, EntityGroup],
    position: Optional[Position] = None
) -> bool
```

Returns True if pickup was successful.

### Parameters
- `entity`: Entity/Prototype to pickup
- `position`: Optional position to pickup from (required for Prototypes)

### Examples
```python
# Pickup using prototype and position
pickup_entity(Prototype.Boiler, Position(x=0, y=0))

# Pickup using entity reference
boiler = place_entity(Prototype.Boiler, position=pos)
pickup_entity(boiler)

# Pickup entity group (like belt lines)
belt_group = connect_entities(start_pos, end_pos, Prototype.TransportBelt)
pickup_entity(belt_group)
```

## Important Rules

1. **Entity vs Position Usage**
```python
# When using Prototype, position is required
pickup_entity(Prototype.Boiler, Position(x=0, y=0))

# When using Entity, position should be None
boiler = place_entity(Prototype.Boiler, position=pos)
pickup_entity(boiler)  # No position needed
```

2. **Inventory Space**
```python
try:
    pickup_entity(entity)
except Exception as e:
    print("Inventory full or other error:", e)
```

3. **Entity Groups**
```python
# Belt groups are picked up automatically
belts = connect_entities(start, end, Prototype.TransportBelt)
pickup_entity(belts)  # Picks up all belts in group
```

## Entity Type Handling

### 1. Single Entities
```python
# Basic entities
furnace = place_entity(Prototype.StoneFurnace, position=pos)
pickup_entity(furnace)

# Using prototype and position
pickup_entity(Prototype.StoneFurnace, furnace.position)
```

### 2. Belt Groups
```python
# Creating and picking up belt line
belt_group = connect_entities(
    Position(x=0, y=0),
    Position(x=10, y=0),
    Prototype.TransportBelt
)
pickup_entity(belt_group)  # Picks up entire line
```

### 3. Pipe Groups
```python
# Creating and picking up pipe network
pipe_group = connect_entities(
    Position(x=0, y=0),
    Position(x=10, y=0),
    Prototype.Pipe
)
pickup_entity(pipe_group)  # Picks up all connected pipes
```

### 4. Underground Entities
```python
# Underground belts handle both ends
underground = place_entity(Prototype.UndergroundBelt, position=pos)
pickup_entity(underground)  # Picks up both entrance and exit
```

## Best Practices

1. **Group Cleanup**
```python
def cleanup_belt_line(belt_group):
    try:
        # First try group pickup
        pickup_entity(belt_group)
    except Exception:
        # Fallback to individual pickup
        for belt in belt_group.belts:
            try:
                pickup_entity(belt)
            except Exception:
                print(f"Failed to pickup belt at {belt.position}")
```

2**Verification**
```python
def verify_pickup(entity_type: Prototype, position: Position):
    initial_count = inspect_inventory()[entity_type]
    pickup_entity(entity_type, position)
    final_count = inspect_inventory()[entity_type]
    return final_count > initial_count
```

## Common Patterns

1. **Factory Deconstruction**
```python
def deconstruct_smelting_line(start_pos: Position):
    # Pick up inserters first
    for inserter in get_entities({Prototype.BurnerInserter}):
        pickup_entity(inserter)
        
    # Then furnaces
    for furnace in get_entities({Prototype.StoneFurnace}):
        pickup_entity(furnace)
        
    # Finally belts
    belts = get_entities({Prototype.TransportBelt})
    for belt in belts:
        pickup_entity(belt)
```


## Error Handling

1. **Full Inventory**
```python
try:
    pickup_entity(entity)
except Exception as e:
    if "inventory is full" in str(e):
        print("Need to make space first")
    else:
        print(f"Other error: {e}")
```

2. **Missing Entity**
```python
try:
    pickup_entity(Prototype.Boiler, position)
except Exception as e:
    if "Couldn't find" in str(e):
        print("Entity not at position")
    else:
        raise
```

3. **Group Pickup Failures**
```python
def safe_group_pickup(group):
    try:
        pickup_entity(group)
    except Exception:
        # Try individual pickups
        for entity in group.entities:
            try:
                pickup_entity(entity)
            except Exception as e:
                print(f"Failed to pickup {entity}: {e}")
```

## Integration with Other Tools

The pickup_entity tool works well with:

1. `place_entity()` - Moving/replacing entities
2. `connect_entities()` - Managing entity groups
3. `inspect_inventory()` - Checking space
4. `get_entities()` - Finding entities to pickup

Example workflow:
```python
def relocate_factory_section(old_pos: Position, new_pos: Position):
    # Get all entities in old location
    entities = get_entities()
    
    # Store their relative positions
    layouts = [(e.position - old_pos, e.prototype) for e in entities]
    
    # Pick everything up
    for entity in entities:
        pickup_entity(entity)
    
    # Rebuild at new location
    for rel_pos, prototype in layouts:
        place_entity(prototype, position=new_pos + rel_pos)
```