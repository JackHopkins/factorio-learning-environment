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