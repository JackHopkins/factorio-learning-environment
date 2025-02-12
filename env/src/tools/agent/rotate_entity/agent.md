# rotate_entity

The `rotate_entity` tool allows you to change the orientation of placed entities in Factorio. Different entities have different rotation behaviors and requirements.

## Basic Usage

```python
rotate_entity(entity: Entity, direction: Direction = Direction.UP) -> Entity
```

Returns the rotated Entity object.

### Parameters
- `entity`: Entity to rotate
- `direction`: Target direction (UP/DOWN/LEFT/RIGHT)

### Examples
```python
# Rotating inserters - Inserter rotation affects pickup/drop positions
# Important: By default inserters take from entities they are placed next to
# Always rotate the inserters the other way if they need to take items from an entity
inserter = place_entity(Prototype.BurnerInserter, position=pos, direction = Direction.UP)
print(f"Original inserter: pickup={inserter.pickup_position}, drop={inserter.drop_position}")
inserter = rotate_entity(inserter, Direction.DOWN)
print(f"Rotated inserter: pickup={inserter.pickup_position}, drop={inserter.drop_position}")
```

## Entity-Specific Behaviors

### 1. Assembling Machines, Oil refineris and Chemical Cplants
Always need to set the recipe for assembling machines, oil refineries and chemical plants as their behaviour differs with recipes
```python
# Must set recipe before rotating
assembler = place_entity(Prototype.AssemblingMachine1, position=pos)

# This will fail:
try:
    assembler = rotate_entity(assembler, Direction.RIGHT)
except Exception as e:
    print("Cannot rotate without recipe")

# Correct way:
assembler = set_entity_recipe(assembler, Prototype.IronGearWheel)
assembler = rotate_entity(assembler, Direction.RIGHT)
```

## Common Use Cases

1. **Smelting Setup**
```python
# Place furnace
furnace = place_entity(
    Prototype.StoneFurnace,
    position=start_pos
)
print(f"Put furnace at {furnace.position}")
# Input inserter on the left, facing right
input_inserter = place_entity_next_to(
    Prototype.BurnerInserter,
    furnace.position,
    Direction.LEFT
)
input_inserter = rotate_entity(
    input_inserter,
    Direction.RIGHT
)
print(f"Put input inserter to input items into furnace at {input_inserter.position}")
# Output inserter on the right,
# dont need to rotate as its taking from the furnace
output_inserter = place_entity_next_to(
    Prototype.BurnerInserter,
    furnace.position,
    Direction.RIGHT
)
print(f"Put output inserter to get items from furnace at {output_inserter.position}")
```
