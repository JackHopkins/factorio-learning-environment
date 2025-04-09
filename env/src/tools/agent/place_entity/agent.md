# place_entity

The `place_entity` tool allows you to place entities in the Factorio world while handling direction, positioning, and various entity-specific requirements. This guide explains how to use it effectively.

## Basic Usage

```python
# first move to target location
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