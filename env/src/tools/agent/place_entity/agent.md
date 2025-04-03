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
# first moveto target location
move_to(Position(x=0, y=0))
# Basic placement
chest = place_entity(Prototype.WoodenChest, position=Position(x=0, y=0))
# log your actions
print(f"Placed chest at {chest.position}")

# Directional placement
inserter = place_entity(
    Prototype.BurnerInserter,
    direction=Direction.RIGHT,
    position=Position(x=5, y=5)
)
# log your actions
print(f"Placed inserter at {inserter.position} to input into a chest")
```
## Best Practices
- Use nearest buildable to ensure safe placement