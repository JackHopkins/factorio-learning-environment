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

**Quantity Handling**
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

## Common Pitfalls

1. **Empty Inventories**
   - Attempting to extract from empty inventories will raise an exception
   - Always verify item existence before extraction

2. **Distance Limitations**
   - Player must be within range of the target entity
   - Move closer if extraction fails due to distance