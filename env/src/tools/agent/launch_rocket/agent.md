# launch_rocket

The `launch_rocket` tool allows you to launch rockets from a rocket silo. This guide explains the complete process of setting up and launching rockets in Factorio.

## Basic Usage

```python
launch_rocket(silo: Union[Position, RocketSilo]) -> RocketSilo
```

The function returns the updated RocketSilo entity.

### Parameters
- `silo`: Either a Position object or RocketSilo entity indicating where to launch from

## Complete Rocket Launch Process

### 1. Setting Up the Rocket Silo

First, place the silo:
```python
# Place rocket silo
silo = place_entity_next_to(Prototype.RocketSilo, engine.position, Direction.RIGHT, spacing=5)
```

## Required Components

For each rocket launch you need:
1. 100 Rocket Fuel
2. 100 Rocket Control Units
3. 100 Low Density Structures


### 2. Monitoring Rocket Construction

Track the silo's status during construction:
```python
# Check initial state
assert silo.rocket_parts == 0
assert silo.launch_count == 0

# Wait for components to be inserted
sleep(100)  # Adjust time based on inserter speed

# Get updated silo state
silo = get_entities({Prototype.RocketSilo})[0]

# Verify construction started
assert silo.status == EntityStatus.PREPARING_ROCKET_FOR_LAUNCH

# Wait for construction completion
sleep(180)  # Adjust based on crafting speed
silo = get_entities({Prototype.RocketSilo})[0]

# Verify rocket is ready
assert silo.status == EntityStatus.WAITING_TO_LAUNCH_ROCKET
```

### 5. Launching the Rocket

Finally, launch the rocket:
```python
# Launch
silo = launch_rocket(silo)

# Verify launch sequence started
assert silo.status == EntityStatus.LAUNCHING_ROCKET

# Wait for launch completion
sleep(10)
silo = get_entities({Prototype.RocketSilo})[0]
```