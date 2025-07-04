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