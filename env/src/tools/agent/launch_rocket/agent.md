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

First, establish power and place the silo:
```python
# Set up power generation
water_pos = nearest(Resource.Water)
move_to(water_pos)
pump = place_entity(Prototype.OffshorePump, position=water_pos)
boiler = place_entity_next_to(Prototype.Boiler, pump.position, Direction.DOWN, spacing=5)
engine = place_entity_next_to(Prototype.SteamEngine, boiler.position, Direction.DOWN, spacing=5)

# Connect power infrastructure
connect_entities(pump, boiler, Prototype.Pipe)
connect_entities(boiler, engine, Prototype.Pipe)
insert_item(Prototype.Coal, boiler, quantity=50)

# Place rocket silo
silo = place_entity_next_to(Prototype.RocketSilo, engine.position, Direction.RIGHT, spacing=5)
connect_entities(engine, silo, Prototype.SmallElectricPole)
```

### 2. Setting Up Component Supply

Create input systems for the three required components:
```python
# Setup for Low Density Structures
lds_chest = place_entity_next_to(Prototype.SteelChest, silo.position, Direction.LEFT, spacing=1)
lds_inserter = place_entity_next_to(Prototype.FastInserter, lds_chest.position, Direction.RIGHT)

# Setup for Rocket Fuel
fuel_chest = place_entity_next_to(Prototype.SteelChest, lds_chest.position, Direction.DOWN, spacing=2)
fuel_inserter = place_entity_next_to(Prototype.FastInserter, fuel_chest.position, Direction.RIGHT)

# Setup for Rocket Control Units
rcu_chest = place_entity_next_to(Prototype.SteelChest, lds_chest.position, Direction.UP, spacing=2)
rcu_inserter = place_entity_next_to(Prototype.FastInserter, rcu_chest.position, Direction.RIGHT)

# Power all inserters
for inserter in [lds_inserter, fuel_inserter, rcu_inserter]:
    connect_entities(engine, inserter, Prototype.SmallElectricPole)
```

### 3. Loading Components

Supply the required components:
```python
# Insert rocket components
insert_item(Prototype.RocketFuel, fuel_chest, quantity=100)
insert_item(Prototype.RocketControlUnit, rcu_chest, quantity=100)
insert_item(Prototype.LowDensityStructure, lds_chest, quantity=100)
```

### 4. Monitoring Rocket Construction

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

## Required Components

For each rocket launch you need:
1. 100 Rocket Fuel
2. 100 Rocket Control Units
3. 100 Low Density Structures

## Status Monitoring

Monitor silo.status for these states:
- `EntityStatus.NORMAL` - Initial state
- `EntityStatus.PREPARING_ROCKET_FOR_LAUNCH` - Building rocket
- `EntityStatus.WAITING_TO_LAUNCH_ROCKET` - Ready to launch
- `EntityStatus.LAUNCHING_ROCKET` - Launch in progress
- `EntityStatus.ITEM_INGREDIENT_SHORTAGE` - Needs more components

## Best Practices

1. **Power Management**
```python
# Ensure stable power before starting
engine = place_entity(Prototype.SteamEngine, position=pos)
connect_entities(engine, silo, Prototype.SmallElectricPole)
assert silo.energy > 0, "Silo not receiving power"
```

2. **Component Management**
```python
# Check component availability
inventory = inspect_inventory()
required_items = {
    Prototype.RocketFuel: 100,
    Prototype.RocketControlUnit: 100,
    Prototype.LowDensityStructure: 100
}
has_all = all(inventory.get(item, 0) >= amount 
             for item, amount in required_items.items())
```

3. **Status Verification**
```python
def verify_silo_status(silo: RocketSilo, expected_status: EntityStatus):
    silo = get_entities({Prototype.RocketSilo})[0]  # Get fresh state
    assert silo.status == expected_status, f"Expected {expected_status}, got {silo.status}"
```

## Common Issues and Solutions

1. "No rocket silo found"
   - Verify silo position
   - Check silo is properly placed
   - Ensure silo is powered

2. "Rocket is not ready for launch"
   - Check component supply
   - Verify power connection
   - Wait for construction completion

3. "Cannot launch rocket"
   - Verify silo status is WAITING_TO_LAUNCH_ROCKET
   - Check for proper power supply
   - Ensure no missing components
