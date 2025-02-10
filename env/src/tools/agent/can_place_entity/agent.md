
# can_place_entity

## Overview
`can_place_entity` is a utility function that checks whether an entity can be placed at a specific position in Factorio. It verifies various placement conditions including:
- Player reach distance
- Entity existence in inventory
- Collision with other entities
- Terrain compatibility (e.g., water for offshore pumps)
- Space requirements

## Basic Usage

```python
# Basic syntax
can_place = can_place_entity(
    entity: Prototype,  # The entity type to place
    direction: Direction = Direction.UP,  # Optional direction
    position: Position = Position(x=0, y=0)  # Position to check
) -> bool
```

## Examples

1. Basic placement check:
```python
# Check if we can place a pipe at (5,0)
can_place = can_place_entity(
    Prototype.Pipe, 
    position=Position(x=5, y=0)
)
if can_place:
    place_entity(Prototype.Pipe, position=Position(x=5, y=0))
```

2. Check with direction:
```python
# Check if we can place a mining drill facing down
can_place = can_place_entity(
    Prototype.BurnerMiningDrill,
    direction=Direction.DOWN,
    position=Position(x=0, y=0)
)
```

## Common Use Cases

1. Pre-checking resource patches:
```python
copper_ore = nearest(Resource.CopperOre)
can_build = can_place_entity(
    Prototype.BurnerMiningDrill,
    position=copper_ore
)
if can_build:
    move_to(copper_ore)
    place_entity(Prototype.BurnerMiningDrill, position=copper_ore)
```

2. Validating build locations:
```python
# Check before attempting to place large entities
target_pos = Position(x=10, y=10)
if can_place_entity(Prototype.SteamEngine, position=target_pos):
    move_to(target_pos)
    place_entity(Prototype.SteamEngine, position=target_pos)
else:
    print("Cannot place steam engine at target position")
```

## Important Considerations

1. Player Distance
- Checks fail if the target position is beyond the player's reach
- Always move close enough before checking placement

2. Entity Collisions
- Checks for existing entities in the target area
- Returns False if there would be a collision

3. Special Cases
- Offshore pumps require water tiles
- Some entities have specific placement requirements

## Best Practices

1. Always check before placing:
```python
if can_place_entity(entity, position=pos):
    move_to(pos)
    place_entity(entity, position=pos)
else:
    # Handle failed placement
```

2. Consider direction requirements:
```python
# For directional entities like inserters
if can_place_entity(
    Prototype.BurnerInserter, 
    direction=Direction.DOWN,
    position=pos
):
    # Safe to place
```

3. Use with error handling:
```python
try:
    if can_place_entity(entity, position=pos):
        place_entity(entity, position=pos)
except Exception as e:
    print(f"Placement check failed: {e}")
```