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

## Entity Type Rules

### 1. Furnaces
- Can accept fuels (coal, wood)
- Can accept smeltable items (ores)
- Cannot mix different ores in same furnace (extract ores and plates of different types before inputting new ones)

### 2. Burner Entities
- Can only accept fuel items
- Common with BurnerInserter, BurnerMiningDrill

### 3. Assembling Machines
- Must have recipe set first
- Can only accept ingredients for current recipe
