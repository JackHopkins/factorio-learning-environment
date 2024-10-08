# Place an assembling machine
assembling_machine = place_entity(Prototype.AssemblingMachine1, Direction.UP, Position(x=0, y=0))
assert assembling_machine, "Failed to place assembling machine"

# Set the recipe for iron gear wheels
set_entity_recipe(assembling_machine, Prototype.IronGearWheel)
assert get_entity(Prototype.AssemblingMachine1, assembling_machine.position).recipe.name == "iron-gear-wheel", "Failed to set recipe for assembling machine"

# Place inserters for input and output
input_inserter = place_entity(Prototype.BurnerInserter, Direction.RIGHT, Position(x=-1, y=0))
assert input_inserter, "Failed to place input inserter"

output_inserter = place_entity(Prototype.BurnerInserter, Direction.LEFT, Position(x=1, y=0))
assert output_inserter, "Failed to place output inserter"

# Place chests for input and output
input_chest = place_entity(Prototype.IronChest, Direction.UP, Position(x=-2, y=0))
assert input_chest, "Failed to place input chest"

output_chest = place_entity(Prototype.IronChest, Direction.UP, Position(x=2, y=0))
assert output_chest, "Failed to place output chest"

# Insert iron plates into the input chest
insert_item(Prototype.IronPlate, input_chest, 50)
assert inspect_inventory(input_chest).get(Prototype.IronPlate) == 50, "Failed to insert iron plates into input chest"

# Insert fuel (coal) into burner inserters
insert_item(Prototype.Coal, input_inserter, 5)
assert inspect_inventory(input_inserter).get(Prototype.Coal) == 5, "Failed to insert coal into input inserter"

insert_item(Prototype.Coal, output_inserter, 5)
assert inspect_inventory(output_inserter).get(Prototype.Coal) == 5, "Failed to insert coal into output inserter"

# Wait for production to start
sleep(30)

# Check if iron gear wheels are being produced
output_inventory = inspect_inventory(output_chest)
assert output_inventory.get(Prototype.IronGearWheel) > 0, "No iron gear wheels produced"

print("Iron gear wheel production line set up successfully!")
