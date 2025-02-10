# move_to

The `move_to` tool allows you to navigate to specific positions in the Factorio world. This guide explains how to use it effectively.

## Basic Usage

```python
move_to(position: Position) -> Position
```

The function returns your final Position after moving.

### Parameters

- `position`: Target Position to move to

### Examples

```python
# Simple movement
new_pos = move_to(Position(x=10, y=10))

# Move to resource
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)

# Move while laying transport belts behind
move_to(target_pos, laying=Prototype.TransportBelt)
```

## Important Rules

1. **Error Handling**
```python
try:
    move_to(position)
except Exception as e:
    print(f"Movement failed: {e}")
```

2. **Path Verification**
```python
# Ensure destination is reachable
target = Position(x=10, y=10)
move_to(target)
```

## Movement Patterns

### 1. Resource Navigation
```python
# Find and move to resources
def move_to_resource(resource_type: Resource):
    resource_pos = nearest(resource_type)
    move_to(resource_pos)
    
# Usage
move_to_resource(Resource.IronOre)
```

### 2. Multi-Point Movement
```python
# Move through multiple points
def move_through_points(positions: list[Position]):
    for pos in positions:
        move_to(pos)
        
points = [
    Position(x=0, y=0),
    Position(x=10, y=0),
    Position(x=10, y=10)
]
move_through_points(points)
```

## Best Practices

1. **Resource Navigation**
```python
# When moving to resources, use nearest() first
resource_pos = nearest(Resource.Coal)
if resource_pos:
    move_to(resource_pos)
```


## Common Patterns

1. **Resource Collection Circuit**
```python
def collect_resources():
    resources = [
        Resource.Coal,
        Resource.IronOre,
        Resource.CopperOre,
        Resource.Stone
    ]
    
    for resource in resources:
        pos = nearest(resource)
        move_to(pos)
        harvest_resource(pos, quantity=10)
```

## Troubleshooting

1. "Cannot move"
   - Check for obstacles in path
   - Verify destination is reachable
   - Ensure coordinates are valid