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

# Place inserter next to a furnace to input items into the furnace
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


## Best Practices

1. **Spacing Guidelines**
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