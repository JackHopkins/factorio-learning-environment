# harvest_resource

The `harvest_resource` tool allows you to harvest resources like ores, trees, rocks and stumps from the Factorio world. This guide explains how to use it effectively.

## Basic Usage

```python
harvest_resource(position: Position, quantity: int = 1, radius: int = 10) -> int
```

The function returns the actual quantity harvested.

### Parameters

- `position`: Position object indicating where to harvest from
- `quantity`: How many resources to harvest (default: 1)
- `radius`: Search radius around the position (default: 10)

### Examples

```python
# Harvest 10 coal from nearest coal patch
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvested = harvest_resource(coal_pos, quantity=10)

# Harvest 5 iron ore
iron_pos = nearest(Resource.IronOre) 
move_to(iron_pos)
harvested = harvest_resource(iron_pos, quantity=5)
```

## Important Rules

1. You **must move to the resource** before harvesting:
```python
# Wrong - will fail
harvest_resource(nearest(Resource.Coal), 10)

# Correct
coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, 10)
```

2. Check inventory space before large harvests
```python
inventory = inspect_inventory()
if inventory[Prototype.Coal] < 4000:  # Check for space
    harvest_resource(coal_pos, quantity=100)
```

3. Handle potential failures gracefully:
```python
try:
    harvested = harvest_resource(pos, quantity=50)
except Exception as e:
    print(f"Failed to harvest: {e}")
```

## Harvestable Resources

The tool can harvest:

1. Basic Resources
- Coal (Resource.Coal)
- Iron Ore (Resource.IronOre)
- Copper Ore (Resource.CopperOre) 
- Stone (Resource.Stone)

2. Trees (Resource.Wood)
- Harvesting trees yields wood
- Creates stumps that can be harvested again

3. Rocks and Stumps
- Rock harvesting yields stone
- Stump harvesting yields additional wood

## Best Practices

1. **Efficient Resource Collection**
```python
# When you need multiple resources, plan the order:
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, 5)  # Get stone for furnace

coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, 10)  # Get coal for fuel
```

2. **Error Handling**
```python
def safe_harvest(resource_type, amount):
    try:
        pos = nearest(resource_type)
        move_to(pos)
        return harvest_resource(pos, amount)
    except Exception as e:
        print(f"Failed to harvest {resource_type}: {e}")
        return 0
```

3. **Inventory Management**
```python
# Check inventory before and after harvesting
initial_iron = inspect_inventory()[Prototype.IronOre]
harvest_resource(iron_pos, 50)
final_iron = inspect_inventory()[Prototype.IronOre]
iron_gained = final_iron - initial_iron
```

## Common Patterns

1. **Gathering Initial Resources**
```python
# Common startup pattern:
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, 5)  # For furnace

coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, 10)  # For fuel

iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, 10)  # For smelting
```

2. **Wood Collection**
```python
# Trees yield more wood than expected due to stumps
wood_pos = nearest(Resource.Wood)
move_to(wood_pos)
# Request less than needed as you'll get extra from stumps
harvest_resource(wood_pos, quantity=40, radius=50)
```

## Troubleshooting

Common issues and solutions:

1. "Nothing within reach to harvest"
   - Make sure you've moved to the resource first
   - Check if position is within reach distance
   - Verify resource exists at target position

2. "Inventory is full"
   - Check current inventory before harvesting
   - Remove or craft items to make space
   - Consider smaller harvest quantities

3. "Could not harvest {quantity} {resource}"
   - Resource patch may be depleted
   - Try finding another patch using nearest()
   - Consider reducing requested quantity

## Performance Tips

1. **Minimize Movement**
- Plan harvest order to minimize travel distance
- Harvest all needed resources from one patch before moving

2. **Batch Harvesting**
- Harvest larger quantities when possible to reduce trips
- Consider future needs when harvesting

3. **Radius Usage**
- Use larger radius for scattered resources like trees
- Use smaller radius for dense ore patches

## Integration with Other Tools

The harvest_resource tool works well with:

1. `nearest()` - Finding resource patches
2. `move_to()` - Reaching resources
3. `inspect_inventory()` - Managing harvested resources
4. `craft_item()` - Using harvested materials

Example workflow:
```python
# Complete workflow for making iron plates
stone_pos = nearest(Resource.Stone)
move_to(stone_pos)
harvest_resource(stone_pos, 5)
craft_item(Prototype.StoneFurnace)

coal_pos = nearest(Resource.Coal)
move_to(coal_pos)
harvest_resource(coal_pos, 10)

iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)
harvest_resource(iron_pos, 10)
```