# print

The `print` tool allows you to output information about game state, entities, and other objects to stdout. This is essential for debugging, monitoring game state, and verifying operations.

## Basic Usage

```python
print(*args) -> str
```

Returns a string representation of the printed message.

### Parameters
- `*args`: Variable number of objects to print

### Supported Types
- Entity objects
- Inventory objects
- Dictionaries
- Booleans
- Strings
- Position objects
- Lists
- Tuples
- Any object with a `dict()` method (BaseModel derivatives)

## Common Use Cases

### 1. Entity Information
```python
# Print entity details
drill = place_entity(Prototype.BurnerMiningDrill, position=pos)
print(drill)  # Shows position, direction, status, etc.

# Print multiple entities
furnace = place_entity(Prototype.StoneFurnace, position=pos)
print(drill, furnace)  # Shows details of both entities
```

### 2. Inventory Monitoring
```python
# Check player inventory
inventory = inspect_inventory()
print(inventory)  # Shows all items and quantities

# Check entity inventory
chest = place_entity(Prototype.WoodenChest, position=pos)
chest_inventory = inspect_inventory(chest)
print(chest_inventory)  # Shows chest contents
```

### 3. Position Tracking
```python
# Print positions
resource_pos = nearest(Resource.Coal)
print(resource_pos)  # Shows x, y coordinates

# Print position calculations
target = Position(x=resource_pos.x + 2, y=resource_pos.y)
print("Original:", resource_pos, "Target:", target)
```

## Best Practices

1. **Operation Verification**
```python
def verify_placement(entity: Entity, pos: Position):
    print(f"Attempting to place {entity} at {pos}")
    try:
        placed = place_entity(entity, position=pos)
        print(f"Successfully placed: {placed}")
        return placed
    except Exception as e:
        print(f"Placement failed: {e}")
        return None
```

2. **Resource Management**
```python
def monitor_resources():
    inventory = inspect_inventory()
    print("Current resources:")
    if inventory[Prototype.Coal] < 10:
        print("Low on coal:", inventory[Prototype.Coal])
    if inventory[Prototype.IronPlate] < 20:
        print("Low on iron plates:", inventory[Prototype.IronPlate])
```

3. **State Changes**
```python
def track_entity_state(entity: Entity):
    print(f"Initial state: {entity}")
    # Perform operations
    entity = insert_item(Prototype.Coal, entity, 10)
    print(f"After fuel addition: {entity}")
```

## Common Patterns

1. **Operation Logging**
```python
def setup_mining_operation():
    # Log each step
    print("Starting mining setup...")
    
    drill = place_entity(Prototype.BurnerMiningDrill, position=pos)
    print(f"Placed drill at {drill.position}")
    
    chest = place_entity_next_to(
        Prototype.WoodenChest,
        drill.position,
        direction=Direction.DOWN
    )
    print(f"Added output chest at {chest.position}")
    
    print("Mining setup complete")
```

2. **Status Monitoring**
```python
def check_production_line(entities: list[Entity]):
    print("Checking production line status:")
    for entity in entities:
        print(f"{entity.prototype}: {entity.status}")
        
        if hasattr(entity, 'energy'):
            print(f"Power level: {entity.energy}")
            
        if hasattr(entity, 'inventory'):
            print(f"Inventory: {inspect_inventory(entity)}")
```

3. **Debug Information**
```python
def debug_entity_placement(entity: Prototype, pos: Position):
    print(f"Debug info for {entity} placement:")
    print(f"Target position: {pos}")
    
    inventory = inspect_inventory()
    print(f"Available in inventory: {inventory[entity]}")
    
    try:
        placed = place_entity(entity, position=pos)
        print(f"Placement successful: {placed}")
    except Exception as e:
        print(f"Placement failed: {e}")
```

## Error Handling

1. **Print in Try-Except Blocks**
```python
try:
    result = potentially_risky_operation()
    print("Operation succeeded:", result)
except Exception as e:
    print("Operation failed:", e)
    print("Current state:", get_relevant_state())
```

2. **Validation Checks**
```python
def validate_entity(entity: Entity):
    if not entity:
        print("Entity is None")
        return False
        
    print("Validating entity:", entity)
    if entity.status == EntityStatus.NO_POWER:
        print("Entity has no power")
    elif entity.status == EntityStatus.NO_FUEL:
        print("Entity needs fuel")
        
    return entity.status == EntityStatus.WORKING
```

## Integration Examples

1. **Construction Monitoring**
```python
def build_power_system():
    print("Starting power system construction")
    
    # Track each component
    pump = place_entity(Prototype.OffshorePump, position=water_pos)
    print("Pump placed:", pump)
    
    boiler = place_entity_next_to(
        Prototype.Boiler,
        pump.position,
        direction=Direction.DOWN
    )
    print("Boiler placed:", boiler)
    
    engine = place_entity_next_to(
        Prototype.SteamEngine,
        boiler.position,
        direction=Direction.DOWN
    )
    print("Steam engine placed:", engine)
    
    # Print final status
    print("Power system status:")
    print(f"Pump: {pump.status}")
    print(f"Boiler: {boiler.status}")
    print(f"Engine: {engine.status}")
```

Remember to use print statements strategically to track important state changes and verify operations are working as expected, but avoid excessive printing that could clutter the output.