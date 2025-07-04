# render

## Description
The `render` tool creates a visual representation of entities in the game world. It's useful for understanding spatial relationships, checking factory layouts, and debugging entity configurations. The tool now enforces a maximum limit of 50 tiles on each side of the center position to improve performance. You can also select which specific layers to render using the new `layers` parameter.

## Usage
```python
# Render around a specific position with default radius (10 tiles)
image = render(position=Position(x=10, y=15))

# Render with a custom radius (capped at 50 tiles)
image = render(position=Position(x=10, y=15), radius=20)

# Render a specific bounding box area (will be clipped to max_tiles from center position)
box = BoundingBox(
    left_top=Position(x=5, y=5),
    right_bottom=Position(x=25, y=25),
    left_bottom=Position(x=5, y=25),
    right_top=Position(x=25, y=5)
)
image = render(position=Position(x=15, y=15), bounding_box=box)

# Render with custom style
custom_style = {
    "cell_size": 30,  # Larger tiles
    "grid_enabled": False,  # No grid lines
    "label_enabled": True   # Show labels
}
image = render(position=Position(x=10, y=15), style=custom_style)

# Specify only certain layers to render (e.g., only entities and grid)
image = render(position=Position(x=10, y=15), layers=Layer.ENTITIES | Layer.GRID)

# Render everything except water tiles and trees
image = render(position=Position(x=10, y=15), layers=Layer.ALL & ~(Layer.WATER | Layer.TREES))

# Display the image
image.show()
```

### Surveying Resource Patches
```python
# Find nearest iron ore
iron_pos = nearest(Prototype.IronOre)

# Visualize just the resource patches, without entities or other elements
image = render(position=iron_pos, radius=20, layers=Layer.RESOURCES | Layer.GRID)
image.show()

# Get details about the patch
patch = get_resource_patch(Prototype.IronOre)
print(f"Iron patch size: {patch.size} ore in an area of {patch.bounding_box.width()} x {patch.bounding_box.height()} tiles")
```

### Rendering Just the Factory Layout
```python
# When planning or documenting your factory, you might want to see just the factory layout
# without natural elements or resources cluttering the view
image = render(position=Position(10, 15), 
               layers=Layer.ENTITIES | Layer.CONNECTIONS | Layer.GRID | Layer.PLAYER)
image.show()
```

### Analyzing Resources
```python
# To focus on resource distribution in an area
image = render(position=Position(10, 15), radius=30,
               layers=Layer.RESOURCES | Layer.GRID | Layer.PLAYER)
image.show()

# Or to see how resources relate to water features
image = render(position=Position(10, 15), radius=30,
               layers=Layer.RESOURCES | Layer.WATER | Layer.GRID | Layer.PLAYER)
image.show()
```

## Common Issues and Solutions

### Issue: Image shows empty grid
**Solution**: Ensure there are entities in the area you're trying to render, or increase the radius (up to the max_tiles limit). If you're using layer filters, check that you haven't excluded the layers containing your entities.

### Issue: Render is slow for large factories
**Solution**: The tool now automatically clips the map to 50 tiles on each side of the position to improve performance. You can adjust this limit using the `max_tiles` parameter if needed. Additionally, consider using the `layers` parameter to only render the elements you need.

### Issue: Can't see entire factory layout
**Solution**: For very large factories, render specific sections by providing different center positions. You can create multiple renders and combine them using other image tools if needed.

### Issue: Too much visual clutter on the map
**Solution**: Use the `layers` parameter to selectively display only the elements you need. For example, to focus on your factory layout, you might disable natural elements with `layers=Layer.ALL & ~Layer.NATURAL`.

### Issue: Missing layer features after update
**Solution**: If you're using a custom layer combination and not seeing expected features, check that you've included all necessary layers. Some features might depend on multiple layers (e.g., underground belts need both ENTITIES and CONNECTIONS layers to show properly).

## Performance Tips

1. **Render only what you need**: Use the `layers` parameter to render only the elements you're interested in. This can significantly improve rendering speed for complex maps.

2. **Limit render area**: Specify a reasonable radius or bounding box to avoid rendering unnecessarily large areas.

3. **Use appropriate resolution**: Adjust the `cell_size` in the style dictionary if you need a higher or lower resolution image.

4. **Pipeline multiple renders**: For large factory analysis, consider creating a series of targeted renders (e.g., one for resources, one for production lines, etc.) rather than trying to show everything at once.

5. **Disable legend when not needed**: Set `"legend_enabled": False` in your style dictionary if you don't need the legend, especially for programmatic analysis.show()

## Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `position` | `Position` | Center position to render around | Player's current position |
| `radius` | `float` | Radius in tiles around position to render (capped at max_tiles) | 10 |
| `bounding_box` | `BoundingBox` | Specific area to render (will be clipped to max_tiles from center position) | None |
| `style` | `dict` | Custom style configuration | Default style |
| `max_tiles` | `int` | Maximum number of tiles to render on each side of the position | 50 |
| `layers` | `Layer` | Flags specifying which elements to render | Layer.ALL |

## Layer Options
You can use the following Layer enum values, either individually or combined with the bitwise OR operator (`|`):

| Layer | Description |
|-------|-------------|
| `Layer.NONE` | Render nothing (empty image) |
| `Layer.GRID` | Render grid lines |
| `Layer.WATER` | Render water tiles |
| `Layer.RESOURCES` | Render resource patches (iron, copper, etc.) |
| `Layer.TREES` | Render trees |
| `Layer.ROCKS` | Render rocks |
| `Layer.ENTITIES` | Render player-built entities |
| `Layer.CONNECTIONS` | Render underground belt/pipe connections |
| `Layer.ORIGIN` | Render origin marker (0,0) |
| `Layer.PLAYER` | Render player position marker |
| `Layer.LABELS` | Render entity labels |
| `Layer.NATURAL` | Render all natural elements (TREES | ROCKS) |
| `Layer.ALL` | Render all layers (default) |

## Return Value
Returns a `RenderedImage` object with methods:
- `show()`: Display the image (works in IDEs)
- `save(path)`: Save the image to a file
- `to_base64()`: Get base64 string representation for embedding

## Style Configuration
You can customize the rendering with a style dictionary:

```python
{
    "background_color": (40, 40, 40),      # RGB background color
    "grid_color": (60, 60, 60),            # RGB grid line color
    "text_color": (255, 255, 255),         # RGB text color
    "entity_colors": {                     # Colors for specific entities
        "iron-chest": (120, 160, 200),
        "assembling-machine-1": (120, 160, 200),
        # Add custom colors for other entities
    },
    "cell_size": 20,                       # Pixels per game tile
    "margin": 10,                          # Pixels around edge
    "grid_enabled": True,                  # Show grid lines
    "label_enabled": True,                 # Show entity labels
    "direction_indicator_enabled": True,   # Show direction arrows
    "status_indicator_enabled": True       # Show status indicators
}
```

## Example Patterns

### Visualizing a Production Line
```python
# Place some entities
assembler = place_entity(Prototype.AssemblingMachine1, Position(0, 0))
set_entity_recipe(assembler, "iron-gear-wheel")
chest_in = place_entity(Prototype.IronChest, Position(-2, 0))
chest_out = place_entity(Prototype.IronChest, Position(2, 0))
insert_item(chest_in, "iron-plate", 50)

# Place inserters
in_inserter = place_entity(Prototype.Inserter, Position(-1, 0), Direction.WEST)
out_inserter = place_entity(Prototype.Inserter, Position(1, 0), Direction.EAST)

# Visualize the setup (only showing entities and grid)
image = render(position=Position(0, 0), radius=5, layers=Layer.ENTITIES | Layer.GRID)
image.show()
```

### Visualizing Electricity Networks
```python
# View electricity network coverage in your factory
image = render(position=Position(10, 15), radius=30,
               layers=Layer.ELECTRICITY | Layer.GRID | Layer.ENTITIES)
image.show()

# Analyze electricity coverage in relation to your factory layout
image = render(position=Position(10, 15), radius=30,
               layers=Layer.ELECTRICITY | Layer.ENTITIES | Layer.GRID | Layer.PLAYER)
image.show()

# Check for disconnected electricity networks
image = render(position=Position(10, 15), radius=40,
               layers=Layer.ELECTRICITY | Layer.GRID)
image.show()
```