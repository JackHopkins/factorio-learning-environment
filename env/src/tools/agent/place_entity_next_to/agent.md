# place_entity_next_to

The `place_entity_next_to` tool enables placement of entities relative to other entities. It automatically handles spacing and alignment based on entity dimensions and types.

## Basic Usage

```python
place_entity_next_to(
    entity: Prototype,
    reference_position: Position,
    direction: Direction = Direction.RIGHT,
    spacing: int = 0
) -> Entity
```

Returns the placed Entity object.

### Parameters
- `entity`: Prototype of entity to place
- `reference_position`: Position of reference entity/point
- `direction`: Which direction to place from reference (UP/DOWN/LEFT/RIGHT)
- `spacing`: Additional tiles of space between entities (0 or more)

### Examples
```python

# Place inserter next to a furnace
inserter = place_entity_next_to(
    Prototype.BurnerInserter,
    furnace.position,
    direction=Direction.UP,
    spacing=0
)
```

## Common Entity Combinations
### 1. Getting items from a chemical plant
```python
def create_assembly_line(chemical_plant):
    # Place inserter next to machine to take items from it
    output_inserter = place_entity_next_to(
        Prototype.BurnerInserter,
        chemical_plant.position,
        direction=Direction.LEFT,
        spacing=0
    )
    # insert coal to inserter
    output_inserter = insert_item(Prototype.Coal, output_inserter, quantity = 10)
    # Place chest at inserters drop position to get the items
    output_chest = place_entity(
        Prototype.WoodenChest,
        position = output_inserter.position,
    )
    # log your actions
    print(f"Placed chest at {output_chest.position} to get items from a chemical_plant at {chemical_plant.position}. Inserter that puts items into the chest is at {output_inserter.position}")
```

## Entity-Specific Considerations

### 1. Inserters
```python
# Always use 0 spacing with inserters
def place_inserter(target: Entity, direction: Direction):
    return place_entity_next_to(
        Prototype.BurnerInserter,
        target.position,
        direction=direction,
        spacing=0  # Must be 0 for inserters
    )
```

### 2. Mining Drills
```python
# Ensure mining area overlaps resources
def place_drill_line():
    previous_drill = None
    for i in range(3):
        if not previous_drill:
            drill = place_entity(
                Prototype.ElectricMiningDrill,
                position=ore_position
            )
            print(f"Placed first drill at {drill.position}")
        else:
            drill = place_entity_next_to(
                Prototype.ElectricMiningDrill,
                previous_drill.position,
                direction=Direction.RIGHT,
                spacing=0
            )
            print(f"Placed drill {i} at {drill.position}")
        previous_drill = drill
```


## Best Practices

1. **Spacing Guidelines**
```python
# Use 0 spacing for:
- Inserters
- Adjacent belts
- Direct connections

# Use 1+ spacing for:
- Leaving room for inserters
- Future expansion
- Entity access

# Use 3+ spacing for:
- Room for pipe connections
- Major factory sections
```

## Common Patterns

1. **Input/Output Setup**
```python
def setup_machine_io(machine: Entity):
    # Input inserter
    input_inserter = place_entity_next_to(
        Prototype.BurnerInserter,
        machine.position,
        direction=Direction.LEFT,
        spacing=0
    )
    # rotate inserter to put itemsinto the machine as by defaul it takes from the machine
    input_inserter = rotate_entity(input_inserter, direction = Direction.RIGHT)
    print(f"Placed input inserter at {input_inserter.position} to input items into machine at {machine.position}")
    # Output inserter
    output_inserter = place_entity_next_to(
        Prototype.BurnerInserter,
        machine.position,
        direction=Direction.RIGHT,
        spacing=0
    )
    # dont need to rotate as it takes from the machine
    print(f"Placed output inserter at {output_inserter.position} to get output items from machine at {machine.position}")
    return input_inserter, output_inserter
```