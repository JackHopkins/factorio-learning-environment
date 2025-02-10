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

### 3. Wood (Trees)
```python
# Check wood resources
wood_patch = get_resource_patch(
    Resource.Wood,
    position=Position(x=0, y=0)
)
print(f"Estimated {wood_patch.size} wood available")
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
    miner_width = 3  # Electric mining drill width
    miners_needed = math.ceil(width / miner_width) * math.ceil(height / miner_width)
    
    return {
        'total_resource': patch.size,
        'miners_needed': miners_needed,
        'dimensions': (width, height)
    }
```

### 2. Resource Patch Analysis
```python
def analyze_patch_feasibility(patch):
    # Calculate minimum required miners
    min_miners = math.ceil(patch.size / 1000)  # Assume 1000 ore per miner is minimum
    
    # Calculate power requirements
    power_per_miner = 90  # kW
    total_power = min_miners * power_per_miner
    
    return {
        'minimum_miners': min_miners,
        'power_required': total_power,
        'patch_area': patch.bounding_box.width() * patch.bounding_box.height()
    }
```

### 3. Factory Layout Planning
```python
def plan_factory_layout(resource_patch):
    # Get patch boundaries
    bbox = resource_patch.bounding_box
    
    # Plan smelter placement (10 tiles from patch)
    smelter_position = Position(
        x=bbox.right_bottom.x + 10,
        y=bbox.center().y
    )
    
    # Plan belt system
    belt_start = bbox.right_bottom
    belt_end = smelter_position
    
    return {
        'mining_area': bbox,
        'smelter_position': smelter_position,
        'belt_path': (belt_start, belt_end)
    }
```

## Best Practices

1. **Validate Resource Existence**
```python
try:
    patch = get_resource_patch(resource, position)
except Exception as e:
    print(f"No resource found: {e}")
    # Handle missing resource case
```

2. **Efficient Search**
```python
def find_optimal_patch(resource_type, min_size):
    # Start with small radius
    radius = 10
    while radius <= 50:  # Maximum search radius
        try:
            patch = get_resource_patch(resource_type, position, radius)
            if patch.size >= min_size:
                return patch
        except Exception:
            pass
        radius += 10
    return None
```

3. **Resource Estimation**
```python
def estimate_mining_duration(patch, num_miners):
    # Mining speed calculations
    miner_speed = 0.5  # Base mining speed
    resource_per_second = miner_speed * num_miners
    
    duration = patch.size / resource_per_second
    return duration  # Returns seconds
```

## Common Patterns

### Mining Outpost Planning
```python
def plan_mining_outpost(resource_type, position):
    # Get resource patch information
    patch = get_resource_patch(resource_type, position)
    
    # Calculate dimensions
    width = patch.bounding_box.width()
    height = patch.bounding_box.height()
    
    # Plan components
    components = {
        'miners': [],
        'power_poles': [],
        'belts': [],
        'chests': []
    }
    
    # Calculate miner positions
    miner_spacing = 3
    for x in range(0, width, miner_spacing):
        for y in range(0, height, miner_spacing):
            components['miners'].append(
                Position(
                    x=patch.bounding_box.left_top.x + x,
                    y=patch.bounding_box.left_top.y + y
                )
            )
    
    return components
```

### Power Planning
```python
def plan_power_infrastructure(patch):
    # Calculate power requirements
    bbox = patch.bounding_box
    area = bbox.width() * bbox.height()
    miners_needed = math.ceil(area / 9)  # 3x3 miner size
    
    power_requirements = {
        'miners': miners_needed * 90,  # 90kW per miner
        'inserters': miners_needed * 13,  # 13kW per inserter
        'total': 0
    }
    power_requirements['total'] = sum(power_requirements.values())
    
    return power_requirements
```

## Error Handling

### Common Errors

1. **No Resource Found**
```python
try:
    patch = get_resource_patch(Resource.Coal, position)
except Exception as e:
    if "No resource of type" in str(e):
        # Handle missing resource
        pass
```

2. **Invalid Position**
```python
def safe_get_patch(resource, position):
    try:
        return get_resource_patch(resource, position)
    except Exception as e:
        print(f"Error finding resource patch: {e}")
        return None
```

## Tips for Effective Usage

1. **Resource Search Strategy**
   - Start with small search radius
   - Increase radius if needed
   - Consider patch size requirements

2. **Layout Planning**
   - Use bounding box for layout calculations
   - Leave space for infrastructure
   - Consider future expansion

3. **Performance Optimization**
   - Cache patch information when needed
   - Minimize repeated searches
   - Use appropriate search radius

## Debugging Tips

If resource patch detection fails:

1. **Check Position**
   - Verify coordinates
   - Ensure within map bounds
   - Check for obstacles

2. **Verify Resource Type**
   - Confirm resource exists
   - Check spelling/enumeration
   - Verify game stage (some resources appear later)

3. **Search Radius**
   - Try different radius values
   - Check for nearby obstacles
   - Consider map generation settings