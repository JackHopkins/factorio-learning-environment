# get_connection_amount

The `get_connection_amount` tool calculates how many entities would be needed to connect two points in Factorio without actually placing the entities. This is useful for planning connections and verifying resource requirements before construction.

## Core Functionality

The tool determines the number of connecting entities (pipes, belts, or power poles) needed between:
- Two positions
- Two entities
- Two entity groups
- Any combination of the above

## Basic Usage

```python
# Get number of entities needed between positions/entities
amount = get_connection_amount(source, target, connection_type=Prototype.X)
```

### Parameters

1. `source`: Starting point (can be Position, Entity, or EntityGroup)
2. `target`: Ending point (can be Position, Entity, or EntityGroup)
3. `connection_type`: Type of connecting entity to use (default: Prototype.Pipe)

### Return Value
Returns an integer representing the number of entities required for the connection.

## Common Use Cases

### 1. Planning Belt Lines
```python
# Calculate belts needed between drill and furnace
belt_count = get_connection_amount(
    drill.drop_position,
    furnace_inserter.pickup_position,
    connection_type=Prototype.TransportBelt
)

# Verify inventory before building
assert inspect_inventory()[Prototype.TransportBelt] >= belt_count, "Not enough belts!"
```

### 2. Power Infrastructure Planning
```python
# Check power pole requirements
pole_count = get_connection_amount(
    steam_engine,
    electric_drill,
    connection_type=Prototype.SmallElectricPole
)

print(f"Need {pole_count} small electric poles to connect power")
```