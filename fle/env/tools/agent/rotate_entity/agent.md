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
