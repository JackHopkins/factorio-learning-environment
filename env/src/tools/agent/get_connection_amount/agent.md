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

### 3. Fluid Systems Design
```python
# Plan pipe connections
pipe_count = get_connection_amount(
    offshore_pump,
    boiler,
    connection_type=Prototype.Pipe
)

print(f"Pipeline requires {pipe_count} pipes")
```

## Best Practices

1. **Resource Verification**
```python
# Check if we have enough entities before building
def can_build_connection(source, target, prototype):
    needed = get_connection_amount(source, target, prototype)
    available = inspect_inventory()[prototype]
    return available >= needed
```

2. **Position Optimization**
```python
# Find most efficient connection path
def find_best_connection_point(source, possible_targets, prototype):
    return min(
        possible_targets,
        key=lambda pos: get_connection_amount(source, pos, prototype)
    )
```

3. **Cost Estimation**
```python
# Calculate resource requirements for multiple connections
def estimate_total_connections(connection_points, prototype):
    total = 0
    for source, target in connection_points:
        total += get_connection_amount(source, target, prototype)
    return total
```

## Common Patterns

### Factory Planning
```python
# Plan multiple factory sections
def plan_factory_layout(drill_pos, furnace_pos, assembly_pos):
    # Calculate belt requirements
    drill_to_furnace = get_connection_amount(
        drill_pos,
        furnace_pos,
        Prototype.TransportBelt
    )
    
    furnace_to_assembly = get_connection_amount(
        furnace_pos,
        assembly_pos,
        Prototype.TransportBelt
    )
    
    # Calculate power requirements
    power_poles = get_connection_amount(
        steam_engine_pos,
        assembly_pos,
        Prototype.SmallElectricPole
    )
    
    return {
        "belts_needed": drill_to_furnace + furnace_to_assembly,
        "poles_needed": power_poles
    }
```

### Resource Network Planning
```python
# Plan mining outpost connections
def plan_mining_outpost(ore_patch_pos, main_bus_pos):
    belt_count = get_connection_amount(
        ore_patch_pos,
        main_bus_pos,
        Prototype.TransportBelt
    )
    
    power_count = get_connection_amount(
        main_power_pos,
        ore_patch_pos,
        Prototype.SmallElectricPole
    )
    
    return belt_count, power_count
```

## Tips for Effective Usage

1. **Always verify before building**
   - Calculate requirements first
   - Check inventory availability
   - Consider alternative paths if count is too high

2. **Optimize connection paths**
   - Compare different routes
   - Consider underground alternatives
   - Balance distance vs. resource usage

3. **Handle edge cases**
   - Check for obstacles
   - Consider terrain limitations
   - Account for entity dimensions

4. **Resource management**
   - Calculate total requirements upfront
   - Include buffer for repairs/changes
   - Consider alternative connection types

## Common Mistakes to Avoid

1. **Forgetting Entity Dimensions**
   - Remember entities have different sizes
   - Account for inserter spacing
   - Consider connection point locations

2. **Ignoring Terrain**
   - Water bodies block ground connections
   - Cliffs prevent direct paths
   - Resources block building

3. **Overlooking Alternatives**
   - Underground belts might use fewer resources
   - Different power pole types have different ranges
   - Alternative paths might be more efficient

## Debugging Tips

If the connection amount seems incorrect:

1. **Check Positions**
   - Verify source/target coordinates
   - Ensure positions are reachable
   - Check for obstacles

2. **Verify Connection Type**
   - Confirm prototype is appropriate
   - Check entity compatibility
   - Verify connection points exist

3. **Consider Alternatives**
   - Try different connection types
   - Check alternative paths
   - Verify entity orientations