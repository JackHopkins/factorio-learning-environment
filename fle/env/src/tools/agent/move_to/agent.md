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
```
## Movement Patterns

### 1. Resource Navigation
```python
move_to(nearest(IronOre))
```

### 2. Move before placing
always need to move to the position where you need to place the entity
```python
move_to(Position(x = 0, y = 0))
chest = place_entity(Prototypw.WoodenChest, position = Position(x = 0, y = 0))
```

## Troubleshooting

1. "Cannot move"
   - Verify destination is reachable (i.e not water)
   - Ensure coordinates are valid