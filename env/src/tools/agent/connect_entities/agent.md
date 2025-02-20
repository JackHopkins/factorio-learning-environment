# connect_entities

The `connect_entities` tool provides functionality to connect different types of Factorio entities using various connection types like transport belts, pipes and power poles. This document outlines how to use the tool effectively.

## Core Concepts

The connect_entities tool can connect:
- Transport belts (including underground belts)
- Pipes (including underground pipes) 
- Power poles
- Walls

For each connection type, the tool handles:
- Pathing around obstacles
- Proper entity rotation and orientation
- Network/group management
- Resource requirements verification
- Connection point validation

## Basic Usage

### General Pattern
```python
# Basic connection between two positions or entities
connection = connect_entities(source, target, connection_type=Prototype.X)

# Connection with multiple waypoints
connection = connect_entities(pos1, pos2, pos3, pos4, connection_type=Prototype.X)
```

### Source/Target Types
The source and target can be:
- Positions
- Entities 
- Entity Groups

### Connection Types
You must specify a connection type prototype:
```python
# Single connection type
connection_type=Prototype.TransportBelt

# Multiple compatible connection types 
# If you have UndergroundBelts in inventory, use them to simplify above-ground structures
connection_type={Prototype.TransportBelt, Prototype.UndergroundBelt}
```

## Transport Belt Connections

```python
# Connect mining drill output to a furnace inserter
belts = connect_entities(
    drill,
    furnace_inserter, 
    connection_type=Prototype.TransportBelt
)

# Belt groups are returned for management
print(f"Created belt line with {len(belts.belts)} belts")
```

Key points:
- Always use inserters between belts and machines/chests
- Use underground belts for crossing other belts
- Belt groups maintain direction and flow information

## Pipe Connections

Pipes connect fluid-handling entities:
```python
# Connect water flow with over and underground pipes
water_pipes = connect_entities(offshore_pump, boiler, {Prototype.TransportBelt, Prototype.UndergroundBelt})
print(f"Connected offshore_pump at {offshore_pump.position} to boiler at {boiler.position} with {pipes}")
```

Key points:
- Respects fluid input/output connection points
- Underground pipes have limited range
- Pipe groups track fluid system IDs

## Power Pole Connections

To add power to entities, you need to connect the target entity (drill, assembling machine, oil refinery etc) to a working power source (steam engine, solar panel etc) 
```python
# Connect power
poles = connect_entities(
    steam_engine,
    drill,
    Prototype.SmallElectricPole
)
print(f"Created the connection to power drill at {drill.position} with steam engine at {steam_engine.position}: {poles}")
```

Key points:
- Automatically spaces poles based on wire reach
- Creates electrical networks
- Handles pole to entity connections
- Power groups track network IDs

## Best Practices

1. **Pre-check Resources**
```python
inventory = inspect_inventory()
# use get_connection_amount to see if you have enough
required_count = get_connection_amount(source.position, target.position, connection_type=Prototype.TransportBelt)
assert inventory[Prototype.TransportBelt] >= required_count
```

3. **Entity Groups**
```python
# Work with entity groups
belt_group = connect_entities(source, target, Prototype.TransportBelt)
for belt in belt_group.belts:
    print(f"Belt at {belt.position} flowing {belt.direction}")
```

## Common Patterns

### Many-to-One Connections
When you need to connect multiple sources to a single target with transport belts
1. Establish sources and target
2. Create the main connection by connecting one source to the target with transport belts
3. Connect all remaining sources to the main connection with transport belts

Example: Connecting multiple source inserters to one target inserter
```python
# get the inserter variables
source_inserter_1 = get_entity(Prototype.BurnerInserter, Position(x = 1, y = 2))
source_inserter_2 = get_entity(Prototype.BurnerInserter, Position(x = 3, y = 2))
source_inserter_3 = get_entity(Prototype.BurnerInserter, Position(x = 5, y = 2))
target_inserter = get_entity(Prototype.BurnerInserter, Position(x = 10, y = 28))
# log your general idea what you will do next
print(f"I will create a connection from the inserters at [{source_inserter_1.position}, {source_inserter_2.position}, {source_inserter_3.position}] to the inserter at {target_inserter.position}")
# create the main connection
main_connection = connect_entities(source_inserter_1, 
                                    target_inserter,
                                    Prototype.TransportBelt)
# Print out the whole connection for logs
print(f"Created the main connection between inserter at {source_inserter_1.position} to inserter at {target_inserter.position}: {main_connection}")

# Connect source_inserter_2 and source_inserter_3 to the main connection
secondary_sources = [source_inserter_2, source_inserter_3]
for source in secondary_sources:
    # connect the source to main connection
    # Use the first beltgroup from the main connection to connect to
    # Also override the main_connection to get the newest belt groups
    main_connection = connect_entities(source, 
                                    main_connection,
                                    Prototype.TransportBelt)
    print(f"Extended main connection to include inserter at {source.position}: {main_connection}")
print(f"Final connection after connecting all inserters to target: {main_connection}")
```

When you want to connect entities to existing power pole groups, similar rules apply.

Assume in this example there is a steam engine at Position(x = 1, y = 2) and the drill is at Position(x = 10, y = 28)
```python
# create the main connection
main_power_connection = connect_entities(steam_engine, 
                                    drill_1,
                                    Prototype.SmallElectricPole)
# Print out the whole connection for logs
print(f"Created the main connection to power drill at {drill_1.position} with steam engine at {steam_engine.position}: {main_connection}")

# connect the secondary source to the main power connection
# Use the first ElectricityGroup from the main connection to connect to
# Also override the main_power_connection to get the newest ElectricityGroups
main_power_connection = connect_entities(drill_2, 
                                main_connection,
                                Prototype.SmallElectricPole)
```

## Troubleshooting

Common issues and solutions:

### 1. Connection Failures
- Verify inventory has required entities
- Ensure compatible connection types

### 3. Entity Groups
- Update stale group references
- Handle group merging properly
- Track network IDs
- Clean up disconnected groups
