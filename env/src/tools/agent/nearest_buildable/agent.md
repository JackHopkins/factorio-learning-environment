# nearest_buildable

The `nearest_buildable` tool helps find valid positions to place entities while respecting space requirements and resource coverage. This guide explains how to use it effectively.

## Basic Usage

### 1. Basic Entity Placement
```python
# Find place for chest near the origin
chest_box = BuildingBox(height=Prototype.WoodenChest.HEIGHT, width=Prototype.WoodenChest.WIDTH)
buildable_area = nearest_buildable(
    Prototype.WoodenChest,
    chest_box,
    Position(x=0, y=0)
)

# Place at center of buildable area
move_to(buildable_area.center)
chest = place_entity(Prototype.WoodenChest, position=buildable_area.center)
```

## Best practices
- Always use Prototype.X.WIDTH and .HEIGHT to plan the buildingboxes
- When doing power setups or setups with inserters, ensure the buildingbox is large enough to have room for connection types

## Troubleshooting

1. "No buildable position found"
   - Check building box size is appropriate
   - Verify resource coverage for miners