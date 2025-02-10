# extract_item

The extract tool allows you to remove items from entity inventories in the Factorio world. This tool is essential for moving items between entities and managing inventory contents.

## Basic Usage

```python
# Extract items using a position
extracted_count = extract_item(Prototype.IronPlate, position, quantity=5)

# Extract items using an entity directly
extracted_count = extract_item(Prototype.CopperCable, entity, quantity=3)
```

The function returns the number of items successfully extracted. The extracted items are automatically placed in the player's inventory.

## Parameters

- `entity`: The Prototype of the item to extract (required)
- `source`: Either a Position or Entity to extract from (required)
- `quantity`: Number of items to extract (default=5)

## Important Behaviors

1. **Position vs Entity Source**
   - You can provide either a Position or an Entity as the source
   - When using a Position, the tool will find the closest valid entity containing the item
   - When using an Entity, it will extract directly from that specific entity

2. **Multiple Inventory Types**
   - The tool can extract from various inventory types (chest, furnace, assembling machine, etc.)
   - It automatically handles different inventory slots (input, output, fuel, etc.)

3. **Quantity Handling**
   - If requested quantity exceeds available items, it extracts all available items
   - Returns actual number of items extracted

## Examples

### Extracting from a Chest
```python
# Place a chest and insert items
chest = place_entity(Prototype.IronChest, position=Position(x=0, y=0))
insert_item(Prototype.IronPlate, chest, quantity=10)

# Extract using position
count = extract_item(Prototype.IronPlate, chest.position, quantity=2)
# count will be 2, items move to player inventory

# Extract using entity
count = extract_item(Prototype.IronPlate, chest, quantity=5)
# count will be 5, items move to player inventory
```

### Extracting from an Assembling Machine
```python
# Set up assembling machine
assembler = place_entity(Prototype.AssemblingMachine1, position=Position(x=0, y=0))
set_entity_recipe(assembler, Prototype.ElectronicCircuit)
insert_item(Prototype.IronPlate, assembler, quantity=10)
insert_item(Prototype.CopperCable, assembler, quantity=3)

# Extract ingredients
count = extract_item(Prototype.IronPlate, assembler, quantity=2)
count = extract_item(Prototype.CopperCable, assembler, quantity=2)
```

## Common Pitfalls

1. **Invalid Positions**
   - Ensure the position has a valid entity containing the item
   - The tool searches within a 10-tile radius of the given position

2. **Empty Inventories**
   - Attempting to extract from empty inventories will raise an exception
   - Always verify item existence before extraction

3. **Distance Limitations**
   - Player must be within range of the target entity
   - Move closer if extraction fails due to distance

## Best Practices

1. **Inventory Verification**
   ```python
   # Check inventory before extraction
   inventory = inspect_inventory(entity)
   if inventory[Prototype.IronPlate] >= needed_amount:
       count = extract_item(Prototype.IronPlate, entity, quantity=needed_amount)
   ```

2. **Error Handling**
   ```python
   try:
       count = extract_item(Prototype.IronPlate, position, quantity=5)
   except Exception as e:
       print(f"Extraction failed: {e}")
       # Handle the error appropriately
   ```

3. **Quantity Management**
   - Request exact quantities needed
   - Check return value to confirm extracted amount
   - Handle cases where fewer items than requested were extracted
