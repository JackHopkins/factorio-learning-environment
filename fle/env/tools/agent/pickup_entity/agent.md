# pickup_entity

The `pickup_entity` tool allows you to remove entities from the world and return them to your inventory. It can handle single entities, entity groups (like belt lines), and items on the ground.

## Basic Usage

```python
pickup_entity(
    entity: Union[Entity, Prototype, EntityGroup],
    position: Optional[Position] = None
) -> bool
```

Returns True if pickup was successful.

### Parameters
- `entity`: Entity/Prototype to pickup
- `position`: Optional position to pickup from (required for Prototypes)

### Examples
```python
# Pickup using prototype and position
pickup_entity(Prototype.Boiler, Position(x=0, y=0))

# Pickup using entity reference
boiler = place_entity(Prototype.Boiler, position=pos)
pickup_entity(boiler)

# Pickup entity group (like belt lines)
# Belt groups are picked up automatically
belt_group = connect_entities(start_pos, end_pos, Prototype.TransportBelt)
pickup_entity(belt_group)  # Picks up all belts in group

# same for underground belts
belt_group = connect_entities(start_pos, end_pos, Prototype.UndergroundBelt)
pickup_entity(belt_group)  # Picks up all belts in group
```

## Best Practices

1. **Group Cleanup**
```python
def cleanup_belt_line(belt_group):
    try:
        # First try group pickup
        pickup_entity(belt_group)
    except Exception:
        # Fallback to individual pickup
        for belt in belt_group.belts:
            try:
                pickup_entity(belt)
            except Exception:
                print(f"Failed to pickup belt at {belt.position}")
```