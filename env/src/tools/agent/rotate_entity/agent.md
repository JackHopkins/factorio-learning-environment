# rotate_entity

The `rotate_entity` tool allows you to change the orientation of placed entities in Factorio. Different entities have different rotation behaviors and requirements.

## Basic Usage

Returns the rotated Entity object.

Rotating inserters - Inserter rotation affects pickup/drop positions
Important: By default inserters take items from entities they are placed next to and place them at the drop_position
Always rotate the inserters the other way if they need to put items into the entity (i.e the entity is at the drop_position)
```python
# place inserter above a chest that takes from the chest
output_inserter = place_entity_next_to(Prototype.BurnerInserter, reference_position=chest_pos, direction = Direction.UP)
print(f"Inserter that takes items from the chest: pickup={inserter.pickup_position}, drop={inserter.drop_position}")
# place inserter left from a chest that puts items into the chest
input_inserter = place_entity_next_to(Prototype.BurnerInserter, reference_position=chest_pos, direction = Direction.LEFT)
# rotate the inserter to put items into the chest
input_inserter = rotate_entity(input_inserter, Direction.RIGHT)
print(f"Inserter that puts item into a chest: pickup={inserter.pickup_position}, drop={inserter.drop_position}")
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
