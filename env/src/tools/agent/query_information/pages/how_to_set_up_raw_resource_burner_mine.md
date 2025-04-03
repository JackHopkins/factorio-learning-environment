1. **Mining Setup**
You can put chests directly at the drop positions of drills to catch ore, thus creating automatic drilling lines
```python
# Setup mining drill on ore patch
resource_pos = nearest(Resource.IronOre)
# Define area for drill
drill_box = BuildingBox(height=Prototype.ElectricMiningDrill.HEIGHT, width=Prototype.ElectricMiningDrill.WIDTH)

# Find buildable area
buildable_area = nearest_buildable(
    Prototype.ElectricMiningDrill,
    drill_box,
    resource_pos
)

# Place drill
move_to(buildable_area.center)
drill = place_entity(
    Prototype.ElectricMiningDrill,
    position=buildable_area.center
)
# log your actions
print(f"Placed drill to mine iron ore at {drill.position}")
# insert coal to drill
drill = insert_item(Prototype.Coal, drill, quantity = 10)
# Place output chest that catches ore
chest = place_entity(
    Prototype.WoodenChest,
    position=drill.drop_position,
    direction=Direction.DOWN,
)
# log your actions
print(f"Placed chest to catch iron ore at {chest.position}")
```