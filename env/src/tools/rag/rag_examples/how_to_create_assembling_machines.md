## Automated Assembly Systems
Assembling machines can be used to automatically craft items in factorio

### Basic Assembly Line
Example
Create a copper cable assembling machine
Put down an assembling machine 15 spaces away from an inserter that will send ingredients to the assembling machine  
Important: Each section of the mine should be atleast 20 spaces further away from the other and have enough room for connections
We will use a existing solar panel to power the assembling machine
```python
# get the input inserter and an existing solar panel
furnace_output_inserter = get_entity(Prototype.BurnerInserter, Position(x = 9, y = 0))
solar_panel = get_entity(Prototype.SolarPanel, Position(x = 0, y = 0))
# get a position 15 spaces away
assembler_position = Position(x = furnace_output_inserter.x + 15, y = furnace_output_inserter.y)
# Plan space for assembler and inserters, add some buffer
building_box = BuildingBox(width=Prototype.AssemblingMachine1.WIDTH + 2*Prototype.BurnerInserter.WIDTH + 2, height=Prototype.AssemblingMachine1.HEIGHT+ 2)
buildable_coords = nearest_buildable(Prototype.AssemblingMachine1,
                                        building_box,
                                        assembler_position)

# Place assembling machine
move_to(buildable_coords.center)
assembler = place_entity(Prototype.AssemblingMachine1,
                            position=buildable_coords.center,
                            direction = Direction.DOWN)
print(f"Placed assembling machine at {assembler.position}")

# Set recipe
set_entity_recipe(assembler, Prototype.CopperCable)

# Add input inserter, that will input items into assembly machine
# place it to the right as we added to the width of the building box
assembly_machine_input_inserter = place_entity_next_to(Prototype.BurnerInserter,
                                          assembler.position,
                                          direction=Direction.RIGHT,
                                          spacing=0)
# rotate it to input items into the assembling machine                                          
assembly_machine_input_inserter = rotate_entity(assembly_machine_input_inserter, Direction.LEFT)

# Add output inserter, that will take items fromthe assembly machine
# put it on the other side of assembling machine
output_inserter = place_entity_next_to(Prototype.BurnerInserter,
                                           assembler.position,
                                           direction=Direction.LEFT,
                                           spacing=0)
output_chest = place_entity(Prototype.WoodenChest, position = output_inserter.drop_position)
# add coal to inserters
output_inserter = insert_item(Prototype.Coal, output_inserter, quantity = 5)
input_inserter = insert_item(Prototype.Coal, input_inserter, quantity = 5)
# Connect power
# NB: To check how to power entities, look at the relevant examples for power networks
poles = connect_entities(power_source,
                     assembler,
                     Prototype.SmallElectricPole)
print(f"Powered assembling machine at {assembler.position} with {poles}")
# wait for 5 seconds to check power
sleep(5)
assembler = get_entity(Prototype.AssemblingMachine1, assembler.position)
assert assembler.energy > 0, f"Assembling machine at {assembler.position} is not receiving power" 
# Connect input belt
belts = connect_entities(furnace_output_inserter,
                     assembly_machine_input_inserter,
                     Prototype.TransportBelt)
print(f"Connected assembling machine at {assembler.position} to furnace_output_inserter with {belts}")

# wait for 15 seconds to if structure works and machine is creating copper cables into the output chest
sleep(15)
output_chest = get_entity(Prototype.WoodenChest, output_chest.position)
inventory = inspect_inventory(output_chest)
copper_cables_in_inventory = inventory[Prototype.CopperCable]
assert copper_cables_in_inventory > 0, f"No copper cables created"
```