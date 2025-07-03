# nearest_buildable

The `nearest_buildable` tool helps find valid positions to place entities while respecting space requirements and resource coverage. This guide explains how to use it effectively.

## Basic Usage

```python
nearest_buildable(
    entity: Prototype,
    building_box: BuildingBox,
    center_position: Position
) -> BoundingBox
```

The function returns a BoundingBox object containing buildable area coordinates.

### Parameters
- `entity`: Prototype of entity to place
- `building_box`: BuildingBox defining required area dimensions
- `center_position`: Position to search around

### Return Value
Returns a BoundingBox with these attributes:
- `left_top`: Top-left corner Position
- `right_bottom`: Bottom-right corner Position
- `left_bottom`: Bottom-left corner Position
- `right_top`: Top-right corner Position
- `center`: Center position


## Common Use Cases

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

### 2. Mining Drill Placement
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
```
## Common Patterns

1. **Multiple Entity Placement**
Example: Create a copper plate mining line with 3 drills with inserters for future integration
```python
# log your general idea what you will do next
print(f"I will create a single line of 3 drills to mine copper ore")
# Find space for a line of 3 miners
move_to(source_position)
# define the BuildingBox for the drill. 
# We need 3 drills so width is 3*drill.WIDTH, height is drill.HEIGHT + furnace.HEIGHT, 3 for drill, one for furnace
building_box = BuildingBox(width = 3 * Prototype.ElectricMiningDrill.WIDTH, height = Prototype.ElectricMiningDrill.HEIGHT + Prototype.StoneFurnace.HEIGHT)
# get the nearest buildable area around the source_position
buildable_coordinates = nearest_buildable(Prototype.BurnerMiningDrill, building_box, source_position)

# Place miners in a line
# we first get the leftmost coordinate of the buildingbox to start building from
left_top = buildable_coordinates.left_top
# first lets move to the left_top to ensure building
move_to(left_top)
for i in range(3):
    # we now iterate from the leftmost point towards the right
    # take steps of drill.WIDTH
    drill_pos = Position(x=left_top.x + Prototype.ElectricMiningDrill.WIDTH*i, y=left_top.y)
    # Place the drill facing down as we start from top coordinate
    # The drop position will be below the drill as the direction is DOWN
    drill = place_entity(Prototype.ElectricMiningDrill, position=drill_pos, direction = Direction.DOWN)
    print(f"Placed ElectricMiningDrill {i} at {drill.position} to mine copper ore")
    # place a furnace to catch the ore
    # We use the Direction.DOWN as the direction, as the drill direction is DOWN which means the drop position is below the drill
    # NB: We also need to use drill.position, not drill.drop_position for placement. FUrnaces are multiple tiles wide and using drill.drop_pos will break the placement. VERY IMPORTANT CONSIDERATION
    furnace = place_entity_next_to(Prototype.StoneFurnace, reference_position=drill.position, direction = Direction.DOWN)
    print(f"Placed furnace at {furnace.position} to smelt the copper ore for drill {i} at {drill.position}")
    # add inserters for future potential integartion
    # put them below the furnace as the furnace is below the drill
    inserter = place_entity_next_to(Prototype.Inserter, reference_position=furnace.position, direction = Direction.DOWN)
    print(f"Placed inserter at {inserter.position} to get the plates from furnace {i} at {furnace.position}")

# sleep for 5 seconds and check a furnace has plates in it
sleep(5)
# update furnace entity
furnace = game.get_entity(Prototype.StoneFurnace, furnace.position)
assert inspect_inventory(entity=furnace).get(Prototype.CopperPlate, 0) > 0, f"No copper plates found in furnace at {furnace.position}"
```

## Best practices
- Always use Prototype.X.WIDTH and .HEIGHT to plan the buildingboxes
- When doing power setups or setups with inserters, ensure the buildingbox is large enough to have room for connection types

## Troubleshooting

1. "No buildable position found"
   - Check building box size is appropriate
   - Verify resource coverage for miners