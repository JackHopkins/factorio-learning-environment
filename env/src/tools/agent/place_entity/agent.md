# place_entity

The `place_entity` tool allows you to place entities in the Factorio world while handling direction, positioning, and various entity-specific requirements. This guide explains how to use it effectively.

## Basic Usage

```python
place_entity(
    entity: Prototype,
    direction: Direction = Direction.UP,
    position: Position = Position(x=0, y=0),
    exact: bool = True
) -> Entity
```

Returns the placed Entity object.

### Parameters
- `entity`: Prototype of entity to place
- `direction`: Direction entity should face (default: UP)
- `position`: Where to place entity (default: 0,0)
- `exact`: Whether to require exact positioning (default: True)

### Examples
```python
# Basic placement
chest = place_entity(Prototype.WoodenChest, position=Position(x=0, y=0))

# Directional placement
inserter = place_entity(
    Prototype.BurnerInserter,
    direction=Direction.RIGHT,
    position=Position(x=5, y=5)
)

# Flexible positioning
pump = place_entity(
    Prototype.OffshorePump,
    position=water_pos,
    exact=False
)
```

## Entity-Specific Placement

### 1. Basic Entities (Chests, Furnaces)
```python
# Simple placement
chest = place_entity(Prototype.WoodenChest, position=pos)

# Furnace with direction
furnace = place_entity(
    Prototype.StoneFurnace,
    direction=Direction.UP,
    position=pos
)
```

### 2. Directional Entities (Inserters, Belts)
```python
# Inserter placement
inserter = place_entity(
    Prototype.BurnerInserter,
    direction=Direction.RIGHT,
    position=pos
)

# Transport belt
belt = place_entity(
    Prototype.TransportBelt,
    direction=Direction.DOWN,
    position=pos
)
```

### 3. Mining Drills
```python
# Place on resource patch
ore_pos = nearest(Resource.IronOre)
drill = place_entity(
    Prototype.BurnerMiningDrill,
    position=ore_pos,
    direction=Direction.DOWN
)
```

### 4. Offshore Pumps
```python
# Water-adjacent placement
water_pos = nearest(Resource.Water)
pump = place_entity(
    Prototype.OffshorePump,
    position=water_pos,
    exact=False  # Allow flexible positioning near water
)
```

## Best Practices

1. **Position Verification**
```python
# Check before placing
def safe_place(entity: Prototype, pos: Position) -> Entity:
    try:
        # Move within reach
        move_to(pos)
        # Verify inventory
        if inspect_inventory()[entity] > 0:
            return place_entity(entity, position=pos)
        else:
            raise Exception(f"No {entity} in inventory")
    except Exception as e:
        print(f"Cannot place {entity}: {e}")
        return None
```

2. **Resource Coverage**
```python
# Place mining drill on resources
def place_mining_drill(resource_pos: Position):
    move_to(resource_pos)
    drill = place_entity(
        Prototype.BurnerMiningDrill,
        position=resource_pos,
        exact=False  # Allow adjustment for best resource coverage
    )
    return drill
```

3. **Direction Handling**
```python
def place_with_direction(entity: Prototype, pos: Position, target: Position):
    # Calculate direction based on target
    dx = target.x - pos.x
    dy = target.y - pos.y
    
    if abs(dx) > abs(dy):
        direction = Direction.RIGHT if dx > 0 else Direction.LEFT
    else:
        direction = Direction.DOWN if dy > 0 else Direction.UP
        
    return place_entity(entity, direction=direction, position=pos)
```

## Common Patterns

1. **Mining Setup**
```python
def setup_mining(resource_pos: Position):
    # Place drill
    drill = place_entity(
        Prototype.BurnerMiningDrill,
        position=resource_pos
    )
    
    # Place output chest
    chest = place_entity(
        Prototype.WoodenChest,
        position=drill.drop_position
    )
    
    return drill, chest
```

2. **Belt Line Creation**
```python
def create_belt_line(start: Position, end: Position):
    current = start
    belts = []
    
    while current.x < end.x:
        belt = place_entity(
            Prototype.TransportBelt,
            direction=Direction.RIGHT,
            position=current
        )
        belts.append(belt)
        current = current.right(1)
    
    return belts
```

3. **Power Setup**
```python
def setup_power(water_pos: Position):
    # Place offshore pump by water
    pump = place_entity(
        Prototype.OffshorePump,
        position=water_pos,
        exact=False
    )
    
    # Place boiler
    boiler = place_entity(
        Prototype.Boiler,
        direction=Direction.UP,
        position=pump.position.below(2)
    )
    
    # Place steam engine
    engine = place_entity(
        Prototype.SteamEngine,
        direction=Direction.UP,
        position=boiler.position.below(3)
    )
    
    return pump, boiler, engine
```

## Error Handling

1. **Inventory Checks**
```python
def verify_can_place(entity: Prototype) -> bool:
    inventory = inspect_inventory()
    if inventory[entity] == 0:
        raise Exception(f"No {entity} in inventory")
    return True
```

2. **Position Validation**
```python
def validate_position(pos: Position):
    try:
        # Check if position is reachable
        move_to(pos)
        # Check if position is clear
        return place_entity(entity, position=pos)
    except Exception as e:
        raise Exception(f"Invalid position: {e}")
```

3. **Water Placement**
```python
def safe_water_placement(pump_pos: Position):
    try:
        pump = place_entity(
            Prototype.OffshorePump,
            position=pump_pos,
            exact=False
        )
        return pump
    except Exception as e:
        print(f"Cannot place pump: {e}")
        return None
```

## Special Considerations

1. **Entity Dimensions**
```python
# Account for entity size
def get_clear_position(entity: Prototype, pos: Position):
    building_box = BuildingBox(
        width=3,  # Adjust based on entity
        height=3
    )
    area = nearest_buildable(entity, building_box, pos)
    return area.center()
```

2. **Underground Connections**
```python
def place_underground_belt(start: Position, direction: Direction):
    # Place input
    input_belt = place_entity(
        Prototype.UndergroundBelt,
        direction=direction,
        position=start
    )
    
    # Place output at maximum distance
    output_pos = start.right(4) if direction == Direction.RIGHT else start.left(4)
    output_belt = place_entity(
        Prototype.UndergroundBelt,
        direction=direction,
        position=output_pos
    )
    
    return input_belt, output_belt
```

3. **Resource Optimization**
```python
def optimize_drill_placement(resource_pos: Position):
    # Find position with maximum resource coverage
    bbox = nearest_buildable(
        Prototype.ElectricMiningDrill,
        BuildingBox(width=3, height=3),
        resource_pos
    )
    
    return place_entity(
        Prototype.ElectricMiningDrill,
        position=bbox.center()
    )
```

## Integration with Other Tools

The place_entity tool works well with:

1. `move_to()` - Positioning before placement
2. `nearest()` - Finding resources for placement
3. `inspect_inventory()` - Verifying available items
4. `nearest_buildable()` - Finding valid positions

Example workflow:
```python
def create_mining_outpost():
    # Find resources
    ore_pos = nearest(Resource.IronOre)
    
    # Find buildable area
    area = nearest_buildable(
        Prototype.ElectricMiningDrill,
        BuildingBox(height=3, width=3),
        ore_pos
    )
    
    # Move and place
    move_to(area.center())
    drill = place_entity(
        Prototype.ElectricMiningDrill,
        position=area.center()
    )
    
    return drill
```