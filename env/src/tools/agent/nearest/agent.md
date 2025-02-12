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

2. **Water Finding**
```python
# Water positions are tile-based
water_pos = nearest(Resource.Water)
# move to water pos
move_to(water_pos)
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

## Troubleshooting

1. "No resource found"
   - Check search radius (500 tiles)
   - Move to explore new areas
   - Verify resource type exists on map

2. "Invalid resource type"
   - Check resource enum spelling
   - Verify resource type is supported
   - Use correct Resource enum