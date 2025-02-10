# nearest_buildable

The `nearest_buildable` tool helps find valid positions to place entities while respecting space requirements and resource coverage. This guide explains how to use it effectively.

## Basic Usage

```python
nearest_buildable(
    entity: Prototype,
    building_box: BuildingBox,
    center_position: Position
) -> BoundingBox
```

The function returns a BoundingBox object containing buildable area coordinates.

### Parameters
- `entity`: Prototype of entity to place
- `building_box`: BuildingBox defining required area dimensions
- `center_position`: Position to search around

### Return Value
Returns a BoundingBox with these attributes:
- `left_top`: Top-left corner Position
- `right_bottom`: Bottom-right corner Position
- `left_bottom`: Bottom-left corner Position
- `right_top`: Top-right corner Position
- `center()`: Method to get center Position

## Building Box Usage

```python
# Simple 1x1 box for chests
chest_box = BuildingBox(height=1, width=1)

# 3x3 box for mining drills
drill_box = BuildingBox(height=3, width=3)

# Larger box for multiple entities
factory_box = BuildingBox(height=5, width=10)
```

## Common Use Cases

### 1. Basic Entity Placement
```python
# Find place for chest near the origin
chest_box = BuildingBox(height=1, width=1)
buildable_area = nearest_buildable(
    Prototype.WoodenChest,
    chest_box,
    Position(x=0, y=0)
)

# Place at center of buildable area
move_to(buildable_area.center())
chest = place_entity(Prototype.WoodenChest, position=buildable_area.center())
```

### 2. Mining Drill Placement
```python
# Setup mining drill on ore patch
def place_mining_drill(resource_pos: Position):
    # Define area for drill (3x3)
    drill_box = BuildingBox(height=3, width=3)
    
    # Find buildable area
    buildable_area = nearest_buildable(
        Prototype.ElectricMiningDrill,
        drill_box,
        resource_pos
    )
    
    # Place drill
    move_to(buildable_area.center())
    return place_entity(
        Prototype.ElectricMiningDrill,
        position=buildable_area.center()
    )
```

### 3. Power Infrastructure
```python
# Setup steam engine near water
def place_steam_engine(water_pos: Position):
    # Steam engine needs 3x5 area
    engine_box = BuildingBox(width=5, height=3)
    
    buildable_area = nearest_buildable(
        Prototype.SteamEngine,
        engine_box,
        water_pos
    )
    
    move_to(buildable_area.center())
    return place_entity(
        Prototype.SteamEngine,
        position=buildable_area.center(),
        direction=Direction.RIGHT
    )
```

## Best Practices

1. **Size Planning**
```python
# Account for entity dimensions and spacing
def get_building_box(entity_type: Prototype) -> BuildingBox:
    sizes = {
        Prototype.WoodenChest: (1, 1),
        Prototype.ElectricMiningDrill: (3, 3),
        Prototype.SteamEngine: (5, 3),
        Prototype.AssemblingMachine1: (3, 3)
    }
    width, height = sizes.get(entity_type, (1, 1))
    return BuildingBox(width=width, height=height)
```

2. **Resource Coverage**
```python
# For mining drills, ensure ore coverage
def find_mining_position(ore_pos: Position):
    try:
        drill_box = BuildingBox(height=3, width=3)
        area = nearest_buildable(
            Prototype.ElectricMiningDrill,
            drill_box,
            ore_pos
        )
        return area.center()
    except Exception:
        print("No suitable mining position found")
        return None
```

3. **Multiple Entity Placement**
```python
def place_drill_line(ore_pos: Position, count: int):
    drills = []
    current_pos = ore_pos
    
    for _ in range(count):
        drill_box = BuildingBox(height=3, width=3)
        area = nearest_buildable(
            Prototype.ElectricMiningDrill,
            drill_box,
            current_pos
        )
        
        move_to(area.center())
        drill = place_entity(
            Prototype.ElectricMiningDrill,
            position=area.center()
        )
        drills.append(drill)
        
        # Update position for next search
        current_pos = drill.position.right(3)
    
    return drills
```

## Error Handling

1. **No Buildable Position**
```python
try:
    area = nearest_buildable(entity, box, pos)
except Exception as e:
    print(f"Cannot find buildable position: {e}")
    # Handle alternative placement strategy
```

2. **Resource Coverage**
```python
try:
    area = nearest_buildable(
        Prototype.ElectricMiningDrill,
        BuildingBox(height=3, width=3),
        ore_pos
    )
except Exception:
    print("Not enough ore coverage for drill")
```

## Common Patterns

1. **Factory Section Planning**
```python
def plan_factory_section(center: Position, width: int, height: int):
    box = BuildingBox(width=width, height=height)
    try:
        area = nearest_buildable(
            Prototype.AssemblingMachine1,
            box,
            center
        )
        return area
    except Exception:
        print("Cannot fit factory section")
        return None
```

2. **Mining Outpost Setup**
```python
def setup_mining_outpost(ore_pos: Position):
    # Find area for multiple drills
    drill_line = BuildingBox(width=9, height=3)  # Space for 3 drills
    
    area = nearest_buildable(
        Prototype.ElectricMiningDrill,
        drill_line,
        ore_pos
    )
    
    # Place drills along the line
    drills = []
    for x in range(3):
        pos = Position(
            x=area.left_top.x + (x * 3),
            y=area.left_top.y
        )
        move_to(pos)
        drill = place_entity(
            Prototype.ElectricMiningDrill,
            position=pos
        )
        drills.append(drill)
    
    return drills
```

3. **Power Plant Layout**
```python
def plan_power_plant(water_pos: Position):
    # Space for pump, boiler, and engine
    plant_box = BuildingBox(width=15, height=5)
    
    area = nearest_buildable(
        Prototype.SteamEngine,
        plant_box,
        water_pos
    )
    
    return area
```

## Troubleshooting

1. "No buildable position found"
   - Check building box size is appropriate
   - Verify resource coverage for miners