# insert_item

The `insert_item` tool allows you to insert items from your inventory into entities like furnaces, chests, assembling machines, and transport belts. This guide explains how to use it effectively.

## Basic Usage

```python
insert_item(item: Prototype, target: Union[Entity, EntityGroup], quantity: int = 5) -> Entity
```

The function returns the updated target entity.

### Parameters

- `item`: Prototype of the item to insert
- `target`: Entity or EntityGroup to insert items into
- `quantity`: Number of items to insert (default: 5)

### Examples

```python
# Insert coal into a furnace
furnace = insert_item(Prototype.Coal, furnace, quantity=10)

# Insert iron ore into a furnace
furnace = insert_item(Prototype.IronOre, furnace, quantity=50)

# Insert items onto a belt
belt = insert_item(Prototype.IronOre, belt_group, quantity=5)
```

## Important Rules

1. **Always update the target variable with the return value:**
```python
# Wrong - state will be outdated
insert_item(Prototype.Coal, furnace, 10)

# Correct - updates furnace state
furnace = insert_item(Prototype.Coal, furnace, 10)
```

2. **Check inventory before inserting:**
```python
inventory = inspect_inventory()
if inventory[Prototype.Coal] >= 10:
    furnace = insert_item(Prototype.Coal, furnace, 10)
```

3. **Handle possible errors:**
```python
try:
    furnace = insert_item(Prototype.IronOre, furnace, 50)
except Exception as e:
    print(f"Failed to insert: {e}")
```

## Entity Type Rules

### 1. Furnaces
- Can accept fuels (coal, wood)
- Can accept smeltable items (ores)
- Cannot mix different ores in same furnace
```python
# Add fuel first
furnace = insert_item(Prototype.Coal, furnace, 10)
# Then add ore
furnace = insert_item(Prototype.IronOre, furnace, 50)
```

### 2. Burner Entities
- Can only accept fuel items
- Common with BurnerInserter, BurnerMiningDrill
```python
# Correct - inserting fuel
inserter = insert_item(Prototype.Coal, burner_inserter, 10)

# Wrong - will raise error
inserter = insert_item(Prototype.IronOre, burner_inserter, 10)
```

### 3. Assembling Machines
- Must have recipe set first
- Can only accept ingredients for current recipe
- Can insert products into output inventory
```python
# Set recipe first
assembler = set_entity_recipe(assembler, Prototype.IronGearWheel)
# Insert ingredients
assembler = insert_item(Prototype.IronPlate, assembler, 100)
```

### 4. Transport Belts
- Items are inserted one at a time
- Will stop when belt is full
- Use belt groups for efficient insertion
```python
# Insert items onto belt
belt_group = insert_item(Prototype.IronOre, belt_group, 5)
```

### 5. Chests
- Can accept any item
- Limited by inventory space
```python
chest = insert_item(Prototype.IronPlate, chest, 100)
```

## Best Practices

1. **Smelting Setup**
```python
# Ideal furnace setup pattern
furnace = place_entity(Prototype.StoneFurnace, position=pos)
# Add fuel first
furnace = insert_item(Prototype.Coal, furnace, 20)
# Then add ore
furnace = insert_item(Prototype.IronOre, furnace, 50)
```

2. **Assembling Machine Setup**
```python
# Proper assembling machine setup
assembler = place_entity(Prototype.AssemblingMachine1, position=pos)
assembler = set_entity_recipe(assembler, Prototype.IronGearWheel)
# Insert required ingredients
assembler = insert_item(Prototype.IronPlate, assembler, 100)
```

3. **Belt Loading**
```python
# Efficient belt loading
belt_group = connect_entities(start_pos, end_pos, Prototype.TransportBelt)
belt_group = insert_item(Prototype.IronPlate, belt_group, 10)
```

## Common Patterns

1. **Setting Up a Smelting Line**
```python
# Place and fuel multiple furnaces
for pos in furnace_positions:
    furnace = place_entity(Prototype.StoneFurnace, position=pos)
    # Add fuel
    furnace = insert_item(Prototype.Coal, furnace, 20)
    # Add ore
    furnace = insert_item(Prototype.IronOre, furnace, 50)
```

2. **Automating Assembly**
```python
# Set up assembling machine with ingredients
assembler = place_entity(Prototype.AssemblingMachine1, position=pos)
assembler = set_entity_recipe(assembler, Prototype.IronGearWheel)
# Insert materials
assembler = insert_item(Prototype.IronPlate, assembler, 100)
```

## Troubleshooting

Common issues and solutions:

1. "Entity is too far away"
   - Move closer to target entity
   - Check distance is within 10 tiles
   - Verify entity position

2. "Failed to insert items"
   - Check target entity accepts item type
   - Verify entity has space
   - Ensure correct recipe is set (for assemblers)

3. "Cannot insert X into Y"
   - Check item compatibility
   - Verify entity type accepts item
   - Check for conflicting items (furnaces)

## Performance Tips

1. **Minimize Movement**
- Insert items while placing entities
- Batch similar operations together
- Plan insertion order to reduce travel

2. **Efficient Belt Loading**
- Use belt groups instead of individual belts
- Load at belt input positions
- Consider using inserters for automation

3. **Resource Management**
- Pre-calculate required quantities
- Consider future needs when inserting
- Keep fuel levels adequate

## Integration with Other Tools

The insert_item tool works well with:

1. `place_entity()` - Setting up new machines
2. `set_entity_recipe()` - Configuring assemblers
3. `connect_entities()` - Creating belt systems
4. `inspect_inventory()` - Managing resources

Example workflow:
```python
# Complete smelting setup workflow
furnace = place_entity(Prototype.StoneFurnace, position=pos)
furnace = insert_item(Prototype.Coal, furnace, 20)  # Fuel
furnace = insert_item(Prototype.IronOre, furnace, 50)  # Ore

# Verify furnace is working
assert furnace.status == EntityStatus.WORKING
```

## Status Checking

Always verify entity status after insertion:

1. Check for NO_FUEL on burner entities
2. Verify WORKING status on furnaces
3. Monitor FULL_OUTPUT on belts
4. Check NO_POWER on electric entities

Example:
```python
furnace = insert_item(Prototype.Coal, furnace, 10)
if furnace.status == EntityStatus.NO_FUEL:
    furnace = insert_item(Prototype.Coal, furnace, 10)
```