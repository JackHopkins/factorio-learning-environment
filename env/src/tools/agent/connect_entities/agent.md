# connect_entities

The `connect_entities` tool provides functionality to connect different types of Factorio entities using various connection types like transport belts, pipes, power poles and more. This document outlines how to use the tool effectively.

## Core Concepts

The connect_entities tool can connect:
- Transport belts (including underground belts)
- Pipes (including underground pipes) 
- Power poles
- Walls
- Inserters

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
connection_type={Prototype.TransportBelt, Prototype.UndergroundBelt}
```

## Transport Belt Connections

Transport belts require special consideration for direction and flow:

```python
# Connect mining drill output to furnace input
belts = connect_entities(
    drill.drop_position,
    furnace_inserter.pickup_position, 
    connection_type=Prototype.TransportBelt
)

# Belt groups are returned for management
print(f"Created belt line with {len(belts.belts)} belts")
```

Key points:
- Always use inserters between belts and machines/chests
- Connect to inserter pickup/drop positions
- Use underground belts for crossing other belts
- Belt groups maintain direction and flow information

## Pipe Connections

Pipes can connect fluid-handling entities:

```python
# Connect offshore pump to boiler
pipes = connect_entities(
    offshore_pump,
    boiler,
    connection_type=Prototype.Pipe
)

# Underground pipes for crossing
pipes = connect_entities(
    source,
    target,
    connection_type={Prototype.Pipe, Prototype.UndergroundPipe}
)
```

Key points:
- Respects fluid input/output connection points
- Maintains fluid networks
- Underground pipes have limited range
- Pipe groups track fluid system IDs

## Power Pole Connections

Power poles create electrical networks:

```python
# Connect steam engine to electric drill
poles = connect_entities(
    steam_engine,
    drill,
    connection_type=Prototype.SmallElectricPole
)

# Power pole coverage matters
assert poles.poles[0].wire_reach == 7.5
```

Key points:
- Automatically spaces poles based on wire reach
- Creates electrical networks
- Handles pole to entity connections
- Power groups track network IDs

## Inserter Connections

Inserters require rotation consideration:

```python
# Connect two machines with inserter
inserter = connect_entities(
    source_machine,
    target_machine,
    connection_type=Prototype.BurnerInserter
)

# Inserter rotates to face target
assert inserter.direction.value == Direction.DOWN.value
```

**Key points:**
- Automatically rotates to face target
- Requires fuel for burner inserters
- Position considers machine dimensions
- Validates pickup/drop positions

## Best Practices

1. **Pre-check Resources**
```python
inventory = inspect_inventory()
required_count = 10 # Estimate needed entities
assert inventory[Prototype.TransportBelt] >= required_count
```

2. **Error Handling**
```python
try:
    connection = connect_entities(source, target, connection_type=prototype)
except Exception as e:
    print(f"Connection failed: {e}")
    # Handle failure case
```

3. **Entity Groups**
```python
# Work with entity groups
belt_group = connect_entities(source, target, Prototype.TransportBelt)
for belt in belt_group.belts:
    print(f"Belt at {belt.position} flowing {belt.direction}")
```

4. **Spacing Guidelines**
- Use 0 spacing for inserters
- Use 1 spacing for adjacent machines
- Use 3+ spacing for power/fluid setups

5. **Position Handling**
```python
# Adjust positions for better connections
adjusted_pos = Position(
    x=math.floor(pos.x) + 0.5,
    y=math.floor(pos.y) + 0.5
)
```

## Common Patterns

### Resource Mining Setup
```python
# Find resource and place drill
ore_pos = nearest(Resource.IronOre)
drill = place_entity(Prototype.BurnerMiningDrill, ore_pos)

# Place chest for collection
chest = place_entity_next_to(Prototype.WoodenChest, drill.position)

# Connect with transport belt
belts = connect_entities(
    drill.drop_position,
    chest_inserter.pickup_position,
    Prototype.TransportBelt
)
```

### Power Distribution
```python
# Create power infrastructure
steam_engine = place_entity(Prototype.SteamEngine, pos)
drill = place_entity(Prototype.ElectricMiningDrill, ore_pos)

# Connect power
poles = connect_entities(
    steam_engine,
    drill,
    Prototype.SmallElectricPole
)
```

### Fluid Systems
```python
# Water to steam setup
offshore_pump = place_entity(Prototype.OffshorePump, water_pos)
boiler = place_entity_next_to(Prototype.Boiler, pump.position)
steam_engine = place_entity_next_to(Prototype.SteamEngine, boiler.position)

# Connect water flow
water_pipes = connect_entities(offshore_pump, boiler, Prototype.Pipe)
steam_pipes = connect_entities(boiler, steam_engine, Prototype.Pipe)
```

## Troubleshooting

Common issues and solutions:

### 1. Connection Failures
- Verify inventory has required entities
- Check for obstacles in path
- Ensure compatible connection types
- Validate entity positions/spacing

### 2. Flow Issues
- Check entity rotations
- Verify pickup/drop positions
- Ensure power/fuel requirements met
- Validate network connections

### 3. Performance
- Use underground variants for long distances
- Minimize path complexity
- Group similar connections
- Clean up unused connections

### 4. Entity Groups
- Update stale group references
- Handle group merging properly
- Track network IDs
- Clean up disconnected groups
