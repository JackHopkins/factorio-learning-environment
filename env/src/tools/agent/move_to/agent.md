# move_to

The `move_to` tool allows you to navigate to specific positions in the Factorio world. This guide explains how to use it effectively.

## Basic Usage
The function returns your final Position after moving.
```python
# Simple movement
new_pos = move_to(Position(x=10, y=10))

# Move to resource
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
```

## Troubleshooting

1. "Cannot move"
   - Verify destination is reachable (i.e not water)
   - Ensure coordinates are valid