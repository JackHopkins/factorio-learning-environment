# get_resource_patch

The `get_resource_patch` tool analyzes and returns information about resource patches in Factorio, including their size, boundaries, and total available resources. This tool is essential for planning mining operations and factory layouts.

## Core Functionality

The tool provides:
- Total resource amount in a patch
- Bounding box coordinates of the patch
- Support for all resource types (ores, water, trees)

## Basic Usage

```python
# Get information about a resource patch
patch = get_resource_patch(
    resource=Resource.X,     # Resource type to find
    position=Position(x,y),  # Center position to search
    radius=10               # Search radius (default: 10)
)
```

### Parameters

1. `resource`: Resource - Type of resource to analyze (e.g., Resource.Coal, Resource.Water)
2. `position`: Position - Center point to search around
3. `radius`: int - Search radius in tiles (default: 10)

### Return Value

Returns a ResourcePatch object containing:
```python
ResourcePatch(
    name=str,              # Resource name
    size=int,              # Total resource amount
    bounding_box=BoundingBox(
        left_top=Position(x,y),
        right_bottom=Position(x,y),
        left_bottom=Position(x,y),
        right_top=Position(x,y)
    )
)
```

## Resource Types

### 1. Ore Resources
```python
# Check iron ore patch
iron_patch = get_resource_patch(
    Resource.IronOre,
    position=Position(x=0, y=0)
)
print(f"Found {iron_patch.size} iron ore")
```

### 2. Water Resources
```python
# Check water area
water_patch = get_resource_patch(
    Resource.Water,
    position=Position(x=0, y=0)
)
print(f"Water area contains {water_patch.size} tiles")
```

## Common Use Cases

### 1. Mining Site Planning
```python
def plan_mining_site(resource_type, position):
    patch = get_resource_patch(resource_type, position)
    
    # Calculate mining coverage
    width = patch.bounding_box.width()
    height = patch.bounding_box.height()
    
    # Estimate number of miners needed
    miner_width = Prototype.ElectricMiningDrill.WIDTH  # Electric mining drill width
    miners_needed = math.ceil(width / miner_width) * math.ceil(height / miner_width)
    
    return {
        'total_resource': patch.size,
        'miners_needed': miners_needed,
        'dimensions': (width, height)
    }
```