# Manual

## Core Interaction Patterns

### 0. Material Processing Requirements
Before crafting any items requiring metal plates, ores MUST be smelted first:
```python
# Wrong:
# Can't craft directly from ore!
craft_item(Prototype.IronGearWheel)  # Will fail - needs iron plates, not ore

# Correct:
# 1. Get ore
move_to(nearest(Resource.IronOre))
harvest_resource(nearest(Resource.IronOre), quantity=10)

# 2. Smelt ore into plates
furnace = place_entity(Prototype.StoneFurnace, position=position)
insert_item(Prototype.Coal, furnace, quantity=5)  # Don't forget fuel
insert_item(Prototype.IronOre, furnace, quantity=10)

# 3. Wait for smelting (with safety timeout)
for _ in range(30):  # Maximum 30 seconds wait
    if inspect_inventory(furnace)[Prototype.IronPlate] >= 10:
        break
    sleep(1)
else:
    raise Exception("Smelting timeout - check fuel and inputs")
    
# 4. Now you can craft
craft_item(Prototype.IronGearWheel)
```

### 1. Inventory Requirements
Before placing any entity, ensure it exists in the inventory. Many beginners miss this crucial step:
```python
# Wrong:
drill = place_entity(Prototype.BurnerMiningDrill, position=position)  # Will fail if not in inventory!

# Correct:
# First check recipe and craft if needed
recipe = get_prototype_recipe(Prototype.BurnerMiningDrill)
craft_item(Prototype.BurnerMiningDrill)  # Only after ensuring materials available
drill = place_entity(Prototype.BurnerMiningDrill, position=position)

# Even better - use a helper function:
def ensure_craftable(prototype, quantity=1):
    recipe = get_prototype_recipe(prototype)
    inventory = inspect_inventory()
    if inventory.get(prototype, 0) < quantity:
        craft_item(prototype, quantity)
        
ensure_craftable(Prototype.BurnerMiningDrill)
drill = place_entity(Prototype.BurnerMiningDrill, position=position)
```

You can inspect your own inventory, or the inventory of an entity:
```python
# Check player inventory
player_inv = inspect_inventory()
iron_plates = player_inv[Prototype.IronPlate]

# Check entity inventory
furnace = place_entity(Prototype.StoneFurnace, position=pos)
furnace_inv = inspect_inventory(furnace)
coal_in_furnace = furnace_inv[Prototype.Coal]
```

### 2. Resource Location & Movement
Before any entity placement or interaction, you must first move to the target location:
```python
# Always locate resources first
resource_position = nearest(Resource.Coal)
move_to(resource_position)  # Must move before placing/interacting
```

### 3. Entity Placement Prerequisites

#### Basic Entity Placement
Entities must be placed in a valid location after moving there:
```python
# Basic placement pattern
move_to(target_position) 
entity = place_entity(Prototype.Entity, position=target_position)
```

#### Using place_entity_next_to
The `place_entity_next_to` method is crucial for building organized factory layouts. It handles:
- Automatic position calculation based on entity dimensions
- Proper spacing between entities
- Direction-aware placement

Key parameters:
- `entity_prototype`: The type of entity to place
- `reference_position`: Position of the entity to place next to
- `direction`: Which direction to place relative to reference (UP, DOWN, LEFT, RIGHT)
- `spacing`: Additional tiles of space between entities (0 or more)

```python
# Basic usage
ref_entity = place_entity(Prototype.BurnerMiningDrill, position=drill_position)
connected_entity = place_entity_next_to(
    Prototype.Inserter,
    reference_position=ref_entity.position,
    direction=Direction.UP,
    spacing=0
)
```

#### Common Patterns and Use Cases

1. **Mining to Furnace Setup**
```python
# Place drill on ore patch
drill = place_entity(Prototype.BurnerMiningDrill, position=ore_position)
# Place furnace next to drill's output
furnace = place_entity_next_to(
    Prototype.StoneFurnace,
    reference_position=drill.drop_position,  # Use drop_position for output-connected entities
    direction=Direction.DOWN,
    spacing=0
)
```

2. **Power Infrastructure**

Power typically involves:
-> Water Source + OffshorePump
-> Boiler (burning coal)
-> SteamEngine
-> Electrical Poles connecting to consumers

```python
# Connect water pump to boiler to steam engine
offshore_pump = place_entity(Prototype.OffshorePump, position=water_position)
boiler = place_entity_next_to(
    Prototype.Boiler,
    reference_position=offshore_pump.position,
    direction=Direction.UP,
    spacing=2  # Extra space for pipes
)
steam_engine = place_entity_next_to(
    Prototype.SteamEngine,
    reference_position=boiler.position,
    direction=Direction.RIGHT,
    spacing=2
)
```

#### Special Considerations

1. **Entity Rotation**
- Some entities (like steam engines) auto-rotate based on connection points
- Others need manual rotation after placement:
```python
drill = place_entity_next_to(Prototype.ElectricMiningDrill, 
    reference_position=position,
    direction=Direction.RIGHT) # This places the drill to the RIGHT the position
drill = rotate_entity(drill, Direction.DOWN) # This orients the drill downwards
```

2. **Entity Dimensions**
- Account for different entity sizes when planning layouts
- Use `tile_dimensions` for reference:
```python
print(f"Entity dimensions: {entity.tile_dimensions}")
assert entity.position.is_close(expected_position, tolerance=1)
```

3. **Drop Positions**
- Use `drop_position` when connecting output of one entity to another:
```python
miner = place_entity(Prototype.BurnerMiningDrill, position=ore_position)
belt = place_entity_next_to(
    Prototype.TransportBelt,
    reference_position=miner.drop_position,  # Connect to output
    direction=Direction.DOWN
)
```

4. **Spacing Guidelines**
- Use 0 spacing for flush connections
- Use 1 spacing for entities that need space for inserters between them
- Use 2+ spacing for power setups (boiler to steam engine) or where you need extra space for pipes or belts.

5. **Position Validation**
- Always verify placement with assertions in critical setups:
```python
furnace = place_entity_next_to(Prototype.StoneFurnace, reference_position)
assert furnace, "Failed to place furnace"
assert furnace.position.is_close(expected_position, tolerance=1), \
    f"Furnace misplaced. Expected {expected_position}, got {furnace.position}"
```

6. **Position Handling**
The Position class provides helpful methods for working with coordinates:
```python
# Check if positions are approximately equal
pos1 = Position(x=1.0, y=1.0)
pos2 = Position(x=1.1, y=0.9)
assert pos1.is_close(pos2, tolerance=0.2)

# Position arithmetic
new_pos = pos1 + Position(x=2, y=0)  # Move right 2 units
```

### 4. Entity Chain Construction
When building chains of entities, follow this pattern:
1. Place primary producer (e.g., mining drill)
2. Place destination entity (e.g., furnace)
3. Place connectors (e.g., inserters, belts, pipes)
4. Add fuel/resources

```python
# Example mining-to-furnace chain
move_to(ore_position)
drill = place_entity(Prototype.BurnerMiningDrill, position=ore_position)
furnace = place_entity_next_to(Prototype.StoneFurnace, 
    reference_position=drill.drop_position,
    direction=Direction.RIGHT)
inserter = place_entity_next_to(Prototype.BurnerInserter,
    reference_position=drill.position,
    direction=Direction.RIGHT)

# Always fuel burner entities after placement
insert_item(Prototype.Coal, drill, quantity=5)
```

### 5. Power Systems
Power systems follow a specific order:
1. Water source connection
2. Power generation
3. Power distribution
4. Consumer connection

```python
# Power system pattern
move_to(water_position)
offshore_pump = place_entity(Prototype.OffshorePump, position=water_position)
boiler = place_entity_next_to(Prototype.Boiler, 
    reference_position=offshore_pump.position,
    spacing=2)
steam_engine = place_entity_next_to(Prototype.SteamEngine,
    reference_position=boiler.position,
    spacing=2)

# Connect entities in order
water_pipes = connect_entities(offshore_pump, boiler, Prototype.Pipe)
steam_pipes = connect_entities(boiler, steam_engine, Prototype.Pipe)
```

### 6. Belt Systems
When creating belt systems:
1. Establish source
2. Place destination
3. Connect with belts
4. Add inserters at transfer points

```python
# Belt system pattern
move_to(source_position)
source = place_entity(Prototype.BurnerMiningDrill, position=source_position)
destination = place_entity_next_to(Prototype.Chest, 
    reference_position=source.position,
    direction=Direction.RIGHT)
belt = connect_entities(source.drop_position, destination.position, 
    Prototype.TransportBelt)
```

### 7. Finding Valid Build Locations with nearest_buildable

The nearest_buildable function helps find valid positions to place entities, especially when dealing with resource patches or complex multi-entity layouts:

```python
# Basic usage - find nearest position to place a single entity
position = nearest_buildable(Prototype.BurnerMiningDrill)
drill = place_entity(Prototype.BurnerMiningDrill, position=position)

# Find position for a group of entities using bounding box
drill_layout = BoundingBox(
    left_top=Position(x=0, y=0),
    right_bottom=Position(x=10, y=5),  # Space for multiple drills
    center=Position(x=5, y=2.5)
)
valid_position = nearest_buildable(
    Prototype.ElectricMiningDrill,
    bounding_box=drill_layout
)
```

#### Key Features
1. **Resource Requirements**: Automatically considers entity placement requirements (e.g., miners must be on ore patches)
2. **Space Validation**: Ensures enough clear space for the entire bounding box
3. **Relative Positioning**: Returns coordinates relative to the bounding box's left_top when a box is provided

#### Common Patterns

1. **Mining Setup**:
```python
# Find space for a line of 3 miners
mining_area = BoundingBox(
    left_top=Position(x=0, y=0),
    right_bottom=Position(x=9, y=3),  # 3x3 space for each miner
    center=Position(x=4.5, y=1.5)
)
start_pos = nearest_buildable(
    Prototype.ElectricMiningDrill,
    bounding_box=mining_area
)

# Place miners in a line
for i in range(3):
    drill_pos = Position(x=start_pos.x + i*3, y=start_pos.y)
    place_entity(Prototype.ElectricMiningDrill, position=drill_pos)
```

2. **Factory Layout**:
```python
# Find space for a furnace array with belts
layout_box = BoundingBox(
    left_top=Position(x=0, y=0),
    right_bottom=Position(x=15, y=5),  # Space for furnaces and belts
    center=Position(x=7.5, y=2.5)
)
origin = nearest_buildable(
    Prototype.StoneFurnace, 
    bounding_box=layout_box
)

# Use returned position as reference for layout
furnace = place_entity(Prototype.StoneFurnace, position=origin)
input_belt = place_entity_next_to(
    Prototype.TransportBelt,
    reference_position=furnace.position,
    direction=Direction.LEFT
)
```

#### Error Handling
The function raises an exception if no valid position is found. Always wrap usage in try/except when placement requirements are uncertain:

```python
try:
    position = nearest_buildable(
        Prototype.ElectricMiningDrill,
        bounding_box=large_area
    )
except Exception as e:
    print(f"Could not find valid placement: {e}")
    # Handle alternative placement strategy
```

#### Best Practices

1. **Size Calculation**:
- Include margins in bounding box calculations
- Account for entity dimensions and spacing
- Consider connection points for belts/inserters

2. **Resource Patches**:
- Use with get_resource_patch to validate ore coverage
- Check patch size against bounding box
```python
patch = get_resource_patch(Resource.IronOre, nearest(Resource.IronOre))
if patch.size > mining_area.area:  # Check if patch can support layout
    position = nearest_buildable(
        Prototype.ElectricMiningDrill, 
        bounding_box=mining_area
    )
```

3. **Placement Verification**:
- Always verify placement after finding position
- Use can_place_entity for additional validation
```python
position = nearest_buildable(Prototype.StoneFurnace)
if can_place_entity(Prototype.StoneFurnace, position=position):
    furnace = place_entity(Prototype.StoneFurnace, position=position)
```

### 8. Self-Fueling Mining Systems

Self-fueling mining systems are essential for automating resource collection, particularly for coal mining. These systems use the mined coal to power themselves, creating a sustainable loop.

#### Basic Self-Fueling Mine Pattern
```python
# 1. Find suitable coal patch
coal_patch = get_resource_patch(Resource.Coal, nearest(Resource.Coal))
move_to(coal_patch.bounding_box.center)

# 2. Place mining drill
drill = place_entity(Prototype.BurnerMiningDrill, Direction.DOWN, coal_patch.bounding_box.center)

# 3. Place inserter to feed coal back into drill
inserter = place_entity_next_to(
    Prototype.BurnerInserter, 
    drill.position,
    direction=Direction.UP,
    spacing=0
)
rotate_entity(inserter, Direction.DOWN)  # Face inserter toward drill

# 4. Connect with transport belt
belts = connect_entities(
    drill.drop_position,
    inserter.pickup_position,
    Prototype.TransportBelt
)

# 5. Bootstrap system with initial fuel
insert_item(Prototype.Coal, drill, quantity=5)
```

#### Multi-Drill Self-Fueling Systems

For larger operations, you can create systems with multiple drills sharing a common fuel belt:

```python
    """
    Build a self-fueling coal mining system with multiple drills.
    """
    num_drills = 5
    drills = []
    inserters = []
    
    # 1. Place drills and their inserters
    for i in range(num_drills):
        # Calculate positions with proper spacing
        drill_position = Position(
            x=coal_patch.bounding_box.left_top.x + i * 2,
            y=coal_patch.bounding_box.center.y
        )
        
        # Place and configure each drill
        drill = place_entity(
            Prototype.BurnerMiningDrill,
            Direction.DOWN,
            drill_position
        )
        
        # Place and configure inserter for fuel
        inserter = place_entity_next_to(
            Prototype.BurnerInserter,
            drill_position,
            direction=Direction.UP,
            spacing=0
        )
        inserter = rotate_entity(inserter, Direction.DOWN)
        
        drills.append(drill)
        inserters.append(inserter)
    
    # 2. Create main transport belt
    belt_start = Position(
        x=drills[0].drop_position.x,
        y=drills[0].drop_position.y
    )
    belt_end = Position(
        x=drills[-1].drop_position.x,
        y=drills[0].drop_position.y
    )
    
    # 3. Connect belt in a loop
    main_belt = connect_entities(
        belt_start,
        belt_end,
        Prototype.TransportBelt
    )
    
    # Connect to last inserter
    connect_entities(
        belt_end,
        inserters[-1].pickup_position,
        Prototype.TransportBelt
    )
    
    # Connect between inserters
    connect_entities(
        inserters[-1].pickup_position,
        inserters[0].pickup_position,
        Prototype.TransportBelt
    )
    
    # Close the loop
    connect_entities(
        inserters[0].pickup_position,
        belt_start,
        Prototype.TransportBelt
    )
    
    # 4. Bootstrap the system
    insert_item(Prototype.Coal, drills[0], quantity=10)
```

#### Best Practices for Self-Fueling Systems

1. **Resource Verification**
   - Always verify coal patch size before building
   - Ensure patch is large enough for planned number of drills
   ```python
   assert coal_patch.size >= num_drills * 5, "Coal patch too small"
   ```

2. **Proper Belt Loops**
   - Create complete loops without gaps
   - Verify belt connections after placement
   - Use proper belt directions at corners

3. **System Bootstrap**
   - Add initial fuel to at least one drill
   - Verify fuel reaches all drills
   - Monitor system startup to ensure proper operation

4. **Error Handling**
   ```python
   try:
       drill = place_entity(Prototype.BurnerMiningDrill, position)
       inserter = place_entity_next_to(
           Prototype.BurnerInserter,
           drill.position,
           direction=Direction.UP
       )
   except Exception as e:
       print(f"Failed to build mining system: {e}")
       # Clean up partial construction
   ```

5. **Alternative Designs**
   ```python
   # Using chest as buffer
   chest = place_entity(
       Prototype.IronChest,
       Direction.RIGHT,
       drill.drop_position
   )
   inserter = place_entity_next_to(
       Prototype.BurnerInserter,
       chest.position,
       direction=Direction.UP
   )
   ```

#### Common Patterns

1. **Linear Mining Array**
   - Place drills in a straight line
   - Use shared belt system
   - Single fuel distribution loop

2. **Compact Design**
   - Minimal spacing between components
   - Direct inserter connections
   - Efficient belt routing

3. **Redundant Systems**
   - Multiple fuel paths
   - Backup inserters
   - Buffer chests for stability

#### Troubleshooting

1. **System Stalls**
   - Check belt continuity
   - Verify inserter directions
   - Ensure adequate initial fuel

2. **Inefficient Operation**
   - Optimize belt paths
   - Balance drill placement
   - Adjust inserter positions

3. **Startup Issues**
   - Add more initial fuel
   - Verify all connections
   - Check entity rotation

### 9. Research and Technology

Technology research is crucial for unlocking new capabilities. Research requires:
1. A powered lab
2. Required science packs
3. Power infrastructure

#### Basic Research Setup Pattern
```python
# 1. Set up power infrastructure first (see Power Systems section)
# Assuming we have a working steam engine at Position(x=-10, y=0)
steam_engine = get_entity(Prototype.SteamEngine, position=Position(x=-10, y=0))

# 2. Place and power the lab
# Lab needs significant space as it has large dimensions
# Define building box with extra space for power connections
building_box = BuildingBox(width=5, height=5)
target_position = Position(x=steam_engine.position.x + 10, y=steam_engine.position.y)
buildable_coordinates = nearest_buildable(Prototype.Lab, building_box, target_position)

# Place lab
lab_position = buildable_coordinates["left_top"]
move_to(lab_position)
lab = place_entity(Prototype.Lab, position=lab_position)
print(f"Placed lab at {lab.position}")

# Connect lab to power
power_connection = connect_entities(steam_engine, lab, Prototype.SmallElectricPole)
print(f"Connected lab to power: {power_connection}")

# Wait for power connection
sleep(10)
# Update lab entity to get current state
lab = get_entity(Prototype.Lab, position=lab.position)
assert lab.energy > 0, "Lab is not receiving power"

# 3. Insert required science packs
lab = insert_item(Prototype.AutomationSciencePack, lab, quantity=10)
print(f"Inserted 10 automation science packs into lab")

# 4. Start research
# First check what ingredients are needed
ingredients = set_research(Technology.Automation)
print(f"Research requires: {ingredients}")

# 5. Monitor research progress
initial_progress = get_research_progress(Technology.Automation)
print(f"Initial research state: {initial_progress}")

# Wait for research to progress
sleep(30)

# Check progress
current_progress = get_research_progress(Technology.Automation)
# Progress is measured by remaining ingredients needed
assert current_progress[0].count < initial_progress[0].count, "Research is not progressing"
print(f"Research is progressing! Started with {initial_progress[0].count} packs needed, now need {current_progress[0].count}")
```

#### Research Requirements

1. **Power Requirements**
- Labs must have constant power supply
- Use power poles to connect to steam engines
- Monitor lab.energy to verify power connection

2. **Science Pack Management** 
- Always check required ingredients with `set_research()`
- Insert correct type and quantity of science packs
- Monitor pack consumption with `get_research_progress()`

3. **Research Monitoring**
- Research progress is measured by remaining ingredients needed
- Lower ingredient count indicates progress
- Use `get_research_progress()` to track status

#### Best Practices

1. **Lab Placement**
- Place labs with adequate spacing for power connections
- Group multiple labs together for efficiency
- Keep labs close to power infrastructure

2. **Science Pack Supply**
- Calculate total science packs needed before starting
- Ensure continuous supply for longer research
- Monitor pack consumption rate

3. **Progress Verification**
```python
# Verify research is actually progressing
initial_count = initial_progress[0].count
current_count = get_research_progress(Technology.Automation)[0].count
assert current_count < initial_count, "Research not progressing - check power and science packs"
```

#### Common Errors

1. **Power Issues**
```python
# Always verify power connection
lab = get_entity(Prototype.Lab, position=lab.position)
if lab.energy <= 0:
    print("Lab not receiving power - check connections")
```

2. **Missing Science Packs**
```python
# Check lab inventory before starting
lab_inventory = inspect_inventory(lab)
required_packs = lab_inventory.get(Prototype.AutomationSciencePack, 0)
assert required_packs > 0, "No science packs in lab"
```

## Common Antipatterns to Avoid

1. **Missing Movement**
```python
# Wrong:
entity = place_entity(Prototype.Entity, position=position)

# Correct:
move_to(position)
entity = place_entity(Prototype.Entity, position=position)
```

2. **Incorrect Order Dependencies**
```python
# Wrong:
inserter = place_entity(Prototype.Inserter, position=position)
drill = place_entity(Prototype.BurnerMiningDrill, position=drill_position)

# Correct:
drill = place_entity(Prototype.BurnerMiningDrill, position=drill_position)
inserter = place_entity_next_to(Prototype.Inserter, 
    reference_position=drill.position)
```

3. **Unfueled Burner Entities**
```python
# Wrong:
drill = place_entity(Prototype.BurnerMiningDrill, position=position)
# Missing fuel!

# Correct:
drill = place_entity(Prototype.BurnerMiningDrill, position=position)
insert_item(Prototype.Coal, drill, quantity=5)
```

## Best Practices

1. **Resource Discovery**
- Always use `nearest()` to find resources
- Cache resource patch information when multiple entities will use it
```python
coal_patch = get_resource_patch(Resource.Coal, nearest(Resource.Coal))
```

2. **Entity Positioning and Crafting**
- Verify inventory contains entity before attempting placement
- Craft required entities and materials before starting construction
- Check recipe requirements recursively for complex entities
- Use `place_entity_next_to()` instead of manual position calculations
- Maintain consistent spacing patterns for similar entity types

3. **Connection Validation**
- Verify connections after placing them
- Check entity status for expected states
```python
entities = get_entities({Prototype.TransportBelt}, position)
assert len(entities) > 0, "Belt connection failed"
```

4. **Resource Management**
- Pre-calculate resource requirements
- Verify inventory contents before placement
- Use consistent fuel quantities for similar entity types

5. **Error Handling**
- Always check return values from placement functions
- Verify entity states after important operations
- Clean up partially constructed systems on failure

## Utility Functions

Creating reusable utility functions is essential for maintaining clean and reliable factory code. Here are some key patterns:

**Note** These are for illustration purposes only, and will not be accessible when you play. You must define your own functions as you go.
### 1. Resource Processing Functions
```python
def smelt_ore(ore_type: Prototype, position: Position, quantity: int, timeout: int = 30) -> int:
    """
    Smelt ore into plates with timeout protection.
    Returns number of plates produced.
    """
    # Determine plate type based on ore
    plate_type = {
        Prototype.IronOre: Prototype.IronPlate,
        Prototype.CopperOre: Prototype.CopperPlate,
    }[ore_type]
    
    # Place and fuel furnace
    furnace = place_entity(Prototype.StoneFurnace, position=position)
    insert_item(Prototype.Coal, furnace, quantity=max(5, quantity // 2))
    insert_item(ore_type, furnace, quantity=quantity)
    
    # Wait for smelting with timeout
    for _ in range(timeout):
        plates = inspect_inventory(furnace)[plate_type]
        if plates >= quantity:
            return extract_item(plate_type, furnace.position, quantity)
        sleep(1)
    raise Exception(f"Smelting timeout after {timeout}s")

def ensure_crafting_materials(recipe: Recipe, quantity: int = 1) -> bool:
    """
    Recursively ensure all materials for a recipe are available.
    Includes smelting ores if needed.
    """
    for ingredient in recipe.ingredients:
        required = ingredient.count * quantity
        if inspect_inventory()[ingredient.name] < required:
            if ingredient.name in [Prototype.IronPlate, Prototype.CopperPlate]:
                ore_type = {
                    Prototype.IronPlate: Prototype.IronOre,
                    Prototype.CopperPlate: Prototype.CopperOre
                }[ingredient.name]
                smelt_ore(ore_type, required)
            else:
                craft_recursive(ingredient.name, required)
    return True

def build_power_connection(source: Entity, target: Entity, max_distance: int = 20) -> List[Entity]:
    """
    Connect two entities with power poles, respecting maximum distances.
    Returns list of placed poles.
    """
    ensure_craftable(Prototype.SmallElectricPole, quantity=max_distance // 5)
    return connect_entities(source, target, Prototype.SmallElectricPole)
```

### 2. Factory Building Functions
```python
def setup_smelting_array(ore_position: Position, num_furnaces: int = 5) -> List[Entity]:
    """
    Build a complete smelting array with miners, furnaces, and belts.
    """
    # Build mining drill
    ensure_craftable(Prototype.BurnerMiningDrill)
    drill = place_entity(Prototype.BurnerMiningDrill, position=ore_position)
    
    # Build furnace line
    furnaces = []
    for i in range(num_furnaces):
        furnace = place_entity_next_to(
            Prototype.StoneFurnace,
            reference_position=drill.drop_position,
            direction=Direction.RIGHT,
            spacing=i * 2
        )
        furnaces.append(furnace)
    
    # Connect with belts and inserters
    connect_entities(drill.drop_position, furnaces[-1].position, 
                    Prototype.TransportBelt)
    return furnaces
```

### Best Practices for Utility Functions

1. **Safety First**
- Validate inputs and entity states
- Clean up partially built structures on failure
- Return meaningful values or raise specific exceptions

2. **Resource Management**
- Pre-calculate and verify resource requirements
- Include automatic crafting of required materials
- Handle fuel management systematically
- Clean up resources on failure

3. **Modularity**
- Keep functions focused on a single responsibility
- Make functions composable for larger systems
- Use type hints and documentation
- Return useful data for chaining operations

4. **Error Handling**
- Use specific exception types
- Include diagnostic information in error messages
- Implement cleanup on failure
- Validate preconditions early

5. **Configuration**
- Make important values configurable parameters
- Use reasonable defaults
- Document parameter impacts
- Include validation for parameter ranges