# inspect_inventory

The `inspect_inventory` tool allows you to check the contents of your own inventory or any entity's inventory (chests, furnaces, assembling machines, etc). This guide explains how to use it effectively.

## Basic Usage

```python
inspect_inventory(entity: Optional[Union[Entity, Position]] = None) -> Inventory
```

The function returns an Inventory object that can be queried using Prototype objects.

### Parameters

- `entity`: Optional Entity or Position to inspect (if None, inspects player inventory)

### Return Value

Returns an Inventory object that can be accessed in two ways:
```python
inventory = inspect_inventory()
# Using [] syntax
coal_count = inventory[Prototype.Coal]  # Returns 0 if not present

# Using get() method
coal_count = inventory.get(Prototype.Coal, 0)  # Second argument is default value
```

## Common Usage Patterns

1. **Check Player Inventory**
```python
# Check your own inventory
inventory = inspect_inventory()
coal_count = inventory[Prototype.Coal]
iron_plates = inventory[Prototype.IronPlate]
```

2. **Check Entity Inventory**
```python
# Check chest contents
chest = place_entity(Prototype.IronChest, position=pos)
chest_inventory = inspect_inventory(entity=chest)
items_in_chest = chest_inventory[Prototype.IronPlate]
```

3. **Check Furnace Contents**
```python
# Inspect furnace for both input and output items
furnace = place_entity(Prototype.StoneFurnace, position=pos)
furnace_inventory = inspect_inventory(entity=furnace)
ore_count = furnace_inventory[Prototype.IronOre]
plate_count = furnace_inventory[Prototype.IronPlate]
```

4. **Check Assembling Machine**
```python
# Check both input and output inventories
machine = place_entity(Prototype.AssemblingMachine1, position=pos)
machine_inventory = inspect_inventory(entity=machine)
input_count = machine_inventory[Prototype.IronPlate]
output_count = machine_inventory[Prototype.IronGearWheel]
```

## Best Practices

1. **Always Check Before Operations**
```python
# Check inventory before crafting
inventory = inspect_inventory()
if inventory[Prototype.IronPlate] >= 5:
    craft_item(Prototype.IronGearWheel)
```

2. **Verify Resource Availability**
```python
# Check if you have enough resources
inventory = inspect_inventory()
required_items = {
    Prototype.IronPlate: 10,
    Prototype.Coal: 5
}

has_all = all(inventory.get(item, 0) >= amount 
             for item, amount in required_items.items())
```

3. **Monitor Entity Contents**
```python
# Check furnace operation
furnace_inventory = inspect_inventory(entity=furnace)
if furnace_inventory[Prototype.Coal] < 5:
    furnace = insert_item(Prototype.Coal, furnace, 10)
```

## Entity-Specific Behavior

### 1. Chests
```python
chest = place_entity(Prototype.IronChest, position=pos)
chest_inventory = inspect_inventory(entity=chest)
# Returns combined inventory of all items
```

### 2. Furnaces
```python
furnace = place_entity(Prototype.StoneFurnace, position=pos)
furnace_inventory = inspect_inventory(entity=furnace)
# Returns combined inventory of:
# - Input slot (ores/raw materials)
# - Fuel slot (coal/wood)
# - Output slot (plates/products)
```

### 3. Assembling Machines
```python
machine = place_entity(Prototype.AssemblingMachine1, position=pos)
machine_inventory = inspect_inventory(entity=machine)
# Returns combined inventory of:
# - Input inventory (ingredients)
# - Output inventory (products)
```

### 4. Labs
```python
lab = place_entity(Prototype.Lab, position=pos)
lab_inventory = inspect_inventory(entity=lab)
# Returns science pack inventory
```

## Error Handling

1. **Handle Missing Entities**
```python
try:
    inventory = inspect_inventory(entity=position)
except Exception as e:
    print(f"Could not inspect inventory: {e}")
```

2. **Handle Empty Inventories**
```python
inventory = inspect_inventory()
coal_count = inventory.get(Prototype.Coal, 0)  # Safe access with default
```

## Common Patterns

1. **Resource Verification Pattern**
```python
def has_resources(requirements: dict) -> bool:
    """Check if all required items are in inventory"""
    inventory = inspect_inventory()
    return all(inventory.get(item, 0) >= amount 
              for item, amount in requirements.items())

# Usage
if has_resources({
    Prototype.IronPlate: 5,
    Prototype.Coal: 10
}):
    # Proceed with operation
    pass
```

2. **Entity Monitoring Pattern**
```python
def check_furnace_status(furnace: Entity) -> bool:
    """Monitor furnace contents"""
    inventory = inspect_inventory(entity=furnace)
    has_fuel = inventory[Prototype.Coal] > 0
    has_ore = inventory[Prototype.IronOre] > 0
    has_output_space = inventory[Prototype.IronPlate] < 100
    return has_fuel and has_ore and has_output_space
```

3. **Resource Management Pattern**
```python
def ensure_minimum_resources(minimum_requirements: dict):
    """Ensure minimum resource levels are maintained"""
    inventory = inspect_inventory()
    for item, min_amount in minimum_requirements.items():
        current = inventory.get(item, 0)
        if current < min_amount:
            # Get more resources
            pass
```

## Integration with Other Tools

The inspect_inventory tool works well with:

1. `craft_item()` - Check resources before crafting
2. `insert_item()` - Verify space available
3. `place_entity()` - Ensure required items exist
4. `harvest_resource()` - Monitor gathered resources

Example workflow:
```python
# Complete resource management workflow
inventory = inspect_inventory()
if inventory[Prototype.Coal] < 10:
    # Get coal position
    coal_pos = nearest(Resource.Coal)
    move_to(coal_pos)
    harvest_resource(coal_pos, 20)

# Verify we got the coal
inventory = inspect_inventory()
assert inventory[Prototype.Coal] >= 10
```

## Performance Tips

1. **Cache Results**
- Store inventory results if checking multiple items
- Avoid repeated calls for same entity

2. **Batch Operations**
- Check all required resources at once
- Plan operations based on available resources

3. **Smart Checking**
- Check before expensive operations
- Verify critical resources first