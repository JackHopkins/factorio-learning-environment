# Manual

## Core Interaction Patterns

### 0. Recipe printing
Before crafting any item, you must print the recipes of said items:
```python
# Print recipe for Boiler
print("Recipe for 3 Boilers:")
boiler_recipe = get_prototype_recipe(Prototype.Boiler)
ingredients = boiler_recipe.ingredients
for ingredient in ingredients:
    # need to multiply by 3 as we need 3 boilers
    count = ingredient.count*3
    print(f"Need: {{count}} {{ingredient.name}} for 3 boilers")

```

### 1. Material Processing Requirements
Before crafting any items requiring plates, ores MUST be smelted first:
```python
# Wrong:
# Can't craft directly from ore!
craft_item(Prototype.IronGearWheel)  # Will fail - needs iron plates, not ore

# Correct:
# 1. Get ore
move_to(nearest(Resource.IronOre))
harvest_resource(nearest(Resource.IronOre), quantity=10)
print(f"Harvested 10 iron ore")

# 2. Smelt ore into plates
# move to the position to place the entity
move_to(position)
furnace = place_entity(Prototype.StoneFurnace, position=position)
print(f"Placed the furnace to smelt plates at {furnace.position}")

# we also update the furnace variable by returning it from the function
# This ensures it doesnt get stale and the inventory updates are represented in the variable
furnace = insert_item(Prototype.Coal, furnace, quantity=5)  # Don't forget fuel
furnace = insert_item(Prototype.IronOre, furnace, quantity=10)

# 3. Wait for smelting (with safety timeout)
for _ in range(30):  # Maximum 30 seconds wait
    if inspect_inventory(furnace)[Prototype.IronPlate] >= 10:
        break
    sleep(1)
else:
    raise Exception("Smelting timeout - check fuel and inputs")

# final check for the inventory of furnace
iron_plates_in_furnace = inspect_inventory(furnace)[Prototype.IronPlate]
assert iron_plates_in_furnace>=10, "Not enough iron plates in furnace"
print(f"Smelted 10 iron plates")
# extract the plates from the furnace
# make sure to first move to the furnace pos as we cant extract from a distance
move_to(furnace.position)
# extract the plates
extract_item(Prototype.IronPlate, furnace.position, 10)
# assert we have 10 plates in players inventory
assert inspect_inventory()[Prototype.IronPlate] >=10, f"Not enough plates in inventory"
# 4. Now you can craft
craft_item(Prototype.IronGearWheel)
print(f"Crafted iron gear wheels")
```

### 3. Inventory Requirements
Before placing any entity, ensure it exists in the inventory. Many beginners miss this crucial step:
```python
# Wrong:
drill = place_entity(Prototype.BurnerMiningDrill, position=position)  # Will fail if not in inventory!

# Correct:
inventory = inspect_inventory()
burner_drills_in_inventry = inventory[Prototype.BurnerMiningDrill]
assert burner_drills_in_inventry > 0, "No drills in inventory"
# move to the position to place the entity
move_to(position)
drill = place_entity(Prototype.BurnerMiningDrill, position=position)
print(f"Placed drill to mine stone at {drill.position}")
```

You can inspect your own inventory, or the inventory of an entity:
```python
# Check player inventory
player_inv = inspect_inventory()
iron_plates = player_inv[Prototype.IronPlate]

# Check entity inventory
# move to the position to place the entity
move_to(pos)
furnace = place_entity(Prototype.StoneFurnace, position=pos)
print(f"Placed furnace at {furnace.position}")
furnace_inv = inspect_inventory(furnace) # Check the furnace inventory
coal_in_furnace = furnace_inv[Prototype.Coal]
```

### 4. Resource Location & Movement
Before any entity placement or interaction, you must first move to the target location:
```python
# Always locate resources first
resource_position = nearest(Resource.Coal)
print(f"Found iron at {resource_position}")
move_to(resource_position)  # Must move before placing/interacting
```

### 5. Entity Placement Prerequisites

#### Basic Entity Placement
Entities must be placed in a valid location after moving there:
Include logs for what the entity is placed for
```python
# Basic placement pattern
move_to(target_position) 
entity = place_entity(Prototype.Entity, position=target_position)
print(f"Placed entity at {entity.position} to do X")
```

#### Basic Entity Removal
Entities can be picked up with pickup_entity
```python
# Basic entity picking up pattern
move_to(target_position) 
pickup_entity(Prototype.Entity, position=target_position)
```
The same can be done for beltgroups or pipegroups
In those cases you need to loop through the belts or pipes and pick them up separately
Example with beltgroups
```python
# Place the example groups
starting_pos = Position(x = 0, y = 12)
ending_pos = Position(x = 0, y = 8)
# create the beltgroup
beltgroup_to_be_picked_up = connect_entities(starting_pos, ending_pos, Prototype.TransportBelt)

# loop through the belts to pick them up separately
for belt in beltgroup_to_be_picked_up.belts:
    # pick the belt up
    pickup_entity(Prototype.TransportBelt, position=belt.position)
```
The same can be done for pipegroups, use the pipegroup.pipes to loop through the pipes


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
# move to the position to place the entity
move_to(drill_position)
ref_entity = place_entity(Prototype.BurnerMiningDrill, position=drill_position)
connected_entity = place_entity_next_to(
    Prototype.BurnerInserter,
    reference_position=ref_entity.position,
    direction=Direction.UP,
    spacing=0
)
print(f"Placed inserter at {connected_entity.position} next to ref_entity at position {ref_entity.position} to input X into the ref_entity")
```

#### Common Patterns and Use Cases

1. **Resource factory**
- When creating factories, you must plan out the size requirements of the factory sections. Use the BuildingBox for this. You can set the height and width of the area you need for a specific entity placement. For instance, for a single drill, the height and width requirements are 2 so it buildingbox = BuildingBox(height = 2, width = 2). For a drill line, you can do BuildingBox(height = 2, width = 2*drill_line).
- When knowing the size, use nearest_buildable to get the center coordinate of the area where the BuildingBox would fit. Use the center_position argument, where you can send in the position around where you need to find the buildable area. The returns of the nearest_buildable is a Boundingbox with the following attributess 
            left_top - The top left position of the buildable area
            right_bottom - The bottom right position of the buildable area
            left_bottom - The bottom left position of the buildable area
            right_top - The top right position of the buildable area
- Use the Buildingbox to plan out all factory areas, use one for mining, one for assembling machine area etc. 
- Put each factory section sufficiently far away from each other to ensure no overlap. For instance, when creating plate factories going into an assembling machine, put the assembling machine 10 spaces away from the drills

Example: Iron ore mine
```python
# log your general idea what you will do next
print(f"I will create a iron ore mine with burner mining drill into a collection chest")
# move to the position to place the entity
move_to(iron_ore_position)
# define the BuildingBox for the drills.
# A BurnerMiningDrill has dimensions 2x2 tiles (2 height, 2 width) wide and ElectricMiningDrill has 3x3 dimensions so we need to take that into account
# We also need to put a chest at the drop point of the drill so the height needs to be 3 (2 for drill, 1 for chest)
building_box = BuildingBox(width = 2, height = 3)
# get the nearest buildable area around the iron_ore_position
buildable_coordinates = nearest_buildable(Prototype.BurnerMiningDrill, building_box, iron_ore_position)
# Place drill on the left_top of the buildable_coordinates
drill_pos = buildable_coordinates.left_top
move_to(drill_pos)
# Place the drill facing down as we start from top coordinate
drill = place_entity(Prototype.BurnerMiningDrill, position=drill_pos, position = Position.DOWN) 
print(f"Placed burner mining drill to mine iron ore at {drill.position}") # Position(x = 0, y = 10)

# place a chest at the drop position of the drill to catch the ore
collection_chest = place_entity(Prototype.WoodenChest, position = drill.position)
print(f"Put a collection chest at {collection_chest.position} that catches and stores iron ore from the burner mining drill at {drill.position}")
# wait 10 seconds to check if the construct works and chest has ore
sleep(10)

# get the updated chest entity
collection_chest = get_entity(Prototype.WoodenChest, position = collection_chest.position)
# get the inventory
chest_inventory = inspect_inventory(collection_chest)
# get the iron ore in inventory
iron_ore_in_chest = chest_inventory[Prototype.IronOre]
# check for iron ore
assert iron_ore_in_chest > 0, "No iron ore in chest"
```

2. **Power Infrastructure**

Power typically involves:
-> Water Source + OffshorePump
-> Boiler (burning coal)
-> SteamEngine
NB: Use at least spacing of 3 to ensure there is enough room for pipes
NB: Fluid handling objects have a `fluid_systems` attribute that specifies the fluid network they are attached to.

IMPORTANT: We also need to be very careful and check where we can place boiler and steam engine as they cannot be on water
```python
# log your general idea what you will do next
print(f"I will create a power generation setup with a steam engine")
# Power system pattern
move_to(water_position)
# first place offshore pump on the water system
offshore_pump = place_entity(Prototype.OffshorePump, position=water_position)
print(f"Placed offshore pump to get water at {offshore_pump.position}")
# Then place the boiler close to the offshore pump
# IMPORTANT: We need to be careful as there is water nearby which is unplaceable,
# We do not know where the water is so we will use nearest_buildable for safety and place the entity at the center of the boundingbox
# We will also need to be atleast 4 tiles away from the offshore-pump as the boilers dimensions are 2x3 and otherwise won't have room for connections. Therefore the nearest_buildable buildingbox will have width and length of 9 so the center is 4 tiles away from all borders
bbox = BuildingBox(height = 9, width = 9)
coords = nearest_buildable(Prototype.Boiler,bbox,offshore_pump.position)
# get the top left coordinate
top_left_coord = coords.left_top
# get the centre coordinate by adding 4 to x and y coordinates (we add 4 to y as the y coordinates are inverted in Factorio)
center = Position(top_left_coord.x +4, top_left_coord.y +4)
# place the boiler at the centre coordinate
boiler = place_entity(Prototype.Boiler, position = center)
print(f"Placed boiler to generate steam at {boiler.position}. This will be connected to the offshore pump at {offshore_pump.position}")
# add coal to boiler to start the power generation
boiler = insert_item(Prototype.Coal, boiler, 10)


# Finally we need to place the steam engine close to the boiler
# IMPORTANT: We again need to create a buildingbox with a height and length of 9 to be safe as steam engine has is 3x5 dimensions
bbox = BuildingBox(height = 9, width = 9)
coords = nearest_buildable(Prototype.SteamEngine,bbox,boiler.position)
# get the top left coordinate
top_left_coord = coords.left_top
# get the centre coordinate by adding 4 to x and y coordinates (we add 4 to y as the y coordinates are inverted in Factorio)
center = Position(top_left_coord.x + 4, top_left_coord.y + 4)
# move to the centre coordinate
move_to(center)
# place the steam engine on the centre coordinate
steam_engine = place_entity(Prototype.SteamEngine, position = center)

print(f"Placed steam_engine to generate electricity at {steam_engine.position}. This will be connected to the boiler at {boiler.position} to generate electricity")

# Connect entities in order
water_pipes = connect_entities(offshore_pump, boiler, Prototype.Pipe)
print(f"Connected offshore pump at {offshore_pump.position} to boiler at {boiler.position} with pipes {water_pipes}")
steam_pipes = connect_entities(boiler, steam_engine, Prototype.Pipe)
print(f"Connected boiler at {boiler.position} to steam_engine at {steam_engine.position} with pipes {water_pipes}")

# check that it has power
# sleep for 5 seconds to ensure flow
sleep(5)
# update the entity
steam_engine = get_entity(Prototype.SteamEngine, position = steam_engine.position)
# check that the steam engine is generating power
assert steam_engine.energy > 0, f"Steam engine is not generating power"
print(f"Steam engine at {steam_engine.position} is generating power!")
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
- Use `drop_position` when connecting output of one entity to another
- You can place a chest into drills drop position to catch the ore or a furnace to smelt it directly
- When connecting to a inserter, use the pickup_position of target inserter
For example, if you want to connect inserter_1 at Position(x = 12, y = 11) to inserter_2 at Position(x = 0, y = 0)
```python
# get the inserter entities
inserter_1 = get_entity(Prototype.BurnerInserter, position = Position(x = 12, y = 11))
inserter_2 = get_entity(Prototype.BurnerInserter, position = Position(x = 0, y = 0))
# connect the two inserters (source -> target). Passing in the entity will result in them being connected intelligently.
belts = connect_entities(
    inserter_1, #.drop_position,
    inserter_2, #.pickup_position,
    Prototype.TransportBelt
)
print(f"Connected inserters at {inserter_1.position} and {inserter_2.position} with {belts}")
```

4. **Spacing Guidelines**
- Use 0 spacing for flush connections and when placing inserters
- Use 1 spacing for entities that need space for inserters between them
- Use 3+ spacing for power setups (boiler to steam engine) or where you need extra space for pipes or belts.


5. **Position Handling**
The Position class provides helpful methods for working with coordinates:
```python
# Position arithmetic
new_pos = pos1 + Position(x=2, y=0)  # Move right 2 units

new_pos = new_pos.right(2) # Move right 2 units
```

### 4. Multiple section Construction
When building with multiple factory sections, follow this pattern:
1. Establish a suitable place for a new section. New sections should be sufficiently far away from existing sections (eg 10 spaces)
2. Place the new section (e.g., assembling machine).
3. Place inserters if required to connect new section with existing sections
4. Place connectors (e.g.belts, pipes)
5. Add fuel/resources

Example:
Create a assembling machine and connect it to a existing furnace 
Assume a furnace exists at Position(x = 9, y = -10)
```python
# log your general idea what you will do next
print(f"I will create a assembling machine for copper cables and connect it to the copper plate furnace at Position(x = 9, y = -10)")
# get the existing furnace
furnace = get_entity(Prototype.StoneFurnace, position = Position(x = 9, y = -10))
# place a inserter taking plates out of the furnace
# No need to rotate the inserter as its taking out of the furnace
furnace_output_inserter = place_entity_next_to(Prototype.BurnerInserter, 
                                                reference_position = furnace.position, 
                                                spacing = 0, 
                                                direction =Direction.LEFT ) # assume here you can put the inserter to the left. You need to check this in the game

# Plan the assembling machine 10 spaces away
target_position = Position(x = furnace_output_inserter.position.x + 10, y = furnace_output_inserter.position.y)
# move to the position to place the entity
move_to(target_position)
# define the buildable area for the assembling machine, assembling machines have 3x3 dimensions
# Put 5 as width (3 for assembling machine, 1 for inserter, 1 for inserter pickup position) as we need to account for the inserter picking up items and putting to assembling machine
building_box = BuildingBox(width = 5, height = 3)
# get the nearest buildable area around the target_position
buildable_coordinates = nearest_buildable(Prototype.AssemblingMachine1, building_box, target_position)
# use the left_top coordinate to put the target_machine
assembly_pos = buildable_coordinates.left_top
move_to(assembly_pos)
target_machine = place_entity(Prototype.AssemblingMachine1, position=assembly_pos)
print(f"Placed AssemblingMachine1 at {target_machine.position} to automatically create copper cables")

# put a inserter next to the assembly machine
# always use 0 spacing for inserters
# direction is RIGHT as we put 2 at the width of the buildable coordinates
machine_input_inserter = place_entity_next_to(Prototype.BurnerInserter,
    reference_position=target_machine.position,
    direction=Direction.RIGHT,
    spacing = 0)

# rotate the inserter as we need to put items into the chest
machine_input_inserter = rotate_entity(machine_input_inserter, direction = Direction.LEFT)
print(f"Placed a inserter at {machine_input_inserter.position} to put copper plates into assembling machine at {target_machine.position}")
# fuel the inserter
# we also update the inserter variable by returning it from the function
# This ensures it doesnt get stale and the inventory updates are represented in the variable
machine_input_inserter = insert_item(Prototype.Coal, machine_input_inserter, quantity=20)

# connect the furnace output inserter to chest input inserter
# IMPORTANT: ALWAYS NEED TO CONNECT TRANSPORT BELTS TO A INSERTER, NEVER DIRECTLY CONNECT TO A CHEST OR FURNACE
connection = connect_entities(furnace_output_inserter.drop_position, machine_input_inserter.pickup_position, Prototype.TransportBelt)
print(f"Connected furnace at {furnace.position} to assembling machine at {target_machine.position} with {connection}. This will move copper plates to assembling machine to create copper cables")
```

### 5. Power Systems
Power systems follow a specific order:
1. Get the power source (eg steam engine)
2. Get the power target
3. Connect the target with electric poles using the `connect_entities` function with an appropriate electric pole prototype
NB: Always use connect_entities when connecting power source to target
NB: The `electrical_id` of the entity is used to identify the power network it is connected to.

EXAMPLE
```python
# log your general idea what you will do next
print(f"I will power the assembling machine at Position(x = 1, y = 19) with power from steam engine at Position(x=4, y = -21)")
# get the steam engine. In this example, there is a steam engine at Position(x=4, y = -21)
steam_engine = get_entity(Prototype.SteamEngine, position = Position(x=4, y = -21))

# To power electric mining drills or assembling machines, the engine needs to be connected with electricpoles
# for example, if one exists in Position(x = 1, y = 19), we first get the entity
assembling_machine = get_entity(Prototype.AssemblingMachine1, position = Position(x = 1, y = 19))

# We then connect with connect entities
connect_entities(assembling_machine.position, steam_engine.position, Prototype.SmallElectricPole)
# wait for 10 seconds to power up
sleep(10)
# check that the power was successful
# first refresh entity
assembling_machine = get_entity(Prototype.AssemblingMachine1, position = assembling_machine.position)
# check for power
assert assembling_machine.energy > 0, f"assembling machine is not getting power"
```

### 7. Belt Systems
When creating belt systems, ensure that the belts form a straight line wherever possible.
Straight, grid-aligned belts ensure more predictable item flow and easier maintenance.
Establish source, place destination, and then connect with belts. 
NB: ALWAYS USE INSERTERS TO INSERT ITEMS INTO DESTINATION OR TAKE FROM SOURCE.
IMPORTANT: For best results, align the transport belt segments as straight lines.

Example
Move items from a chest to a furnace
```python
# log your general idea what you will do next
print("I will create a chest that transports items to a furnace using a straight belt line")
source_position = Position(0, 0)
# Belt system pattern
move_to(source_position)
# define the BuildingBox for the chest. 
# chest dimensions are 1x1; add extra space for the inserter
building_box = BuildingBox(width = 1, height = 3)
buildable_coordinates = nearest_buildable(Prototype.WoodenChest, building_box, source_position)
source_pos = buildable_coordinates.left_top
move_to(source_pos)
source = place_entity(Prototype.WoodenChest, position=source_pos)
print(f"Placed chest at {source.position}")

# Add inserter (always use 0 spacing for inserters)
source_inserter = place_entity_next_to(Prototype.BurnerInserter, 
                                      reference_position=source.position,
                                      direction=Direction.DOWN,
                                      spacing=0)
print(f"Placed an inserter at {source_inserter.position} to extract items from the chest at {source.position}")

# Place a furnace 10 spaces away in a grid-aligned fashion for a straight belt run
target_position = Position(x = source.position.x + 10, y = source.position.y)
move_to(target_position)
building_box = BuildingBox(width = 3, height = 1)
buildable_coordinates = nearest_buildable(Prototype.StoneFurnace, building_box, target_position)
furnace_pos = buildable_coordinates.left_top
move_to(furnace_pos)
destination_furnace = place_entity(Prototype.StoneFurnace, position=furnace_pos)
print(f"Placed furnace at {destination_furnace.position}")

# Add inserter next to the furnace (using 0 spacing)
destination_inserter = place_entity_next_to(Prototype.BurnerInserter, 
                                           reference_position=destination_furnace.position,
                                           direction=Direction.RIGHT,
                                           spacing=0)
destination_inserter = rotate_entity(destination_inserter, Direction.LEFT)  # Rotate to insert into the furnace
print(f"Placed inserter at {destination_inserter.position} to feed the furnace at {destination_furnace.position}")

# Connect the two inserters with a straight transport belt line
belt = connect_entities(source_inserter, destination_inserter, Prototype.TransportBelt)
print(f"Connected chest inserter at {source_inserter.position} to furnace inserter at {destination_inserter.position} with a straight belt: {belt}")
```

### 8. Many-to-One Connections
When you need to connect multiple sources to a single target with transport belts
1. Establish sources and target
2. Create the main connection by connecting one source to the target with transport belts
3. Connect all remaining sources to the main connection with transport belts
NB: NEVER CONNECT MULTIPLE ENTITIES DIRECTLY TO THE SAME TARGET
You always need to create one main connection and then connect additional entities to the main connection line with transport belts

Example: Connecting multiple source inserters to one target inserter
Assume we have source_inserter_1, source_inserter_2, source_inserter_3 burner inserter variables as sources on the map at positions Position(x = 1, y = 2), Position(x = 3, y = 2) and Position(x = 5, y = 2)
Also assume we have target_inserter burner inserter variable as the target on the map at Position(x = 10, y = 28)
```python
# get the inserter variables
source_inserter_1 = get_entity(Prototype.BurnerInserter, Position(x = 1, y = 2))
source_inserter_2 = get_entity(Prototype.BurnerInserter, Position(x = 3, y = 2))
source_inserter_3 = get_entity(Prototype.BurnerInserter, Position(x = 5, y = 2))
target_inserter = get_entity(Prototype.BurnerInserter, Position(x = 10, y = 28))
# log your general idea what you will do next
print(f"I will create a connection from the inserters at [{source_inserter_1.position}, {source_inserter_2.position}, {source_inserter_3.position}] to the inserter at {target_inserter.position}")
# create the main connection
main_connection = connect_entities(source_inserter_1.drop_position, 
                                    target_inserter.pickup_position,
                                    Prototype.TransportBelt)
# Print out the whole connection for logs
# as main_connection is a list of beltgroups, we print out the whole list
print(f"Created the main connection between inserter at {source_inserter_1.position} to inserter at {target_inserter.position}: {main_connection}")

# Connect source_inserter_2 and source_inserter_3 to the main connection
secondary_sources = [source_inserter_2, source_inserter_3]
for source in secondary_sources:
    # connect the source to main connection
    # Use the first beltgroup from the main connection to connect to
    # Also override the main_connection to get the newest belt groups
    main_connection = connect_entities(source.drop_position, 
                                    main_connection,
                                    Prototype.TransportBelt)
    print(f"Extended main connection to include inserter at {source.position}: {main_connection}")
print(f"Final connection after connecting all inserters to target: {main_connection}")
```

When you want to connect entities to existing power pole groups, similar rules apply
Assume in this example there is a steam engine at Position(x = 1, y = 2) and the drill is at Position(x = 10, y = 28)
```python
# get the variables
steam_engine = get_entity(Prototype.SteamEngine, Position(x = 1, y = 2))
drill_1 = get_entity(Prototype.ElectricMiningDrill, Position(x = 10, y = 28))
# create the main connection
main_power_connection = connect_entities(steam_engine, 
                                    drill_1,
                                    Prototype.SmallElectricPole)
# Print out the whole connection for logs
# as main_connection is a list of ElectricityGroup, we print out the whole list
print(f"Created the main connection to power drill at {drill_1.position} with steam engine at {steam_engine.position}: {main_connection}")

# connect the secondary source to the main power connection
# Use the first ElectricityGroup from the main connection to connect to
# Also override the main_power_connection to get the newest ElectricityGroups
main_power_connection = connect_entities(drill_2, 
                                main_connection,
                                Prototype.SmallElectricPole)
```


### 9. Using assembling machines
To create automatic item crafting mines (copper cable, electronic circuits etc), you need to use a assembling machine that automatically crafts the entities.
To use assembling machines for automatic crafting mines, you need to power them and set their recipe
The recipe will be set to the entity the machine needs to craft
You also need to add inserters that input crafting ingredients into the machine and inserters that take the crafted item out of the machine

```python
# Assume there's an assembling machine at Position(x = 2, y = -19) and a steam engine generating power at Position(x = -10, y = 0)
# log your general idea what you will do next
print(f"I will create a assembling machine for copper cables")
# first get the assembling machine and steam engine entities
assembling_machine = get_entity(Prototype.AssemblingMachine1, position = Position(x = 2, y = -19))
steam_engine = get_entity(Prototype.SteamEngine, position = Position(x = -10, y = 0))

# connect the steam engine and assembling machine with power poles to power the assembling machine
# We use connect entities as we're dealing with power poles
connect_entities(assembling_machine.position, steam_engine.position, Prototype.SmallElectricPole)
# wait for 10 sec to assure assembling machine is powered
sleep(10)
# update the assembling machine entity
assembling_machine = get_entity(Prototype.AssemblingMachine1, position = Position(x = 2, y = -19))
assert assembling_machine.energy>0, "Assembling machine is not powered"

# set the recipe for assembling machine to iron gear wheels
set_entity_recipe(entity = assembly_machine, prototype = Prototype.CopperCable)
print(f"Set the recipe of assembly machine at {assembly_machine.position} to Prototype.CopperCable")

# add inserter that inputs ingredients that will be crafted to the target entity
# always use 0 spacing for inserters
ingredient_input_inserter = place_entity_next_to(
    Prototype.BurnerInserter, 
    assembling_machine.position,
    direction=Direction.UP,
    spacing = 0
)
print(f"Placed a inserter at {ingredient_input_inserter.position} that puts copper ore into the assembling machine at {assembly_machine.position}")
#VERY IMPORTANT:  Need to rotate the inserter as it needs to put itms into assembling machine
ingredient_input_inserter = rotate_entity(ingredient_input_inserter, Direction.DOWN)  # Face inserter towards the assembling machine

# add inserter that takes the cables away
# always use 0 spacing for inserters
output_inserter = place_entity_next_to(
    Prototype.BurnerInserter, 
    assembling_machine.position,
    direction=Direction.LEFT,
    spacing = 0
)
print(f"Placed a inserter at {output_inserter.position} that takes away copper cables from the assembling machine at {assembly_machine.position}")
```


#### Key Features
1. **Resource Requirements**: Automatically considers entity placement requirements (e.g., miners must be on ore patches)
2. **Space Validation**: Ensures enough clear space for different factory sections, eg assembling machine area 10 spaces away from furnaces

#### Common Patterns

1. **Mining Setup**:
Example: Create a copper plate mining line with 3 drills
```python
# log your general idea what you will do next
print(f"I will create a single line of 3 drills to mine copper ore")
# Find space for a line of 3 miners
move_to(source_position)
# define the BuildingBox for the drill. 
# A BurnerMiningDrill dimensions are 2xe (2 width, 2 height) and ElectricMiningDrill is has 3x3 dimensions so we need to take that into account
# We need 3 drills so width is 3*3, height is 4, 3 for drill, one for furnace
building_box = BuildingBox(width = 3*3, height = 4)
# get the nearest buildable area around the source_position
buildable_coordinates = nearest_buildable(Prototype.BurnerMiningDrill, building_box, source_position)

# Place miners in a line
# we first get the leftmost coordinate of the buildingbox to start building from
left_top = buildable_coordinates.left_top
# first lets move to the left_top to ensure building
move_to(left_top)
for i in range(3):
    # we now iterate from the leftmost point towards the right
    # take steps of 2 as drills have width of 2
    drill_pos = Position(x=left_top.x + 2*i, y=left_top.y)
    # Place the drill facing down as we start from top coordinate
    drill = place_entity(Prototype.ElectricMiningDrill, position=drill_pos, direction = Direction.DOWN)
    print(f"Placed ElectricMiningDrill {i} at {drill.position} to mine copper ore")
    # place a chest to catch the ore
    furnace = place_entity(Prototype.StoneFurnace, position = drill.drop_position)
    print(f"Placed furnace at {furnace.position} to smelt the copper ore for drill {i} at {drill.position}")
```

#### Error Handling
The function raises an exception if no valid position is found. Always wrap usage in try/except when placement requirements are uncertain:

```python
try:
    position = nearest_buildable(
        Prototype.ElectricMiningDrill,
        building_box=large_area,
        position = Position(x = 0, y = 1)
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


3. **Placement Verification**:
- Always verify placement after finding position
- Use can_place_entity for additional validation
```python
positions = nearest_buildable(Prototype.StoneFurnace)
if can_place_entity(Prototype.StoneFurnace, position=positions.left_top):
    furnace = place_entity(Prototype.StoneFurnace, position=positions.left_top)
```

### 10. Research and Technology

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

### Self-Fueling Mining Systems

Self-fueling mining systems are essential for automating resource collection, particularly for coal mining. These systems use the mined coal to power themselves, creating a sustainable loop.

#### Basic Self-Fueling Mine Pattern
```python
# log your general idea what you will do next
print(f"I will create a self fueling single drill system")
# 1. Find suitable coal patch
coal_patch = nearest(Resource.Coal)
# define the BuildingBox for the drill. 
# A BurnerMiningDrill has dimensions 2x2 and ElectricMiningDrill has 3x3 dimensions so we need to take that into account
# We need to put 4 as height as we account for the inserter that will put the coal into the drill (+1 for inserter, +1 for inserter pickup position)
building_box = BuildingBox(width = 2, height = 4)
# get the nearest buildable area around the source_position
buildable_coordinates = nearest_buildable(Prototype.BurnerMiningDrill, building_box, source_position)

# 2. Place mining drill
# place in left_top of buildable_coordinates
target_pos = buildable_coordinates.left_top
move_to(target_pos)
# Place the drill facing down as we start from top coordinate
drill = place_entity(Prototype.BurnerMiningDrill, Direction.DOWN, target_pos)
print(f"Placed BurnerMiningDrill to mine coal at {drill.position}")

# 3. Place inserter to feed coal back into drill
# direction is DOWN as we put 2 at the height of the buildable coordinates and put drill at top left
coal_input_inserter = place_entity_next_to(
    Prototype.BurnerInserter, 
    drill.position,
    direction=Direction.DOWN,
    spacing=0
)
print(f"Placed coal_input_inserter at {coal_input_inserter.position} that will input coal to the burner mining drill at {drill.position}")
# VERY IMPORTANT: rotate input inserter to put items into drill
coal_input_inserter = rotate_entity(coal_input_inserter, Direction.DOWN)  # Face inserter toward drill

# 4. Connect with transport belt
# IMPORTANT: ALWAYS NEED TO CONNECT TRANSPORT BELTS TO A INSERTER, NEVER DIRECTLY CONNECT TO A CHEST OR FURNACE
belts = connect_entities(
    drill.drop_position,
    inserter.pickup_position,
    Prototype.TransportBelt
)
print(f"Connected BurnerMiningDrill at {drill.position} to inserter at {coal_input_inserter.position} with {belts}")

# 5. Bootstrap system with initial fuel
# we also update the drill variable by returning it from the function
# This ensures it doesnt get stale and the inventory updates are represented in the variable
drill = insert_item(Prototype.Coal, drill, quantity=20)
```

#### Shared belt resource mining systems

For larger operations, you can create systems with multiple drills with two rows of drills sharing a common belt in the middle
EXAMPLE: Build a mining system sharing a common transport belt into a single chest
This should be done in 2 policies
Policy 1: Put down the drill line and the shared transport line
```python
    """
    Build a mining system sharing a common transport belt
    """
    # log your general idea what you will do next
    print(f"I will put down 2 lines of drills with a single shared transport belt in the middle to mine copper ore")
    copper_ore_pos = nearest(Resource.CopperOre)
    num_drills = 5
    drills = []
    # define the BuildingBox for the drills. 
    # A BurnerMiningDrill has 2x2 dimensions and ElectricMiningDrill has 3x3 dimensions so we need to take that into account
    # 2 lines of drills sharing a common belt means 5 height (2 for upper line, 2 for bottom line, 1 for middle belt)
    building_box = BuildingBox(width = 2*num_drills, height = 5)
    # get the nearest buildable area around the source_position
    buildable_coordinates = nearest_buildable(Prototype.BurnerMiningDrill, building_box, copper_ore_pos)
    # we first get the left coordinates of the buildingbox to start building from
    left_top = buildable_coordinates.left_top
    # create a list to keep track of upper drills to create the shared belt
    drills = []
    print(f"I will create a drillline with 2 lines sharing a common transport belt in the middle")
    # start placing the drills
    for i in range(num_drills):
        # Calculate positions with proper spacing
        upper_drill_position = Position(
            x=left_top.x + i * 2,
            y=left_top.y
        )
        move_to(upper_drill_position)
        # Place and configure each drill
        upper_drill = place_entity(
            Prototype.BurnerMiningDrill,
            Direction.DOWN, # direction is down as its the upper drill
            upper_drill_position
        )
        print(f"Placed upper BurnerMiningDrill {i} at {upper_drill.position} to mine coal")
        # append to the list
        drills.append(upper_drill)

        # Place the bottom drill with place_entiy_next_to and down from upper drill
        bottom_drill = place_entity_next_to(
            Prototype.BurnerMiningDrill,
            direction = Direction.DOWN, # direction is down as we place the drill below the upper drill
            reference_position = upper_drill.position,
            spacing = 1 # We put 1 spacing as we need room for transport belts
        )
        # now we need to rotate the bottom drill to face up, i.e towards the shared transport belt
        bottom_drill = rotate_entity(bottom_drill, direction = Direction.UP)
        print(f"Placed bottom BurnerMiningDrill {i} at {bottom_drill.position} to mine coal")
        drills.append(bottom_drill)

    # 2. Create main transport belt
    # first get the belt start and end coordinates
    # for this we need to get the minimum and maximum x coordinates from drill drop positions
    x_coordinates = [drill.drop_position.x for drill in drills]
    start_x = min(x_coordinates)
    end_x = max(x_coordinates)
    # as its a horisontal line, y coordinate stays the same
    shared_y_coordinate = drills[0].drop_position.y
    belt_start = Position(x = start_x, y = shared_y_coordinate)
    belt_end = Position(x = end_x, y = shared_y_coordinate)
    
    # Now we connect
    main_belt = connect_entities(
        belt_start,
        belt_end,
        Prototype.TransportBelt
    )
    # print out all Beltgroup coordinates
    # Beltgroup has many belts so we dont pick one but print out all
    print(f"Created the main belt for the shared drill line: {main_belt}")
    # Example: Beltgroup end position is at Position(x = 12, y = -8)
```

Policy 2: Put down the single chest that is the end of the line
```python
    """
    Build a mining system sharing a common transport belt
    """
    # log your general idea what you will do next
    print(f"I will connect the transport belt end at {belt_end_position} to a single destination chest that will collect copper ore")
    # from logs we see that the belt end is at Position(x = 12, y = -8)
    belt_end_position = Position(x = 12, y = -8)
    # add 10 spaces to ensure no collision
    chest_central_pos = Position(x = belt_end_position.x+10, y = belt_end_position.y)
    # define the buildable area for the chest, chest dimensions are 1x1
    # Also need to account for inserter so width is 3 (+1 for inserter, +1 for inster pickup position)
    building_box = BuildingBox(width = 3, height = 1)
    # get the nearest buildable area around the iron_ore_position
    buildable_coordinates = nearest_buildable(Prototype.WoodenChest, building_box, chest_central_pos)
    # we first get the leftmost coordinate of the buildingbox to start building from
    left_top = buildable_coordinates.left_top
    
    # place the chest
    chest = place_entity(Prototype.WoodenChest, position = left_top)
    print(f"placed collection chest at {chest.position} that will get the copper ore from the shared mining belt")

    # add the inserter
    # we add the inserter to the right as the buildable area had 2 width and we put chest at top left
    chest_inserter = place_entity_next_to(
           Prototype.BurnerInserter,
           chest.position,
           direction=Direction.RIGHT,
           spacing = 0
       )
    
    # rotate the inserter to put items into chest
    chest_inserter = rotate_entity(destination_inserter, Direction.LEFT)
    print(f"placed a inserter at {chest_inserter.position} that will input copper ore to the chest at {chest.position}")
    # 2. Connect the main transport belt to the chest inserter pickup position
    # Now we connect
    main_belt_extended = Fentities(
        belt_end_position,
        chest_inserter.pickup_position,
        Prototype.TransportBelt
    )
    # print out all Beltgroup coordinates
    # Beltgroup has many belts so we dont pick one but print out all
    print(f"Extended the shared resource belt to the inserter at {chest_inserter.position} to input items into the chest at {chest.position}: {main_belt_extended}")
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
       # always use 0 spacing for inserters
       inserter = place_entity_next_to(
           Prototype.BurnerInserter,
           drill.position,
           direction=Direction.UP,
           spacing = 0
       )
   except Exception as e:
       print(f"Failed to build mining system: {e}")
       # Clean up partial construction
   ```

#### Common Patterns

1. **Linear Mining Array**
   - Place drills in a straight line
   - Place chests or furnaces at the drop positions

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

4. **Outdated variables**
   - Always update your variables you want to use to ensure the variable state is not outdated
   - Whenever you use insert_item, make sure to override the input entity with the return
   - Always use inspect_inventory to get the inventories, as that gets the latest inventory
   - Regularly update your variables using entity = get_entity(Prototype.X, entity.position)


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
chest = place_entity(Prototype.WoodenChest, position=chest_position)

# Correct:
# move to the position to place the entity
move_to(chest_position)
chest = place_entity(Prototype.WoodenChest, position=chest_position)
inserter = place_entity_next_to(Prototype.Inserter, 
    reference_position=chest.position, spacing = 0)
```

3. **Unfueled Burner Entities**
```python
# Wrong:
drill = place_entity(Prototype.BurnerMiningDrill, position=position)
# Missing fuel!

# Correct:
drill = place_entity(Prototype.BurnerMiningDrill, position=position)
drill = insert_item(Prototype.Coal, drill, quantity=20)
# we also update the drill variable by returning it from the function
# This ensures it doesnt get stale and the inventory updates are represented in the variable
```

## Best Practices

1. **Resource Discovery**
- Always use `nearest()` to find resources
- Cache resource patch information when multiple entities will use it
```python
copper_ore = get_resource_patch(Resource.CopperOre, nearest(Resource.CopperOre))
```

2. **Entity Positioning and Crafting**
- Verify inventory contains entity before attempting placement
- Craft required entities and materials before starting construction
- Check recipe requirements recursively for complex entities
- Always print the recipes to know what are the dependencies
- Maintain consistent spacing patterns for similar entity types

3. **Resource Management**
- Pre-calculate resource requirements
- Verify inventory contents before placement
- Use consistent fuel quantities for similar entity types

4. **Error Handling**
- Always check return values from placement functions
- Verify entity states after important operations
- Clean up partially constructed systems on failure

5. **Logging**
- Always log what you have done in detail
- Log all unknown information as that will be seen in the future steps and used for debugging or planning
- Make sure to log placing entities with placement positions or interactions with the map that give information about your environment
- When entities are part of automatic structures, include what resource or ingredient that automatic structure creates 
- When connecting structures with automatic belts, include the reason for connection and what you are connecting
- IMPORTANT: Include the intention of entities in your print statements. This will be used later to generate a summary so for the summary to be accurate you need to say what the entities are for

## INSTRUCTIONS WHEN CREATING STRUCTURES
- When a entity has status "WAITING_FOR_SPACE_IN_DESTINATION", it means the there is no space in the drop position. For instance, a mining drill will have status WAITING_FOR_SPACE_IN_DESTINATION when the entities it mines are not being properly collected by a furnace or a chest or transported away from drop position with transport belts
- Make sure to always put enough fuel into all entities that require fuel. It's easy to mine more coal, so it's better to insert in abundance 
- Keep it simple! Minimise the usage of transport belts if you don't need them. Use chests and furnaces to catch the ore directly from drills
- Inserters put items into entities or take items away from entities. You need to add inserters when items need to be automatically put into entities like chests, assembling machines, furnaces, boilers etc. The only exception is you can put a furnace or a chest directly at drills drop position, that catches the ore directly