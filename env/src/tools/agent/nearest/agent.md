# nearest

The `nearest` tool finds the closest entity or resource relative to your current position in Factorio. This guide explains how to use it effectively.

## Basic Usage

```python
nearest(type: Union[Prototype, Resource]) -> Position
```

The function returns a Position object with the coordinates of the nearest entity or resource.

### Parameters
- `type`: Resource or Prototype to find (e.g., Resource.Coal, Resource.Water)

### Examples
```python
# Find nearest coal
coal_pos = nearest(Resource.Coal)

# Find nearest iron ore
iron_pos = nearest(Resource.IronOre)

# Find nearest water
water_pos = nearest(Resource.Water)
```

## Supported Resource Types

### Basic Resources
```python
# Ores
nearest(Resource.Coal)
nearest(Resource.IronOre)
nearest(Resource.CopperOre)
nearest(Resource.Stone)
nearest(Resource.UraniumOre)

# Fluids
nearest(Resource.Water)
nearest(Resource.CrudeOil)

# Natural
nearest(Resource.Wood)  # Finds nearest tree
```

## Important Behavior

1. **Search Range**
```python
# Searches within 500 tiles of player position
# Will raise exception if nothing found:
try:
    resource_pos = nearest(Resource.Coal)
except Exception as e:
    print("No coal within 500 tiles")
```

2. **Position Accuracy**
```python
# Returns positions on the resource grid
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)  # Will move to exact resource position
```

3. **Water Finding**
```python
# Water positions are tile-based
water_pos = nearest(Resource.Water)
# Use for placing offshore pumps
pump = place_entity(Prototype.OffshorePump, position=water_pos)
```

## Common Patterns

1. **Resource Collection Pattern**
```python
def collect_resource(resource_type: Resource, amount: int):
    # Find resource
    resource_pos = nearest(resource_type)
    # Move to it
    move_to(resource_pos)
    # Harvest it
    harvest_resource(resource_pos, amount)
```

2. **Power Setup Pattern**
```python
def setup_power():
    # Find water for offshore pump
    water_pos = nearest(Resource.Water)
    move_to(water_pos)
    
    # Place power infrastructure
    pump = place_entity(Prototype.OffshorePump, position=water_pos)
    boiler = place_entity_next_to(Prototype.Boiler, pump.position, Direction.DOWN)
    engine = place_entity_next_to(Prototype.SteamEngine, boiler.position, Direction.DOWN)
```

3. **Resource Verification Pattern**
```python
def verify_resources_available():
    required_resources = [
        Resource.Coal,
        Resource.IronOre,
        Resource.CopperOre,
        Resource.Stone
    ]
    
    for resource in required_resources:
        try:
            pos = nearest(resource)
            print(f"Found {resource} at {pos}")
        except Exception:
            print(f"Missing required resource: {resource}")
```

## Best Practices

1. **Error Handling**
```python
try:
    resource_pos = nearest(Resource.Coal)
except Exception as e:
    print(f"Could not find resource: {e}")
    # Handle missing resource case
```

2**Resource Distance Checking**
```python
def is_resource_close(resource_type: Resource, max_distance: float = 50):
    try:
        pos = nearest(resource_type)
        player_pos = Position(x=0, y=0)  # Current position
        distance = ((pos.x - player_pos.x)**2 + (pos.y - player_pos.y)**2)**0.5
        return distance <= max_distance
    except:
        return False
```

Example workflow:
```python
# Complete mining setup workflow
def setup_mining(resource_type: Resource):
    # Find resource
    resource_pos = nearest(resource_type)
    
    # Move to location
    move_to(resource_pos)
    
    # Place mining drill
    drill = place_entity(Prototype.BurnerMiningDrill, position=resource_pos)
    
    # Place chest for output
    chest = place_entity_next_to(
        Prototype.WoodenChest,
        drill.position,
        Direction.DOWN
    )
    
    return drill, chest
```

## Troubleshooting

1. "No resource found"
   - Check search radius (500 tiles)
   - Move to explore new areas
   - Verify resource type exists on map

2. "Invalid resource type"
   - Check resource enum spelling
   - Verify resource type is supported
   - Use correct Resource enum

3. Position accuracy
   - Positions are grid-aligned
   - Water positions are tile-based
   - Use returned positions directly