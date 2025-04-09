# get_connection_amount

The `get_connection_amount` tool calculates how many entities would be needed to connect two points in Factorio without actually placing the entities. This is useful for planning connections and verifying resource requirements before construction.

## Core Functionality

The tool determines the number of connecting entities (pipes, belts, or power poles) needed between:
- Two positions
- Two entities
- Two entity groups
- Any combination of the above

## Basic Usage

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