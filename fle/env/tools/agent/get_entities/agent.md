# get_entities

The get_entities tool allows you to find and retrieve entities in the Factorio world based on different criteria. This tool is essential for locating specific entities, gathering information about your surroundings, and interacting with the game world.

## Basic Usage

```python
# Get entities by prototype within a radius
entities = get_entities(prototype=Prototype.IronChest, radius=10)

# Get entities by position
entities = get_entities(position=Position(x=10, y=15), radius=5)

# Get all entities of a certain type around the player
entities = get_entities(prototype=Prototype.AssemblingMachine1)
```

The function returns a list of Entity objects that match the specified criteria.

## Parameters

- `prototype`: The Prototype of entities to find (optional)
- `position`: Position to search around (default=player's current position)
- `radius`: Search radius in tiles (default=20)
- `name`: Exact entity name to search for (optional)
- `type`: Entity type category to search for (optional)

**Search Behavior**
   - If no prototype/name/type is specified, returns all entities within radius
   - Returns empty list if no matching entities are found
   - Maximum radius is limited to 50 tiles for performance reasons

## Examples

### Finding Specific Entities

```python
# Find all transport belts within 15 tiles of the player
belts = get_entities(prototype=Prototype.TransportBelt, radius=15)
print(f"Found {len(belts)} transport belts nearby")

# Find the closest furnace to a specific position
position = Position(x=5, y=10)
furnaces = get_entities(prototype=Prototype.StoneFurnace, position=position, radius=30)
if furnaces:
    closest_furnace = min(furnaces, key=lambda entity: entity.position.distance_to(position))
    print(f"Closest furnace is at {closest_furnace.position}")
```


## Common Pitfalls

1. **Performance Considerations**
   - Using too large of a radius can impact performance
   - Filter results as specifically as possible

2. **Entity Access**
   - Some actions may require the player to be near the entity

## Best Practices

1. **Efficient Searching**
```python
# Instead of searching the entire map:
def find_resource_patch(resource_type: Prototype):
    # Start with a reasonable radius
    for radius in [20, 40, 60, 80]:
        resources = get_entities(prototype=resource_type, radius=radius)
        if resources:
            return resources
    
    # If still not found, search in different directions
    for direction in [(50, 0), (0, 50), (-50, 0), (0, -50)]:
        pos = Position(x=player.position.x + direction[0], 
                       y=player.position.y + direction[1])
        resources = get_entities(prototype=resource_type, position=pos, radius=40)
        if resources:
            return resources
    
    return []
```

2. **Combining with Other Tools**
```python
# Find and interact with all chests containing iron plates
chests = get_entities(prototype=Prototype.IronChest)
iron_containing_chests = []

for chest in chests:
    inventory = inspect_inventory(chest)
    if Prototype.IronPlate in inventory and inventory[Prototype.IronPlate] > 0:
        iron_containing_chests.append(chest)
        print(f"Chest at {chest.position} contains {inventory[Prototype.IronPlate]} iron plates")

# Extract iron from the chest with the most plates
if iron_containing_chests:
    target_chest = max(iron_containing_chests, 
                       key=lambda c: inspect_inventory(c)[Prototype.IronPlate])
    extracted = extract_item(Prototype.IronPlate, target_chest, quantity=10)
    print(f"Extracted {extracted} iron plates from chest at {target_chest.position}")
```