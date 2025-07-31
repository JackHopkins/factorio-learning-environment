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
move_to(water_pos)
# Flexible positioning
pump = place_entity(
    Prototype.OffshorePump,
    position=water_pos
)
# log your actions
print(f"Placed pump at {pump.position}to generate power")
```

### Mining Drills
```python
# Place on resource patch
ore_pos = nearest(Resource.IronOre)
move_to(ore_pos)
drill = place_entity(
    Prototype.BurnerMiningDrill,
    position=ore_pos,
    direction=Direction.DOWN
)
# log your actions
print(f"Placed drill at {drill.position} to mine iron ore")
```

## Best Practices
- Use nearest buildable to ensure safe placement

## Common Patterns

1. **Mining Setup**
You can put chests directly at the drop positions of drills to catch ore, thus creating automatic drilling lines
```python
def setup_mining(resource_pos: Position):
    move_to(resource_pos)
    # Place drill
    # put the drop position down
    drill = place_entity(
        Prototype.BurnerMiningDrill,
        position=resource_pos,
        direction=Direction.DOWN,
    )
    # log your actions
    print(f"Placed drill to mine iron ore at {drill.position}")
    # insert coal to drill
    drill = insert_item(Prototype.Coal, drill, quantity = 10)
    # Place output chest that catches ore
    chest = place_entity(
        Prototype.WoodenChest,
        position=drill.drop_position,
        direction=Direction.DOWN,
    )
    # log your actions
    print(f"Placed chest to catch iron ore at {chest.position}")
    # wait for 5 seconds and check if chest has the ore
    sleep(5)
    # update chest entity
    chest = game.get_entity(Prototype.WoodenChest, chest.position)
    assert inspect_inventory(entity=chest).get(Prototype.IronOre, 0) > 0, f"No iron ore found in chest at {chest.position}"
    return drill, chest
```