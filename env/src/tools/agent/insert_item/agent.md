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

### 4. Chests
- Can accept any item
- Limited by inventory space
```python
chest = insert_item(Prototype.IronPlate, chest, 100)
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